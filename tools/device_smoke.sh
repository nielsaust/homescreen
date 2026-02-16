#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[device-smoke] root: $ROOT_DIR"

python3 tools/doctor.py --device
python3 tools/smoke.py

if command -v systemctl >/dev/null 2>&1; then
  echo "[device-smoke] checking systemd status"
  for unit in homescreen.service homescreen; do
    if systemctl list-unit-files | grep -q "^${unit}"; then
      systemctl --no-pager --full status "$unit" | sed -n '1,12p' || true
      break
    fi
  done
else
  echo "[device-smoke][warn] systemctl not available"
fi

python3 - <<'PY'
import json
import socket
from pathlib import Path

root = Path(".")
settings_path = root / "local_config" / "settings.json"
if not settings_path.exists():
    print("[device-smoke][warn] settings file missing; skipping broker socket check")
    raise SystemExit(0)

data = json.loads(settings_path.read_text())
broker = data.get("mqtt_broker")
port = int(data.get("mqtt_port", 1883))
if not broker:
    print("[device-smoke][warn] mqtt_broker missing; skipping socket check")
    raise SystemExit(0)

try:
    with socket.create_connection((broker, port), timeout=3):
        print(f"[device-smoke] mqtt broker reachable at {broker}:{port}")
except OSError as exc:
    print(f"[device-smoke][warn] mqtt broker not reachable at {broker}:{port} ({exc})")
PY

echo "[device-smoke] done"
