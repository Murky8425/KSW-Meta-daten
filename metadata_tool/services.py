import io
import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

from PIL import Image


def _exiftool():
    command = shutil.which("exiftool")
    if command is None:
        raise RuntimeError("ExifTool wurde nicht gefunden. Installiere es mit 'sudo apt install libimage-exiftool-perl'.")
    return command


def read_xmp_metadata(file_path):
    result = subprocess.run([_exiftool(), "-j", "-G1", "-a", "-s", str(file_path)], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or "ExifTool konnte die Datei nicht lesen.")
    parsed = json.loads(result.stdout)
    return parsed[0] if parsed else {}


def write_xmp_metadata(file_path, fields):
    suffix = Path(file_path).suffix or ".bin"
    with tempfile.TemporaryDirectory() as temp_dir:
        output = Path(temp_dir) / f"{Path(file_path).stem}-mit-xmp{suffix}"
        arguments = [_exiftool(), "-o", str(output)]
        for tag, value in fields.items():
            if value:
                if tag == "XMP-dc:Subject":
                    arguments.append(f"-{tag}=")
                    arguments.extend(f"-{tag}={keyword}" for keyword in value)
                else:
                    arguments.append(f"-{tag}={value}")
        arguments.append(str(file_path))
        result = subprocess.run(arguments, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise ValueError(result.stderr.strip() or "ExifTool konnte die Metadaten nicht schreiben.")
        return output.read_bytes()


def remove_metadata(file_path):
    suffix = Path(file_path).suffix or ".bin"
    with tempfile.TemporaryDirectory() as temp_dir:
        output = Path(temp_dir) / f"{Path(file_path).stem}-ohne-metadaten{suffix}"
        result = subprocess.run([_exiftool(), "-all=", "-o", str(output), str(file_path)], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise ValueError(result.stderr.strip() or "ExifTool konnte die Metadaten nicht entfernen.")
        return output.read_bytes()


def resize_image(file_path, scale):
    try:
        scale = int(scale)
    except (TypeError, ValueError) as exc:
        raise ValueError("Die Bildgröße muss zwischen 10 und 200 Prozent liegen.") from exc
    if not 10 <= scale <= 200:
        raise ValueError("Die Bildgröße muss zwischen 10 und 200 Prozent liegen.")

    suffix = Path(file_path).suffix.lower()
    format_by_suffix = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".tif": "TIFF", ".tiff": "TIFF", ".webp": "WEBP"}
    image_format = format_by_suffix.get(suffix)
    if image_format is None:
        raise ValueError("Dieses Bildformat kann nicht direkt verkleinert werden.")

    with Image.open(file_path) as image:
        width = max(1, round(image.width * scale / 100))
        height = max(1, round(image.height * scale / 100))
        resized = image.resize((width, height), Image.Resampling.LANCZOS)
        output = io.BytesIO()
        save_image = resized.convert("RGB") if image_format == "JPEG" and resized.mode not in {"RGB", "L"} else resized
        save_options = {"quality": 92} if image_format in {"JPEG", "WEBP"} else {}
        save_image.save(output, format=image_format, **save_options)
    return output.getvalue()


def create_zip(files):
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_name, file_data in files:
            zip_file.writestr(file_name, file_data)
    return archive.getvalue()