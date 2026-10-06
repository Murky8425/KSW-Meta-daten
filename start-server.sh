#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/home/rh-admin/KSW-Meta-daten"
APP_HOST="0.0.0.0"
APP_PORT="8000"

cd "$PROJECT_DIR"

source .venv/bin/activate
python manage.py migrate --noinput
exec python manage.py runserver "$APP_HOST:$APP_PORT"