import base64
import hashlib
import io
import json
import mimetypes
import shutil
import tempfile
import uuid
from urllib.parse import quote
from pathlib import Path

from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.mail import send_mail
from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from PIL import Image

from .forms import AccountLoginForm, RegistrationForm
from .models import AccountLifecycle, ExtractedMetadata, StoredImage, UserPreference
from .services import convert_image, create_zip, read_xmp_metadata, remove_metadata, resize_image, write_xmp_metadata


ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".heic", ".avif"}


def _upload_dir(request):
    directory = request.session.get("upload_dir")
    path = Path(directory) if directory else None
    if path and path.is_dir() and path.parent == Path(tempfile.gettempdir()):
        return path

    path = Path(tempfile.mkdtemp(prefix="ksw-meta-"))
    for image in StoredImage.objects.filter(owner=request.user):
        (path / image.storage_name).write_bytes(bytes(image.image_data))
    request.session["upload_dir"] = str(path)
    return path


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
            files.append({
                "key": path.name,
                "name": path.name,
                "path": path,
                "mime": mime,
                "preview": preview,
            })
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
    directory_value = request.session.get("upload_dir")
    directory = Path(directory_value) if directory_value else None
    if directory and (not directory.is_dir() or directory.parent != Path(tempfile.gettempdir())):
        directory = None
    if directory:
        shutil.rmtree(directory, ignore_errors=True)
    for key in ("upload_dir", "converted_path", "converted_name", "converted_mime", "show_converted"):
        request.session.pop(key, None)


def _save_preferred_scale(request, scale):
    scale = int(scale)
    if not 10 <= scale <= 200:
        raise ValueError("Die Bildgröße muss zwischen 10 und 200 Prozent liegen.")
    preference, _ = UserPreference.objects.get_or_create(owner=request.user)
    preference.preferred_scale = scale
    preference.save(update_fields=["preferred_scale"])


def _delete_selected_image(request, storage_name):
    stored_image = StoredImage.objects.filter(owner=request.user, storage_name=storage_name).first()
    if stored_image:
        directory_value = request.session.get("upload_dir")
        directory = Path(directory_value) if directory_value else None
        if directory and directory.is_dir() and directory.parent == Path(tempfile.gettempdir()):
            file_path = directory / stored_image.storage_name
            file_path.unlink(missing_ok=True)
        stored_image.delete()


def _persist_image(request, file, image_data, scale=None):
    stored_image = StoredImage.objects.get(owner=request.user, storage_name=file["key"])
    stored_image.image_data = image_data
    if scale is not None:
        stored_image.last_scale = int(scale)
    stored_image.save(update_fields=["image_data", "last_scale"])
    file["path"].write_bytes(image_data)


def _archive_derived_image(request, filename, image_data, scale=None):
    safe_name = Path(filename).name
    storage_name = f"{uuid.uuid4().hex}{Path(safe_name).suffix.lower()}"
    stored_image = StoredImage.objects.create(
        owner=request.user,
        original_filename=safe_name,
        storage_name=storage_name,
        image_data=image_data,
    )
    if scale is not None:
        stored_image.last_scale = int(scale)
        stored_image.save(update_fields=["last_scale"])
    directory = _upload_dir(request)
    (directory / storage_name).write_bytes(image_data)


def register(request):
    if request.user.is_authenticated:
        return redirect("index")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save(commit=False)
        user.email = form.cleaned_data["email"]
        user.is_active = False
        user.save()
        AccountLifecycle.objects.create(owner=user)
        token = signing.dumps({"user_id": user.pk, "email": user.email}, salt="metadata_tool.email-verification")
        verification_url = request.build_absolute_uri(reverse("verify_email", args=[token]))
        send_mail(
            "E-Mail-Adresse bestätigen",
            f"Bitte bestätige deine E-Mail-Adresse über diesen Link: {verification_url}",
            None,
            [user.email],
            fail_silently=False,
        )
        return render(request, "metadata_tool/verification_sent.html", {"email": user.email})
    return render(request, "metadata_tool/register.html", {"form": form})


def verify_email(request, token):
    try:
        payload = signing.loads(token, salt="metadata_tool.email-verification", max_age=60 * 60 * 24 * 3)
        user = get_user_model().objects.get(pk=payload["user_id"], email=payload["email"])
    except (signing.BadSignature, signing.SignatureExpired, KeyError, get_user_model().DoesNotExist):
        return render(request, "metadata_tool/verification_invalid.html", status=400)

    lifecycle, _ = AccountLifecycle.objects.get_or_create(owner=user)
    if not lifecycle.email_verified:
        lifecycle.email_verified = True
        lifecycle.verified_at = timezone.now()
        lifecycle.save(update_fields=["email_verified", "verified_at"])
        user.is_active = True
        user.save(update_fields=["is_active"])
    return render(request, "metadata_tool/verification_complete.html")


