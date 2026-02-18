#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi

.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

POST_PULL_ARGS=()
if [[ -f "local_config/menu.json" ]] && [[ -t 0 ]]; then
  read -r -p "[bootstrap] local_config/menu.json exists. Overwrite with default menu? (y/N): " overwrite_menu
  case "${overwrite_menu:-}" in
    y|Y|yes|YES)
      POST_PULL_ARGS+=(--force-menu-overwrite)
      ;;
  esac
fi
.venv/bin/python tools/post_pull_setup.py "${POST_PULL_ARGS[@]}"

echo "[bootstrap] done"
echo "[bootstrap] if tkinter is missing on your OS, install system package python3-tk"
