#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/home/rh-admin/KSW-Meta-daten"
ORACLE_CONTAINER="oracle-free"
ORACLE_NAME="FREEPDB1"
ORACLE_USER="Murky"
ORACLE_PASSWORD="Start1234567"
ORACLE_HOST="127.0.0.1"
ORACLE_PORT="1521"
APP_HOST="0.0.0.0"
APP_PORT="8000"

cd "$PROJECT_DIR"

if ! docker inspect "$ORACLE_CONTAINER" >/dev/null 2>&1; then
    docker run -d \
        --name "$ORACLE_CONTAINER" \
        -p 1521:1521 \
        -e ORACLE_PASSWORD="$ORACLE_PASSWORD" \
        -e APP_USER="$ORACLE_USER" \
        -e APP_USER_PASSWORD="$ORACLE_PASSWORD" \
        gvenzl/oracle-free:23-slim
elif [[ "$(docker inspect -f '{{.State.Status}}' "$ORACLE_CONTAINER")" != "running" ]]; then
    docker start "$ORACLE_CONTAINER"
fi

for attempt in {1..60}; do
    if (echo >/dev/tcp/"$ORACLE_HOST"/"$ORACLE_PORT") >/dev/null 2>&1; then
        break
    fi
    if [[ "$attempt" == 60 ]]; then
        echo "Oracle ist nach 120 Sekunden nicht erreichbar." >&2
        exit 1
    fi
    sleep 2
done

source .venv/bin/activate
export ORACLE_NAME ORACLE_USER ORACLE_PASSWORD ORACLE_HOST ORACLE_PORT
python manage.py migrate --noinput
exec python manage.py runserver "$APP_HOST:$APP_PORT"