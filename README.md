# KSW-Meta-daten

Django-Anwendung zum Auslesen und Bearbeiten von XMP-Metadaten in Bilddateien.

## Installation

### SQLite-Datenbank

Die Anwendung verwendet SQLite. Benutzerkonten, persönliche Einstellungen und
hochgeladene Bilddateien werden nach der Migration in `db.sqlite3` gespeichert:

```bash
python manage.py migrate
```

Ein Konto kann über **Registrieren** auf der Website erstellt werden. Django
speichert Passwörter nur gehasht; Bilder und Downloads gehören jeweils dem
angemeldeten Benutzer.

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

### 3. Django-Anwendung starten

```bash
python manage.py runserver
```

Danach <http://127.0.0.1:8000/> im Browser öffnen, ein Konto registrieren und
anmelden. Das Upload-Feld akzeptiert mehrere Bilder gleichzeitig. Unter **Mein
Bildarchiv** lassen sich die eigenen Originale später erneut herunterladen.

Unter **Metadaten hinzufügen** stehen zwei Bereiche zur Verfügung:

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
- Originalbilder werden in der lokalen SQLite-Datenbank gespeichert. Die Datei
  `db.sqlite3` sollte regelmäßig gesichert und nicht öffentlich bereitgestellt
  werden.
- Die zuletzt verwendete Bildskalierung wird im Benutzerkonto gespeichert und
  beim nächsten Besuch wieder in den Reglern angezeigt.
- Die App zeigt zusätzlich alle von ExifTool gefundenen Metadaten im aufklappbaren
	Bereich an, nicht nur XMP.

SELECT
    id,
    filename,
    title,
    creator,
    rights,
    extracted_at
FROM ausgelesene_metadaten;

