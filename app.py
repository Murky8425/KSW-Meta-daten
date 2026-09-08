import json
import io
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

import streamlit as st


st.set_page_config(page_title="XMP-Metadaten auslesen", layout="wide")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Space+Grotesk:wght@500;600;700&display=swap');

    :root {
        --ink: #17313b;
        --muted: #61747a;
        --paper: #f6f3ed;
        --panel: #fffdf9;
        --line: #d8e1df;
        --teal: #087f79;
        --teal-dark: #075d5b;
        --coral: #e76f51;
    }

    .stApp {
        background: var(--paper);
        color: var(--ink);
        font-family: 'DM Sans', sans-serif;
    }

    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stAppViewContainer"] > .main { background: transparent; }
    .block-container { max-width: 1180px; padding: 3rem 2rem 5rem; }

    h1, h2, h3, [data-testid="stMarkdownContainer"] h1,
    [data-testid="stMarkdownContainer"] h2,
    [data-testid="stMarkdownContainer"] h3 {
        color: var(--ink);
        font-family: 'Space Grotesk', sans-serif;
        letter-spacing: 0;
    }

    h1 { font-size: clamp(2.3rem, 5vw, 4.4rem); line-height: .98; margin: 0; }
    h2 { margin-top: 2rem; }
    p, label, .stCaption { color: var(--muted); }

    .hero {
        background: linear-gradient(120deg, #e4f1ed 0%, #fffdf9 62%, #f9dfd3 100%);
        border: 1px solid var(--line);
        border-radius: 18px;
        padding: 2.2rem 2.4rem;
        margin-bottom: 1.6rem;
        box-shadow: 0 18px 45px rgba(23, 49, 59, .08);
    }
    .eyebrow {
        color: var(--coral);
        font-size: .78rem;
        font-weight: 700;
        letter-spacing: .14em;
        text-transform: uppercase;
        margin-bottom: .7rem;
    }
    .hero-copy { max-width: 620px; font-size: 1.05rem; margin: 1rem 0 0; }

    [data-testid="stFileUploader"] {
        background: var(--panel);
        border: 2px dashed #9cc6c0;
        border-radius: 14px;
        padding: .6rem;
        transition: border-color .2s ease, background .2s ease;
    }
    [data-testid="stFileUploader"]:hover {
        background: #f2fbf8;
        border-color: var(--teal);
    }
    [data-testid="stFileUploaderDropzoneInstructions"] svg { fill: var(--teal); }

    [data-testid="stForm"], [data-testid="stExpander"] {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 14px;
    }
    [data-testid="stForm"] { padding: .35rem .8rem .8rem; }
    [data-testid="stRadio"] > div { gap: .7rem; }
    [data-testid="stRadio"] label {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 10px;
        padding: .55rem .8rem;
    }
    [data-testid="stImage"] { border-radius: 10px; overflow: hidden; }

    .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
        border: 0;
        border-radius: 9px;
        background: var(--teal);
        color: #ffffff !important;
        font-weight: 700;
        padding: .65rem 1rem;
        transition: background .2s ease, transform .2s ease;
    }
    .stButton > button *, .stDownloadButton > button *, .stFormSubmitButton > button * {
        color: #ffffff !important;
    }
    .stButton > button:hover, .stDownloadButton > button:hover,
    .stFormSubmitButton > button:hover {
        background: var(--teal-dark);
        color: #ffffff !important;
        transform: translateY(-1px);
    }
    [data-testid="stAlert"] { border-radius: 10px; }
    </style>
    """,
    unsafe_allow_html=True,
)


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


def create_zip(files):
    """Bündelt mehrere bearbeitete Bilddateien in einer ZIP-Datei."""
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_name, file_data in files:
            zip_file.writestr(file_name, file_data)
    return archive.getvalue()


st.markdown(
    """
    <section class="hero">
        <div class="eyebrow">Bildarchiv · Metadaten-Werkzeug</div>
        <h1>XMP sichtbar machen.<br>Sauber weitergeben.</h1>
        <p class="hero-copy">Bilder prüfen, Metadaten ergänzen und fertige Dateien im Originalformat herunterladen.</p>
    </section>
    """,
    unsafe_allow_html=True,
)

uploaded_files = st.file_uploader(
    "Bilder hier ablegen oder auswählen",
    type=["jpg", "jpeg", "png", "tif", "tiff", "webp", "heic", "avif"],
    accept_multiple_files=True,
)

if not uploaded_files:
    st.info("Unterstützte Formate: JPG, PNG, TIFF, WebP, HEIC und AVIF.")
else:
    st.markdown(f"**{len(uploaded_files)} Bild(er) ausgewählt** · bereit zur Bearbeitung")
    preview_columns = st.columns(min(len(uploaded_files), 4))
    for index, uploaded_file in enumerate(uploaded_files):
        with preview_columns[index % len(preview_columns)]:
            st.image(uploaded_file, caption=uploaded_file.name, use_container_width=True)

    st.subheader("Metadaten hinzufügen")
    mode = st.radio(
        "Bearbeitungsart",
        ["Auf alle Bilder anwenden", "Nur ein Bild manuell bearbeiten"],
        horizontal=True,
    )

    if mode == "Auf alle Bilder anwenden":
        st.write("Die gleichen Angaben werden in jedes ausgewählte Bild geschrieben.")
        with st.form("batch_xmp_editor"):
            title = st.text_input("Titel")
            description = st.text_area("Beschreibung")
            creator = st.text_input("Urheber / Autor")
            rights = st.text_input("Copyright / Rechte")
            keywords = st.text_input(
                "Schlagwörter",
                help="Mehrere Schlagwörter mit Komma trennen.",
            )
            save_batch = st.form_submit_button("Metadaten auf alle Bilder anwenden")

        if save_batch:
            fields = {
                "XMP-dc:Title": title.strip(),
                "XMP-dc:Description": description.strip(),
                "XMP-dc:Creator": creator.strip(),
                "XMP-dc:Rights": rights.strip(),
                "XMP-dc:Subject": [keyword.strip() for keyword in keywords.split(",") if keyword.strip()],
            }
            try:
                updated_files = [
                    (f"{Path(image.name).stem}-mit-xmp{Path(image.name).suffix}",
                     write_xmp_metadata(image, fields))
                    for image in uploaded_files
                ]
                archive = create_zip(updated_files)
            except (RuntimeError, ValueError) as error:
                st.error(str(error))
            else:
                st.success(f"Metadaten wurden auf {len(updated_files)} Bilder angewendet.")
                st.download_button(
                    "Alle bearbeiteten Bilder als ZIP herunterladen",
                    data=archive,
                    file_name="bilder-mit-xmp.zip",
                    mime="application/zip",
                )
    else:
        selected_name = st.selectbox(
            "Bild für die manuelle Bearbeitung",
            [image.name for image in uploaded_files],
        )
        selected_image = next(image for image in uploaded_files if image.name == selected_name)
        try:
            metadata = read_xmp_metadata(selected_image)
        except (RuntimeError, ValueError, json.JSONDecodeError) as error:
            st.error(str(error))
        else:
            xmp_metadata = {
                key: value for key, value in metadata.items() if key.startswith("XMP")
            }
            if xmp_metadata:
                st.subheader("XMP-Metadaten des ausgewählten Bildes")
                st.dataframe(
                    [{"Feld": key, "Wert": str(value)} for key, value in xmp_metadata.items()],
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
                file_name=f"{Path(selected_image.name).stem}-metadaten.json",
                mime="application/json",
            )

            with st.form("single_xmp_editor"):
                title = st.text_input("Titel", value=str(metadata.get("XMP-dc:Title", "")))
                description = st.text_area("Beschreibung", value=str(metadata.get("XMP-dc:Description", "")))
                creator = st.text_input("Urheber / Autor", value=str(metadata.get("XMP-dc:Creator", "")))
                rights = st.text_input("Copyright / Rechte", value=str(metadata.get("XMP-dc:Rights", "")))
                keywords = st.text_input("Schlagwörter", help="Mehrere Schlagwörter mit Komma trennen.")
                save_single = st.form_submit_button("Nur dieses Bild bearbeiten")

            if save_single:
                fields = {
                    "XMP-dc:Title": title.strip(),
                    "XMP-dc:Description": description.strip(),
                    "XMP-dc:Creator": creator.strip(),
                    "XMP-dc:Rights": rights.strip(),
                    "XMP-dc:Subject": [keyword.strip() for keyword in keywords.split(",") if keyword.strip()],
                }
                try:
                    updated_file = write_xmp_metadata(selected_image, fields)
                except (RuntimeError, ValueError) as error:
                    st.error(str(error))
                else:
                    st.success("Das ausgewählte Bild wurde bearbeitet.")
                    st.download_button(
                        "Bearbeitetes Bild herunterladen",
                        data=updated_file,
                        file_name=f"{Path(selected_image.name).stem}-mit-xmp{Path(selected_image.name).suffix}",
                        mime=selected_image.type or "application/octet-stream",
                    )

        st.subheader("Metadaten aus ausgewähltem Bild entfernen")
        st.write("Erstellt eine neue Kopie ohne EXIF-, XMP- und weitere eingebettete Metadaten.")
        if st.button("Alle Metadaten entfernen"):
            try:
                clean_file = remove_metadata(selected_image)
            except (RuntimeError, ValueError) as error:
                st.error(str(error))
            else:
                st.success("Eine Kopie ohne Metadaten wurde erstellt.")
                st.download_button(
                    "Bild ohne Metadaten herunterladen",
                    data=clean_file,
                    file_name=f"{Path(selected_image.name).stem}-ohne-metadaten{Path(selected_image.name).suffix}",
                    mime=selected_image.type or "application/octet-stream",
                )