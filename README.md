# homescreen

Tkinter homescreen app for Raspberry Pi (HyperPixel) with MQTT-driven automation, menu control, music/weather screens, and overlay windows (camera/calendar/alerts/print status).

## Quick Start (Local)

```bash
make install
make configuration
make test-local
make run
```

## Quick Start (Pi)

```bash
mkdir -p logs
make install
sudo systemctl restart homescreen.service
```

Full deploy/systemd setup: `docs/deploy.md`

## What This App Does

- Startup in idle screen (`weather` or `off` based on settings)
- React to MQTT topics (music + optional integrations like doorbell/calendar/printer)
- Provide menu-based control (schema-driven buttons/actions/states)
- Handle network outages with degraded mode + reconnect behavior
- Keep Tk updates on the UI thread via queue/intents
- MQTT is optional (`enable_mqtt=false` by default for clean installs)
- Music and Weather are optional (`enable_music=false`, `enable_weather=false` by default)

## Documentation Map

- Architecture and runtime flow: `docs/architecture.md`
- Folder structure and boundaries: `docs/structure.md`
- Interactive setup/configuration: `docs/configuration.md`
- Testing and simulation commands: `docs/testing.md`
- Deploy to Raspberry Pi: `docs/deploy.md`
- Logging and Sentry: `docs/observability.md`
- Settings sync workflow: `docs/settings.md`
- Menu schema/actions/state system: `docs/menu-system.md`
- Music integration payload contract: `docs/music-integration.md`
- Security and history rewrite workflow: `docs/security.md`

## Daily Commands

- Install/update env: `make install`
- Configure integrations: `make configuration`
- Configure MQTT topics: `make mqtt-topics`
- Local checks: `make test-local`
- Run app: `make run`
- Pi checks: `make test-device`
- Simulate outage locally: `make net-down`, `make net-status`, `make net-up`
- Menu item scaffolder (interactive): `make menu-item-scaffold`
- Menu wiring check (interactive picker): `make menu-item-verify-toggle`
- Menu contract check: `make menu-contract-check`
- Install pre-commit hook: `make precommit-install`
- Run local secret scans: `make precommit-run`, `make security-scan`
