import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import streamlit as st


st.set_page_config(page_title="XMP-Metadaten auslesen", layout="wide")


def read_xmp_metadata(uploaded_file):
    """Liest XMP und andere Metadaten mit ExifTool als strukturiertes JSON."""
    exiftool = shutil.which("exiftool")
    if exiftool is None:
        raise RuntimeError(
            "ExifTool wurde nicht gefunden. Installiere es mit "
            "'sudo apt install libimage-exiftool-perl' und starte die App neu."
        )

    suffix = Path(uploaded_file.name).suffix or ".bin"
    with tempfile.NamedTemporaryFile(suffix=suffix) as image_file:
        image_file.write(uploaded_file.getvalue())
        image_file.flush()
        result = subprocess.run(
            [exiftool, "-j", "-G1", "-a", "-s", str(image_file.name)],
            capture_output=True,
            text=True,
            check=False,
        )

    if result.returncode != 0:
        message = result.stderr.strip() or "ExifTool konnte die Datei nicht lesen."
        raise ValueError(message)

    parsed = json.loads(result.stdout)
    return parsed[0] if parsed else {}


def write_xmp_metadata(uploaded_file, fields):
    """Schreibt die bearbeiteten XMP-Felder in eine neue Bilddatei."""
    exiftool = shutil.which("exiftool")
    if exiftool is None:
        raise RuntimeError(
            "ExifTool wurde nicht gefunden. Installiere es mit "
            "'sudo apt install libimage-exiftool-perl' und starte die App neu."
        )

    suffix = Path(uploaded_file.name).suffix or ".bin"
    with tempfile.TemporaryDirectory() as temp_dir:
        source = Path(temp_dir) / f"original{suffix}"
        output = Path(temp_dir) / f"{Path(uploaded_file.name).stem}-mit-xmp{suffix}"
        source.write_bytes(uploaded_file.getvalue())

        arguments = [exiftool, "-o", str(output)]
        for tag, value in fields.items():
            if value:
                if tag == "XMP-dc:Subject":
                    arguments.append(f"-{tag}=")
                    arguments.extend(f"-{tag}={keyword}" for keyword in value)
                else:
                    arguments.append(f"-{tag}={value}")
        arguments.append(str(source))

        result = subprocess.run(
            arguments,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            message = result.stderr.strip() or "ExifTool konnte die Metadaten nicht schreiben."
            raise ValueError(message)
        return output.read_bytes()


def remove_metadata(uploaded_file):
    """Erstellt eine Kopie des Bildes ohne eingebettete Metadaten."""
    exiftool = shutil.which("exiftool")
    if exiftool is None:
        raise RuntimeError(
            "ExifTool wurde nicht gefunden. Installiere es mit "
            "'sudo apt install libimage-exiftool-perl' und starte die App neu."
        )

    suffix = Path(uploaded_file.name).suffix or ".bin"
    with tempfile.TemporaryDirectory() as temp_dir:
        source = Path(temp_dir) / f"original{suffix}"
        output = Path(temp_dir) / f"{Path(uploaded_file.name).stem}-ohne-metadaten{suffix}"
        source.write_bytes(uploaded_file.getvalue())
        result = subprocess.run(
            [exiftool, "-all=", "-o", str(output), str(source)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            message = result.stderr.strip() or "ExifTool konnte die Metadaten nicht entfernen."
            raise ValueError(message)
        return output.read_bytes()


st.title("XMP-Metadaten auslesen")
st.write("Bild ablegen, Metadaten prüfen und bei Bedarf als JSON herunterladen.")

uploaded_file = st.file_uploader(
    "Bild hier ablegen oder auswählen",
    type=["jpg", "jpeg", "png", "tif", "tiff", "webp", "heic", "avif"],
)

if uploaded_file is None:
    st.info("Unterstützte Formate: JPG, PNG, TIFF, WebP, HEIC und AVIF.")
else:
    st.image(uploaded_file, caption=uploaded_file.name, use_container_width=True)

    try:
        metadata = read_xmp_metadata(uploaded_file)
    except (RuntimeError, ValueError, json.JSONDecodeError) as error:
        st.error(str(error))
    else:
        xmp_metadata = {
            key: value for key, value in metadata.items() if key.startswith("XMP")
        }

        if xmp_metadata:
            st.subheader("XMP-Metadaten")
            st.dataframe(
                [{"Feld": key, "Wert": str(value)}
                 for key, value in xmp_metadata.items()],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.warning("Diese Bilddatei enthält keine erkannten XMP-Metadaten.")

        with st.expander("Alle gefundenen Metadaten anzeigen"):
            st.json(metadata)

        st.download_button(
            "Metadaten als JSON herunterladen",
            data=json.dumps(metadata, ensure_ascii=False, indent=2),
            file_name=f"{Path(uploaded_file.name).stem}-metadaten.json",
            mime="application/json",
        )

        st.subheader("Eigene XMP-Metadaten hinzufügen oder ändern")
        with st.form("xmp_editor"):
            title = st.text_input("Titel", value=str(metadata.get("XMP-dc:Title", "")))
            description = st.text_area(
                "Beschreibung",
                value=str(metadata.get("XMP-dc:Description", "")),
            )
            creator = st.text_input("Urheber / Autor", value=str(metadata.get("XMP-dc:Creator", "")))
            rights = st.text_input("Copyright / Rechte", value=str(metadata.get("XMP-dc:Rights", "")))
            keywords = st.text_input(
                "Schlagwörter",
                value="",
                help="Mehrere Schlagwörter mit Komma trennen.",
            )
            save_metadata = st.form_submit_button("Neue Bilddatei erzeugen")

        if save_metadata:
            fields = {
                "XMP-dc:Title": title.strip(),
                "XMP-dc:Description": description.strip(),
                "XMP-dc:Creator": creator.strip(),
                "XMP-dc:Rights": rights.strip(),
                "XMP-dc:Subject": [keyword.strip() for keyword in keywords.split(",") if keyword.strip()],
            }
            try:
                updated_file = write_xmp_metadata(uploaded_file, fields)
            except (RuntimeError, ValueError) as error:
                st.error(str(error))
            else:
                st.success("Die neue Bilddatei wurde erstellt.")
                st.download_button(
                    "Bilddatei mit XMP herunterladen",
                    data=updated_file,
                    file_name=f"{Path(uploaded_file.name).stem}-mit-xmp{Path(uploaded_file.name).suffix}",
                    mime=uploaded_file.type or "application/octet-stream",
                )

        st.subheader("Metadaten aus Bild entfernen")
        st.write("Erstellt eine neue Kopie ohne EXIF-, XMP- und weitere eingebettete Metadaten.")
        if st.button("Alle Metadaten entfernen"):
            try:
                clean_file = remove_metadata(uploaded_file)
            except (RuntimeError, ValueError) as error:
                st.error(str(error))
            else:
                st.success("Eine Kopie ohne Metadaten wurde erstellt.")
                st.download_button(
                    "Bild ohne Metadaten herunterladen",
                    data=clean_file,
                    file_name=f"{Path(uploaded_file.name).stem}-ohne-metadaten{Path(uploaded_file.name).suffix}",
                    mime=uploaded_file.type or "application/octet-stream",
                )