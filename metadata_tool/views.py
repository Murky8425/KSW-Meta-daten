import base64
import hashlib
import io
import json
import mimetypes
import shutil
import tempfile
from urllib.parse import quote
from pathlib import Path

from django.http import HttpResponse
from django.shortcuts import redirect, render
from PIL import Image

from .models import ExtractedMetadata
from .services import convert_image, create_zip, read_xmp_metadata, remove_metadata, resize_image, write_xmp_metadata


ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".heic", ".avif"}


def _upload_dir(request):
    directory = request.session.get("upload_dir")
    if not directory:
        return None
    path = Path(directory)
    return path if path.is_dir() and path.parent == Path(tempfile.gettempdir()) else None


def _fields(data):
    return {
        "XMP-dc:Title": data.get("title", "").strip(),
        "XMP-dc:Description": data.get("description", "").strip(),
        "XMP-dc:Creator": data.get("creator", "").strip(),
        "XMP-dc:Rights": data.get("rights", "").strip(),
        "XMP-dc:Subject": [item.strip() for item in data.get("keywords", "").split(",") if item.strip()],
    }


def _preview_data(path, mime):
    if path.suffix.lower() not in {".tif", ".tiff"}:
        return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"
    with Image.open(path) as image:
        preview = io.BytesIO()
        image.convert("RGB").save(preview, format="JPEG", quality=85)
    return f"data:image/jpeg;base64,{base64.b64encode(preview.getvalue()).decode()}"


def _file_context(directory):
    if directory is None:
        return []
    files = []
    for path in sorted(directory.iterdir()):
        if path.is_file() and not path.name.startswith(".converted-"):
            mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            try:
                preview = _preview_data(path, mime)
            except (OSError, ValueError):
                preview = ""
            files.append({"name": path.name, "path": path, "mime": mime, "preview": preview})
    return files


def _converted_context(request, directory):
    if directory is None:
        return None
    converted_path = Path(request.session.get("converted_path", ""))
    if not converted_path.is_file() or converted_path.parent != directory or not converted_path.name.startswith(".converted-"):
        return None
    return {
        "path": converted_path,
        "name": request.session.get("converted_name", converted_path.name.removeprefix(".converted-")),
        "mime": request.session.get("converted_mime", "application/octet-stream"),
        "show": request.session.get("show_converted", False),
        "preview": _preview_data(converted_path, request.session.get("converted_mime", "application/octet-stream")),
    }


def _clear_uploads(request):
    directory = _upload_dir(request)
    if directory:
        shutil.rmtree(directory, ignore_errors=True)
    for key in ("upload_dir", "converted_path", "converted_name", "converted_mime", "show_converted"):
        request.session.pop(key, None)


def _save_metadata(file_path, filename, metadata):
    fields = {
        "title": metadata.get("XMP-dc:Title", ""),
        "description": metadata.get("XMP-dc:Description", ""),
        "creator": metadata.get("XMP-dc:Creator", ""),
        "rights": metadata.get("XMP-dc:Rights", ""),
        "keywords": metadata.get("XMP-dc:Subject", []),
    }
    ExtractedMetadata.objects.update_or_create(
        file_hash=hashlib.sha256(file_path.read_bytes()).hexdigest(),
        defaults={
            "filename": filename,
            "title": str(fields["title"]),
            "description": str(fields["description"]),
            "creator": str(fields["creator"]),
            "rights": str(fields["rights"]),
            "keywords": json.dumps(fields["keywords"], ensure_ascii=False),
            "all_metadata": json.dumps(metadata, ensure_ascii=False, default=str),
        },
    )


