# KSW-Meta-daten

Django-Anwendung zum Auslesen und Bearbeiten von XMP-Metadaten in Bilddateien.

## Installation

### Oracle Database konfigurieren

Die Anwendung verwendet Oracle als Standarddatenbank. Vor dem Start müssen die
Verbindungsvariablen gesetzt werden:

```bash
export ORACLE_NAME="FREEPDB1"
export ORACLE_USER="Murky"
export ORACLE_PASSWORD="Start1234567"
export ORACLE_HOST="localhost"
export ORACLE_PORT="1521"
# Optional: kompletter Easy-Connect-DSN, z. B. localhost:1521/FREEPDB1
# export ORACLE_DSN="localhost:1521/FREEPDB1"
python manage.py migrate
```

`ORACLE_NAME` ist der Oracle-Service-Name. Die Tabelle
`ausgelesene_metadaten` speichert pro Bild den SHA-256-Hash, die zentralen XMP-
Felder und das vollständige von ExifTool gelieferte Metadaten-JSON. Änderungen
an derselben Bilddatei aktualisieren den vorhandenen Datensatz.

Für Oracle Free im Docker-Container können die Werte so gesetzt werden:

```bash
docker run -d --name oracle-free -p 1521:1521 \
	-e ORACLE_PASSWORD="Start1234567" \
	-e APP_USER="Murky" \
	-e APP_USER_PASSWORD="Start1234567" \
	gvenzl/oracle-free:23-slim
```

Das Datenbankpasswort des App-Benutzers wird anschließend für Django als
`ORACLE_PASSWORD` gesetzt. `APP_USER` und `APP_USER_PASSWORD` konfigurieren
den Oracle-Container; `ORACLE_USER` und `ORACLE_PASSWORD` konfigurieren Django.

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

Danach <http://127.0.0.1:8000/> im Browser öffnen. Das Upload-Feld akzeptiert
mehrere Bilder gleichzeitig.

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
- Die Datei wird nur temporär auf dem Server verarbeitet und nicht dauerhaft im
	Repository gespeichert.
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

