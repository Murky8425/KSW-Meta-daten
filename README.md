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

Danach die angezeigte lokale URL im Browser öffnen. Das Feld **Bild hier ablegen
oder auswählen** ist automatisch eine Drag-and-drop-Fläche. Nach dem Upload werden
alle Felder aus dem XMP-Bereich angezeigt. Über **Metadaten als JSON herunterladen**
kann die Ausgabe gespeichert werden. Im Formular darunter können Titel,
Beschreibung, Urheber, Copyright und Schlagwörter ergänzt oder geändert werden.
Mit **Neue Bilddatei erzeugen** wird eine neue Datei erstellt und zum Download
angeboten. Das hochgeladene Original bleibt unverändert. Zusätzlich kann mit
**Alle Metadaten entfernen** eine Kopie ohne EXIF-, XMP- und weitere eingebettete
Metadaten erzeugt und heruntergeladen werden.

## Hinweise

- Eine Bilddatei kann XMP-frei sein. Dann zeigt die App eine entsprechende Meldung.
- Die Datei wird nur temporär auf dem Server verarbeitet und nicht dauerhaft im
	Repository gespeichert.
- Die App zeigt zusätzlich alle von ExifTool gefundenen Metadaten im aufklappbaren
	Bereich an, nicht nur XMP.
