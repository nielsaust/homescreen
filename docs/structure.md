# Project Structure

## Top-level

- `main.py`
  - app entrypoint + high-level orchestration.
- `app/`
  - application code by domain (controllers/services/ui/etc).
- `core/`
  - event/store/reducer primitives.
- `tools/`
  - bootstrap/doctor/smoke/perf/settings/network simulation scripts.
- `docs/`
  - architecture, deploy, testing, observability, settings, menu docs.
- `deploy/`
  - `systemd` unit templates for Pi.

## App Package

- `app/config/`
  - settings loading and defaults.
- `app/controllers/`
  - orchestration/control logic (`display_controller`, `mqtt_controller`, `action_dispatcher`, etc).
- `app/services/`
  - business/runtime services (network bootstrap, queues, lifecycle, observability, music pipeline, power policy).
- `app/models/`
  - runtime objects/data shape helpers (`device_states`, `music_object`).
- `app/ui/screens/`
  - all screen modules (weather, music, menu, off, overlays).
- `app/ui/widgets/`
  - reusable widgets (network status banner).
- `app/viewmodels/`
  - text/state formatting logic for UI screens.
- `app/observability/`
  - logging setup/domain logger/sentry setup.
- `app/hardware/`
  - HyperPixel/RPi-specific hardware adapters.

## Naming and Boundaries

- Controllers coordinate inputs/actions/transitions.
- Services own policy/state transforms/background loops.
- Screens render UI and delegate behavior.
- Main app should avoid domain logic and mostly wire components.
