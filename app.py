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