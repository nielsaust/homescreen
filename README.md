# homescreen

Tkinter-based homescreen controller for Raspberry Pi/HyperPixel with MQTT-driven device control.

## Quick Start

```bash
cp settings.json.example settings.json
make install
make test-local
make run
```

## Test Commands

- Syntax baseline (no deps): `make baseline`
- Local baseline: `make test-local`
- Device baseline (Pi): `make test-device`

More detail: `docs/testing.md`

## Observability

- Local logs: enabled by default
- Optional Sentry: see `docs/observability.md`

## Architecture

- Core event/state skeleton: `docs/architecture.md`
