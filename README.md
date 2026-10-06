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

### Account-E-Mail und Inaktivität

Bei der Registrierung ist eine E-Mail-Adresse erforderlich. Das Konto wird erst
nach Bestätigung des Links aktiviert. Nach fünf Kalendermonaten ohne Anmeldung
versendet der tägliche Account-Lauf eine Warnung. Nach sechs Monaten wird der
Login gesperrt und ein einmaliger Recovery-Code versendet. Mit Benutzername,
Passwort und Recovery-Code kann das Konto wieder freigeschaltet werden. Wie
gewünscht bleiben gesperrte Konten und Bilder unbegrenzt gespeichert, bis das
Konto wiederhergestellt oder manuell per bestätigtem E-Mail-Link endgültig
gelöscht wird. Die manuelle Löschung entfernt auch die persönlichen Bilder.

Im lokalen Entwicklungsmodus werden E-Mails im Server-Terminal ausgegeben. Auf
dem Server wird SMTP automatisch aktiviert, sobald `EMAIL_HOST_USER` gesetzt
ist. Gmail-SMTP wird verwendet. Lege dort `/etc/ksw-metadata.env` an und
trage ein Gmail-App-Passwort ein (nicht das normale Google-Passwort):

```ini
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_HOST_USER=dein-konto@gmail.com
EMAIL_HOST_PASSWORD=DEIN_GOOGLE_APP_PASSWORT
DEFAULT_FROM_EMAIL=dein-konto@gmail.com
```

Die Datei enthält ein Geheimnis und darf nicht ins Git-Repository. Beschränke
ihre Berechtigungen auf root und den Dienstbenutzer. Nach dem Anlegen oder
Ändern müssen Webdienst und täglicher Timer neu gestartet werden:

```bash
sudo chmod 640 /etc/ksw-metadata.env
sudo chown root:rh-admin /etc/ksw-metadata.env
sudo systemctl restart ksw-metadata.service
sudo systemctl enable --now ksw-metadata-account-maintenance.timer
sudo systemctl list-timers ksw-metadata-account-maintenance.timer
```

`install-server.sh` installiert und aktiviert den täglichen Timer. Für einen
bereits eingerichteten Server müssen die neuen Dateien zunächst per Git
übertragen und anschließend `sudo ./install-server.sh` ausgeführt werden.

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

