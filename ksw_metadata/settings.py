import os
from pathlib import Path


# Hauptverzeichnis des Projekts.
BASE_DIR = Path(__file__).resolve().parent.parent

# Sicherheitsschlüssel für Django. In Produktionsumgebungen über eine Umgebungsvariable setzen.
SECRET_KEY = "django-insecure-ksw-metadata-development-key"

# Während der Entwicklung ausführliche Fehlermeldungen anzeigen.
DEBUG = True

# Erlaubte Hostnamen für lokale Zugriffe und den Ubuntu-Server.
allowed_hosts = os.environ.get(
    "DJANGO_ALLOWED_HOSTS",
    "localhost,127.0.0.1,testserver,172.17.200.124",
)
ALLOWED_HOSTS = [host.strip() for host in allowed_hosts.split(",") if host.strip()]

# Vertrauenswürdige Origins für CSRF-geschützte POST-Anfragen.
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "https://localhost:8000",
    "http://172.17.200.124:8000",
]

# Aktivierte Django-Anwendungen.
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "metadata_tool",
]

# Middleware verarbeitet Sicherheit, Sessions, allgemeine Requests und CSRF-Schutz.
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

# Zentrale URL-Konfiguration des Projekts.
ROOT_URLCONF = "ksw_metadata.urls"

# Konfiguration für Django-Templates.
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]

# Einstiegspunkt für WSGI-fähige Server.
WSGI_APPLICATION = "ksw_metadata.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Sprache und Zeitzone der Anwendung.
LANGUAGE_CODE = "de-de"
TIME_ZONE = "Europe/Berlin"

# Übersetzungen und Zeitzonenunterstützung aktivieren.
USE_I18N = True
USE_TZ = True

# Standardtyp für automatisch erzeugte Primärschlüssel.
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Der Browser erhält nur einen Sitzungsschlüssel; Sitzungsdaten bleiben serverseitig.
SESSION_ENGINE = "django.contrib.sessions.backends.db"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "index"
LOGOUT_REDIRECT_URL = "login"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

EMAIL_BACKEND = os.environ.get(
    "DJANGO_EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend" if DEBUG else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com" if not DEBUG else "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "true").lower() in {"1", "true", "yes"}
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "webmaster@localhost")