def index(request):
    if request.method == "POST" and request.POST.get("action") == "clear":
        _clear_uploads(request)
        return redirect("index")

    directory = _upload_dir(request)
    error = None
    selected_name = request.GET.get("selected") or request.POST.get("selected")
    metadata = {}

    if request.method == "POST" and request.FILES.getlist("images"):
        if directory:
            shutil.rmtree(directory)
        directory = Path(tempfile.mkdtemp(prefix="ksw-meta-"))
        for uploaded in request.FILES.getlist("images"):
            safe_name = Path(uploaded.name).name
            if Path(safe_name).suffix.lower() in ALLOWED_EXTENSIONS:
                (directory / safe_name).write_bytes(uploaded.read())
        request.session["upload_dir"] = str(directory)
        return redirect("index")

    files = _file_context(directory)
    converted = _converted_context(request, directory)
    names = {file["name"] for file in files}
    if selected_name not in names:
        selected_name = files[0]["name"] if files else None
    selected_file = next((file for file in files if file["name"] == selected_name), None)

    if request.method == "POST" and selected_file:
        try:
            action = request.POST.get("action")
            if action == "batch":
                updated = [(f"{Path(file['name']).stem}-mit-xmp{Path(file['name']).suffix}", write_xmp_metadata(file["path"], _fields(request.POST))) for file in files]
                response = HttpResponse(create_zip(updated), content_type="application/zip")
                response["Content-Disposition"] = 'attachment; filename="bilder-mit-xmp.zip"'
                return response
            if action == "batch-resize":
                scale = request.POST.get("scale", "100")
                resized = [
                    (f"{Path(file['name']).stem}-{scale}prozent{Path(file['name']).suffix}", resize_image(file["path"], scale))
                    for file in files
                ]
                response = HttpResponse(create_zip(resized), content_type="application/zip")
                response["Content-Disposition"] = 'attachment; filename="bilder-skaliert.zip"'
                return response
            if action == "batch-convert":
                target_format = request.POST.get("target_format", "png")
                converted_files = []
                for file in files:
                    data, suffix, _ = convert_image(file["path"], target_format)
                    converted_files.append((f"{Path(file['name']).stem}-konvertiert.{suffix}", data))
                response = HttpResponse(create_zip(converted_files), content_type="application/zip")
                response["Content-Disposition"] = 'attachment; filename="bilder-konvertiert.zip"'
                return response
            if action == "batch-remove":
                cleaned = [
                    (f"{Path(file['name']).stem}-ohne-metadaten{Path(file['name']).suffix}", remove_metadata(file["path"]))
                    for file in files
                ]
                response = HttpResponse(create_zip(cleaned), content_type="application/zip")
                response["Content-Disposition"] = 'attachment; filename="bilder-ohne-metadaten.zip"'
                return response
            if action == "single":
                return _download(write_xmp_metadata(selected_file["path"], _fields(request.POST)), f"{Path(selected_name).stem}-mit-xmp{Path(selected_name).suffix}", selected_file["mime"])
            if action == "remove":
                return _download(remove_metadata(selected_file["path"]), f"{Path(selected_name).stem}-ohne-metadaten{Path(selected_name).suffix}", selected_file["mime"])
            if action == "resize":
                scale = request.POST.get("scale", "100")
                return _download(
                    resize_image(selected_file["path"], scale),
                    f"{Path(selected_name).stem}-{scale}prozent{Path(selected_name).suffix}",
                    selected_file["mime"],
                )
            if action == "convert":
                target_format = request.POST.get("target_format", "png")
                data, suffix, content_type = convert_image(selected_file["path"], target_format)
                converted_name = f"{Path(selected_name).stem}-konvertiert.{suffix}"
                converted_path = directory / f".converted-{converted_name}"
                converted_path.write_bytes(data)
                request.session["converted_path"] = str(converted_path)
                request.session["converted_name"] = converted_name
                request.session["converted_mime"] = content_type
                request.session["show_converted"] = False
                return redirect(f"/?selected={quote(selected_name)}")
            if action == "preview-converted":
                request.session["show_converted"] = True
                return redirect(f"/?selected={quote(selected_name)}")
            if action == "download-converted":
                if converted:
                    return _download(converted["path"].read_bytes(), converted["name"], converted["mime"])
                error = "Es gibt keine fertige konvertierte Datei zum Herunterladen."
            if action == "json":
                metadata = read_xmp_metadata(selected_file["path"])
                _save_metadata(selected_file["path"], selected_name, metadata)
                return _download(json.dumps(metadata, ensure_ascii=False, indent=2).encode(), f"{Path(selected_name).stem}-metadaten.json", "application/json")
        except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
            error = str(exc)

    if selected_file and not metadata:
        try:
            metadata = read_xmp_metadata(selected_file["path"])
            _save_metadata(selected_file["path"], selected_name, metadata)
        except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
            error = str(exc)
    return render(request, "metadata_tool/index.html", {
        "files": files, "selected_name": selected_name, "metadata": metadata,
        "converted": converted,
        "xmp_metadata": {key: value for key, value in metadata.items() if key.startswith("XMP")},
        "metadata_fields": {
            "title": metadata.get("XMP-dc:Title", ""),
            "description": metadata.get("XMP-dc:Description", ""),
            "creator": metadata.get("XMP-dc:Creator", ""),
            "rights": metadata.get("XMP-dc:Rights", ""),
        },
        "error": error,
    })


def _download(data, filename, content_type):
    response = HttpResponse(data, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response