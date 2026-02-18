#!/usr/bin/env bash
set -euo pipefail

IFACE="${1:-wlan0}"
PING_HOST="${PING_HOST:-8.8.8.8}"
RETRIES="${RETRIES:-6}"
DELAY_SECONDS="${DELAY_SECONDS:-2}"

log() {
  printf '[net-recover] %s\n' "$*"
}

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

ping_ok() {
  ping -c 1 -W 2 "${PING_HOST}" >/dev/null 2>&1
}

if ping_ok; then
  log "network already online (host=${PING_HOST})"
  exit 0
fi

log "starting recovery iface=${IFACE} host=${PING_HOST}"

if have_cmd ip; then
  log "ip link down ${IFACE}"
  sudo ip link set "${IFACE}" down || true
  sleep 1
  log "ip link up ${IFACE}"
  sudo ip link set "${IFACE}" up || true
fi

if have_cmd dhcpcd; then
  log "renew dhcp via dhcpcd on ${IFACE}"
  sudo dhcpcd -k "${IFACE}" || true
  sleep 1
  sudo dhcpcd "${IFACE}" || true
else
  log "dhcpcd not found, restarting dhcpcd service"
  sudo systemctl restart dhcpcd || true
fi

if systemctl list-unit-files "wpa_supplicant@${IFACE}.service" >/dev/null 2>&1; then
  log "restart wpa_supplicant@${IFACE}"
  sudo systemctl restart "wpa_supplicant@${IFACE}" || true
fi

if have_cmd resolvectl; then
  log "flush DNS cache"
  sudo resolvectl flush-caches || true
fi

for attempt in $(seq 1 "${RETRIES}"); do
  if ping_ok; then
    log "recovery success on attempt ${attempt}"
    exit 0
  fi
  log "attempt ${attempt}/${RETRIES} failed; retry in ${DELAY_SECONDS}s"
  sleep "${DELAY_SECONDS}"
done

log "recovery failed after ${RETRIES} attempts"
exit 1