def resend_verification(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        user = get_user_model().objects.filter(email__iexact=email, is_active=False).first()
        lifecycle = AccountLifecycle.objects.filter(owner=user, email_verified=False).first() if user else None
        if lifecycle:
            token = signing.dumps({"user_id": user.pk, "email": user.email}, salt="metadata_tool.email-verification")
            verification_url = request.build_absolute_uri(reverse("verify_email", args=[token]))
            send_mail(
                "E-Mail-Adresse bestätigen",
                f"Bitte bestätige deine E-Mail-Adresse über diesen Link: {verification_url}",
                None,
                [user.email],
                fail_silently=False,
            )
        return render(request, "metadata_tool/resend_verification_sent.html")
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET", "POST"])
    return render(request, "metadata_tool/resend_verification.html")


def login_view(request):
    form = AccountLoginForm(request=request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        next_url = request.POST.get("next") or request.GET.get("next")
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            return redirect(next_url)
        return redirect("index")
    return render(request, "metadata_tool/login.html", {"form": form, "next": request.GET.get("next", "")})


@login_required
def account_delete(request):
    if request.method != "POST":
        return render(request, "metadata_tool/account_delete.html")
    lifecycle = AccountLifecycle.objects.filter(owner=request.user, email_verified=True).first()
    if lifecycle is None:
        return render(request, "metadata_tool/account_delete.html", {
            "error": "Für die Löschbestätigung wird eine bestätigte E-Mail-Adresse benötigt.",
        }, status=400)

    token = signing.dumps({"user_id": request.user.pk, "email": request.user.email}, salt="metadata_tool.account-deletion")
    confirmation_url = request.build_absolute_uri(reverse("confirm_account_deletion", args=[token]))
    send_mail(
        "Kontolöschung bestätigen",
        f"Dein Konto und die gespeicherten Bilder werden endgültig gelöscht. Bestätige die Löschung innerhalb von 24 Stunden: {confirmation_url}",
        None,
        [request.user.email],
        fail_silently=False,
    )
    return render(request, "metadata_tool/account_delete_sent.html", {"email": request.user.email})


def confirm_account_deletion(request, token):
    try:
        payload = signing.loads(token, salt="metadata_tool.account-deletion", max_age=60 * 60 * 24)
        user = get_user_model().objects.get(pk=payload["user_id"], email=payload["email"])
    except (signing.BadSignature, signing.SignatureExpired, KeyError, get_user_model().DoesNotExist):
        return render(request, "metadata_tool/account_delete_invalid.html", status=400)

    if request.method == "POST":
        user.delete()
        _clear_uploads(request)
        logout(request)
        return render(request, "metadata_tool/account_deleted.html")
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET", "POST"])
    return render(request, "metadata_tool/account_delete_confirm.html", {"token": token})


def logout_view(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    _clear_uploads(request)
    logout(request)
    return redirect("login")


@login_required
def download_image(request, image_id):
    image = get_object_or_404(StoredImage, id=image_id, owner=request.user)
    content_type = mimetypes.guess_type(image.original_filename)[0] or "application/octet-stream"
    return _download(bytes(image.image_data), image.original_filename, content_type)


@login_required
def archive(request):
    return render(request, "metadata_tool/archive.html", {
        "saved_images": StoredImage.objects.filter(owner=request.user),
    })


@login_required
def delete_archive_image(request, image_id):
    image = get_object_or_404(StoredImage, id=image_id, owner=request.user)
    directory = _upload_dir(request)
    file_path = directory / image.storage_name
    if file_path.exists():
        file_path.unlink(missing_ok=True)
    image.delete()
    _clear_uploads(request)
    return redirect("archive")


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


@login_required
def index(request):
    if request.method == "POST" and request.POST.get("action") == "clear":
        _clear_uploads(request)
        return redirect("index")

    selected_name = request.GET.get("selected") or request.GET.get("load") or request.POST.get("selected")
    archived_image = None
    if request.method == "GET" and request.GET.get("load"):
        archived_image = StoredImage.objects.filter(
            owner=request.user,
            storage_name=request.GET["load"],
        ).first()
    if archived_image:
        _clear_uploads(request)
        directory = Path(tempfile.mkdtemp(prefix="ksw-meta-"))
        (directory / archived_image.storage_name).write_bytes(bytes(archived_image.image_data))
        request.session["upload_dir"] = str(directory)
    else:
        directory = _upload_dir(request)
    error = None
    metadata = {}

    if request.method == "POST" and request.FILES.getlist("images"):
        directory = _upload_dir(request)
        for uploaded in request.FILES.getlist("images"):
            safe_name = Path(uploaded.name).name
            if Path(safe_name).suffix.lower() in ALLOWED_EXTENSIONS:
                storage_name = safe_name
                if StoredImage.objects.filter(owner=request.user, storage_name=storage_name).exists():
                    stem = Path(safe_name).stem
                    suffix = Path(safe_name).suffix.lower()
                    storage_name = f"{stem}-{uuid.uuid4().hex[:8]}{suffix}"
                image_data = uploaded.read()
                StoredImage.objects.create(
                    owner=request.user,
                    original_filename=safe_name,
                    storage_name=storage_name,
                    image_data=image_data,
                )
                (directory / storage_name).write_bytes(image_data)
        return redirect("index")

    files = _file_context(directory)
    converted = _converted_context(request, directory)
    names = {file["key"] for file in files}
    if selected_name not in names:
        selected_name = files[0]["key"] if files else None
    selected_file = next((file for file in files if file["key"] == selected_name), None)
    preference, _ = UserPreference.objects.get_or_create(owner=request.user)
    current_scale = preference.preferred_scale
    if selected_file:
        stored = StoredImage.objects.filter(owner=request.user, storage_name=selected_file["key"]).first()
        if stored is not None:
            current_scale = stored.last_scale

    if request.method == "POST" and selected_file:
        try:
            action = request.POST.get("action")
            if action == "delete-all-selected":
                for file in files:
                    _delete_selected_image(request, file["key"])
                return redirect("index")
            if action == "batch":
                updated = []
                for file in files:
                    image_data = write_xmp_metadata(file["path"], _fields(request.POST))
                    _persist_image(request, file, image_data)
                    updated.append((f"{Path(file['name']).stem}-mit-xmp{Path(file['name']).suffix}", image_data))
                response = HttpResponse(create_zip(updated), content_type="application/zip")
                response["Content-Disposition"] = 'attachment; filename="bilder-mit-xmp.zip"'
                return response
            if action == "batch-resize":
                scale = request.POST.get("scale", "100")
                resized = [
                    (f"{Path(file['name']).stem}-{scale}prozent{Path(file['name']).suffix}", resize_image(file["path"], scale))
                    for file in files
                ]
                for filename, image_data in resized:
                    _archive_derived_image(request, filename, image_data, scale=scale)
                _save_preferred_scale(request, scale)
                response = HttpResponse(create_zip(resized), content_type="application/zip")
                response["Content-Disposition"] = 'attachment; filename="bilder-skaliert.zip"'
                return response
            if action == "batch-convert":
                target_format = request.POST.get("target_format", "png")
                converted_files = []
                for file in files:
                    data, suffix, _ = convert_image(file["path"], target_format)
                    filename = f"{Path(file['name']).stem}-konvertiert.{suffix}"
                    converted_files.append((filename, data))
                    _archive_derived_image(request, filename, data)
                response = HttpResponse(create_zip(converted_files), content_type="application/zip")
                response["Content-Disposition"] = 'attachment; filename="bilder-konvertiert.zip"'
                return response
            if action == "batch-remove":
                cleaned = [
                    (f"{Path(file['name']).stem}-ohne-metadaten{Path(file['name']).suffix}", remove_metadata(file["path"]))
                    for file in files
                ]
                for file, (_, image_data) in zip(files, cleaned):
                    _persist_image(request, file, image_data)
                response = HttpResponse(create_zip(cleaned), content_type="application/zip")
                response["Content-Disposition"] = 'attachment; filename="bilder-ohne-metadaten.zip"'
                return response
            if action == "single":
                image_data = write_xmp_metadata(selected_file["path"], _fields(request.POST))
                _persist_image(request, selected_file, image_data)
                return _download(image_data, f"{Path(selected_name).stem}-mit-xmp{Path(selected_name).suffix}", selected_file["mime"])
            if action == "delete-selected":
                _delete_selected_image(request, selected_name)
                return redirect("index")
            if action == "remove":
                image_data = remove_metadata(selected_file["path"])
                _persist_image(request, selected_file, image_data)
                return _download(image_data, f"{Path(selected_name).stem}-ohne-metadaten{Path(selected_name).suffix}", selected_file["mime"])
            if action == "resize":
                scale = request.POST.get("scale", "100")
                resized = resize_image(selected_file["path"], scale)
                resized_name = f"{Path(selected_file['name']).stem}-{scale}prozent{Path(selected_file['name']).suffix}"
                _archive_derived_image(request, resized_name, resized, scale=scale)
                _save_preferred_scale(request, scale)
                return _download(resized, resized_name, selected_file["mime"])
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
                    image_data = converted["path"].read_bytes()
                    _archive_derived_image(request, converted["name"], image_data)
                    for key in ("converted_path", "converted_name", "converted_mime", "show_converted"):
                        request.session.pop(key, None)
                    return _download(image_data, converted["name"], converted["mime"])
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
        "preferred_scale": preference.preferred_scale,
        "current_scale": current_scale,
    })


def _download(data, filename, content_type):
    response = HttpResponse(data, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response