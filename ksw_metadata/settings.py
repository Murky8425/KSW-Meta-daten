from pathlib import Path


# Hauptverzeichnis des Projekts.
BASE_DIR = Path(__file__).resolve().parent.parent

# Sicherheitsschlüssel für Django. In Produktionsumgebungen über eine Umgebungsvariable setzen.
SECRET_KEY = "django-insecure-ksw-metadata-development-key"

# Während der Entwicklung ausführliche Fehlermeldungen anzeigen.
DEBUG = True

# Erlaubte Hostnamen für lokale Zugriffe.
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]

# Vertrauenswürdige Origins für CSRF-geschützte POST-Anfragen.
CSRF_TRUSTED_ORIGINS = ["http://localhost:8000", "https://localhost:8000"]

# Aktivierte Django-Anwendungen.
INSTALLED_APPS = ["metadata_tool"]

# Middleware verarbeitet Sicherheit, Sessions, allgemeine Requests und CSRF-Schutz.
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
]

# Zentrale URL-Konfiguration des Projekts.
ROOT_URLCONF = "ksw_metadata.urls"

# Konfiguration für Django-Templates.
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": ["django.template.context_processors.request"]},
}]

# Einstiegspunkt für WSGI-fähige Server.
WSGI_APPLICATION = "ksw_metadata.wsgi.application"

# SQLite-Datenbank. Die Anwendung verwendet aktuell vor allem signierte Cookie-Sessions.
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}

# Sprache und Zeitzone der Anwendung.
LANGUAGE_CODE = "de-de"
TIME_ZONE = "Europe/Berlin"

# Übersetzungen und Zeitzonenunterstützung aktivieren.
USE_I18N = True
USE_TZ = True

# Standardtyp für automatisch erzeugte Primärschlüssel.
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Sessions werden ohne Datenbank als signierte Cookies gespeichert.
SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"