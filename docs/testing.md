# Testing

## Standard Local Loop

```bash
make install
make test-local
make run
```

`make test-local` runs:
- `doctor` environment checks
- `smoke` import/compile checks
- unit tests in `tests/unit`

## Targeted Commands

- Syntax-only quick check: `make baseline`
- Unit tests only: `make test-unit`
- Perf guards: `make perf-check`
- Smoke only: `make smoke`

## Device (Pi) Checks

```bash
make test-device
```

Includes:
- smoke checks
- unit tests
- optional `systemd` status checks
- MQTT reachability check

## Network Outage Simulation (Local/Pi)

```bash
make net-down
make net-status
make net-up
```

Behavior:
- App enters degraded mode while simulated offline.
- MQTT init/reconnect is deferred until network is available.
- Weather falls back to cached payload when available.
- Global network banner updates independent of weather screen ownership.

## Music Diagnostics

Enable in `settings.json`:

```json
{
  "music_debug_logging": true
}
```

This enables detailed music pipeline debug logs and periodic observability-only counters:
- `received`
- `coalesced`
- `dropped`
- `applied`
- `art_requests`
- `art_success`
- `art_stale_dropped`
- `art_placeholder`
- `art_errors`

## Settings Hygiene During Testing

- `settings.json` is local-only and gitignored.
- Keep `settings.json.example` aligned:
  - `make settings-check`
  - `make settings-update-example`
  - `make settings-update-local`
