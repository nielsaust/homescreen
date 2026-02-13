#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${1:-$PWD}"
BRANCH="${2:-main}"
SERVICE_NAME="${3:-homescreen.service}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "[deploy] app_dir=${APP_DIR}"
echo "[deploy] branch=${BRANCH}"
echo "[deploy] service=${SERVICE_NAME}"

cd "${APP_DIR}"

echo "[deploy] fetching latest branch"
git fetch origin "${BRANCH}"

LOCAL_SHA="$(git rev-parse HEAD)"
REMOTE_SHA="$(git rev-parse "origin/${BRANCH}")"

if [[ "${LOCAL_SHA}" == "${REMOTE_SHA}" ]]; then
  echo "[deploy] already up to date (${LOCAL_SHA})"
else
  echo "[deploy] updating ${LOCAL_SHA} -> ${REMOTE_SHA}"
  git pull --ff-only origin "${BRANCH}"
fi

if [[ ! -d ".venv" ]]; then
  echo "[deploy] creating virtualenv"
  "${PYTHON_BIN}" -m venv .venv
fi

source .venv/bin/activate

echo "[deploy] installing dependencies"
pip install --upgrade pip
pip install -r requirements.txt

echo "[deploy] running baseline checks"
make baseline

if command -v systemctl >/dev/null 2>&1; then
  echo "[deploy] restarting ${SERVICE_NAME}"
  sudo systemctl restart "${SERVICE_NAME}"
  sudo systemctl --no-pager --full status "${SERVICE_NAME}" -n 20 || true
else
  echo "[deploy] systemctl not available; skipped restart"
fi

echo "[deploy] completed"
