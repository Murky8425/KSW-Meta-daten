import io
import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path


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


def create_zip(files):
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_name, file_data in files:
            zip_file.writestr(file_name, file_data)
    return archive.getvalue()