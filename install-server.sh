#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/home/rh-admin/KSW-Meta-daten"
SERVICE_NAME="ksw-metadata"

if [[ "$(id -u)" -ne 0 ]]; then
    echo "Bitte mit sudo ausführen: sudo ./install-server.sh" >&2
    exit 1
fi

apt-get update
apt-get install -y python3 python3-venv python3-pip libimage-exiftool-perl docker.io
systemctl enable --now docker

if ! id rh-admin >/dev/null 2>&1; then
    echo "Der Benutzer rh-admin wurde nicht gefunden." >&2
    exit 1
fi

usermod -aG docker rh-admin

python3 -m venv "$PROJECT_DIR/.venv"
"$PROJECT_DIR/.venv/bin/pip" install --upgrade pip
"$PROJECT_DIR/.venv/bin/pip" install -r "$PROJECT_DIR/requirements.txt"

install -m 0755 "$PROJECT_DIR/start-server.sh" "/usr/local/bin/$SERVICE_NAME"
install -m 0644 "$PROJECT_DIR/$SERVICE_NAME.service" "/etc/systemd/system/$SERVICE_NAME.service"
systemctl daemon-reload
systemctl enable "$SERVICE_NAME.service"
systemctl start "$SERVICE_NAME.service"

echo "Installation abgeschlossen. Status:"
systemctl --no-pager --full status "$SERVICE_NAME.service" || true