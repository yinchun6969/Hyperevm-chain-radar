#!/usr/bin/env bash
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo "run with sudo"; exit 1; }
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP=/opt/hyperevm-chain-radar
USER=hyperevm-radar
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv python3-pip ca-certificates
id "$USER" >/dev/null 2>&1 || useradd --system --home "$APP" --shell /usr/sbin/nologin "$USER"
mkdir -p "$APP"
cp -R "$ROOT"/core "$ROOT"/chains "$ROOT"/adapters "$ROOT"/intelligence "$ROOT"/services "$APP"/
cp "$ROOT"/scanner.py "$ROOT"/supervisor.py "$ROOT"/doctor.py "$ROOT"/requirements.txt "$ROOT"/.env.example "$APP"/
python3 -m venv "$APP/.venv"
"$APP/.venv/bin/pip" install --upgrade pip >/dev/null
"$APP/.venv/bin/pip" install -r "$APP/requirements.txt"
[[ -f "$APP/.env" ]] || cp "$APP/.env.example" "$APP/.env"
chown -R "$USER:$USER" "$APP"; chmod 600 "$APP/.env"
cat >/etc/systemd/system/hyperevm-chain-radar.service <<EOF
[Unit]
Description=HyperEVM Chain Radar
After=network-online.target
Wants=network-online.target
[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$APP
EnvironmentFile=$APP/.env
ExecStart=$APP/.venv/bin/python $APP/supervisor.py
Restart=always
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true
ReadWritePaths=$APP
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now hyperevm-chain-radar.service
echo "Dashboard local: http://127.0.0.1:8788/zh"
echo "Doctor: sudo -u $USER $APP/.venv/bin/python $APP/doctor.py"
