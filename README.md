# KSW-Meta-daten

Streamlit-App zum Auslesen von XMP-Metadaten aus Bilddateien.

## Installation

### 1. ExifTool installieren

ExifTool liest XMP zuverlässig aus JPG, PNG, TIFF, WebP und weiteren Formaten.

Ubuntu/Debian:

```bash
sudo apt update
sudo apt install libimage-exiftool-perl
```

macOS:

```bash
brew install exiftool
```

Windows: ExifTool von <https://exiftool.org/> herunterladen und `exiftool.exe` in
einen Ordner im `PATH` legen.

### 2. Python-Umgebung vorbereiten

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Unter Windows lautet der Aktivierungsbefehl:

```powershell
.venv\Scripts\activate
```

### 3. App starten

```bash
streamlit run app.py
```

Danach die angezeigte lokale URL im Browser öffnen. Das Feld **Bilder hier ablegen
oder auswählen** ist automatisch eine Drag-and-drop-Fläche und akzeptiert mehrere
Bilder gleichzeitig.

Unter **Metadaten hinzufügen** stehen zwei Modi zur Verfügung:

- **Auf alle Bilder anwenden:** Die gleichen Angaben werden auf alle Bilder
	geschrieben. Die bearbeiteten Dateien werden gemeinsam als ZIP heruntergeladen.
- **Nur ein Bild manuell bearbeiten:** Ein Bild auswählen, vorhandene XMP-Daten
	prüfen oder ändern und dieses Bild einzeln herunterladen.

Titel, Beschreibung, Urheber, Copyright und Schlagwörter können ergänzt oder
geändert werden. Das hochgeladene Original bleibt unverändert. Im manuellen Modus
können die Metadaten zusätzlich als JSON exportiert oder vollständig aus dem
ausgewählten Bild entfernt werden.

## Hinweise

- Eine Bilddatei kann XMP-frei sein. Dann zeigt die App eine entsprechende Meldung.
- Die Datei wird nur temporär auf dem Server verarbeitet und nicht dauerhaft im
	Repository gespeichert.
- Die App zeigt zusätzlich alle von ExifTool gefundenen Metadaten im aufklappbaren
	Bereich an, nicht nur XMP.

# http://172.17.200.124:8501/
