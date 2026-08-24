#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
APP="$HOME/hyperevm-chain-radar"
pkg update -y
pkg install -y python
mkdir -p "$APP"
cp -R "$ROOT"/core "$ROOT"/chains "$ROOT"/adapters "$ROOT"/intelligence "$ROOT"/services "$APP"/
cp "$ROOT"/scanner.py "$ROOT"/supervisor.py "$ROOT"/doctor.py "$ROOT"/requirements.txt "$ROOT"/.env.example "$APP"/
python -m venv "$APP/.venv"
"$APP/.venv/bin/pip" install --upgrade pip >/dev/null
"$APP/.venv/bin/pip" install -r "$APP/requirements.txt"
[[ -f "$APP/.env" ]] || cp "$APP/.env.example" "$APP/.env"
cat >"$APP/start-termux.sh" <<'SH'
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
[[ -f supervisor.pid ]] && kill -0 "$(cat supervisor.pid)" 2>/dev/null && { echo "already running"; exit 0; }
command -v termux-wake-lock >/dev/null 2>&1 && termux-wake-lock || true
nohup .venv/bin/python supervisor.py >radar.log 2>&1 &
echo $! > supervisor.pid
echo "HyperEVM Chain Radar started PID=$(cat supervisor.pid)"
echo "Dashboard: http://127.0.0.1:8788/zh"
SH
cat >"$APP/stop-termux.sh" <<'SH'
#!/data/data/com.termux/files/usr/bin/bash
cd "$(dirname "$0")"
if [[ -f supervisor.pid ]]; then kill "$(cat supervisor.pid)" 2>/dev/null || true; rm -f supervisor.pid; fi
command -v termux-wake-unlock >/dev/null 2>&1 && termux-wake-unlock || true
SH
chmod +x "$APP"/*.sh
cd "$APP"
.venv/bin/python doctor.py || true
echo "Installed: $APP"
echo "Edit $APP/.env then: cd $APP && bash start-termux.sh"
