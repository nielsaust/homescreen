# Architecture

## Runtime Model

The app is now service-oriented with a single Tk UI thread as rendering authority.

High-level flow:

1. `MainApp` bootstraps settings/logging/Sentry.
2. Composition wires event pipeline + runtime components.
3. Network bootstrap decides online/degraded startup.
4. Queue pumps process MQTT/UI intents on the Tk thread.
5. Controllers/services publish events and request UI changes via intents.

## Core Layers

- `core/`
  - `event_bus.py`: in-process pub/sub.
  - `events.py`: `AppEvent`.
  - `state.py`: `AppState`.
  - `reducer.py` + `store.py`: state updates.
- `app/services/`
  - domain and lifecycle services.
- `app/controllers/`
  - UI/MQTT orchestration and routing.
- `app/ui/`
  - screens/widgets and render utilities.

## Main App Responsibilities (Current)

`main.py` is now mostly orchestration:

- settings/load policy
- startup wiring/composition
- thin wrappers used as app API by controllers/services

Most logic moved into services/controllers.

## Key Services

- `app_composition_service.py`
  - wires event bus/store + runtime components.
- `app_lifecycle_service.py`
  - starts touch bindings, queue pumps, network polling, initial screen.
- `app_runtime_config_service.py`
  - normalizes runtime settings flags/intervals.
- `event_dispatch_service.py`
  - centralized `publish_event`.
- `queue_pump_service.py`
  - UI intent pump + MQTT queue pump.
- `network_bootstrap_service.py`
  - startup connectivity, degraded mode, periodic network checks, deferred MQTT init.
- `mqtt_lifecycle_service.py`
  - MQTT controller init/start/stop.
- `music_update_service.py`
  - coalescing/debounce/transport-priority for music payloads.
- `music_state_service.py`
  - updates `music_object` + emits `music.updated`.
- `music_playback_policy_service.py`
  - pause grace timer / idle fallback.
- `music_metrics_service.py`
  - observability-only music counters/logging.
- `system_info_service.py`
  - platform detection + memory usage logging.
- `app_observability_service.py`
  - UI trace logs, music debug logs, global exception hook.
- `power_policy_service.py`
  - in-bed + idle power/screen policy.
- `startup_sync_service.py`
  - startup MQTT sync queue for required topics.
- `ui_intent_mapper_service.py`
  - store event -> UI intent mapping.
- `device_state_mapping.py` + `DeviceStates`
  - declarative device-state mapping loaded from `local_config/device_state_mapping.json`
  - dynamic field coercion based on mapping `fields` specs.

## UI Thread Safety Strategy

- MQTT callbacks never update Tk directly.
- MQTT payloads are queued.
- UI changes are applied via UI intents on Tk thread.
- This avoids cross-thread Tk updates and race-prone screen mutation.

## Screen/Overlay Model

- Base screens: `off`, `weather`, `music`, `menu`.
- Overlays/windows managed via `OverlayManager` + `DisplayController`.
- Menu actions are schema-driven (`menu_registry`, `action_registry`, `menu_state_resolver`).

## Network Resilience

- Degraded startup allowed (configurable).
- Deferred MQTT init when offline at boot.
- Polling reconnect behavior when network returns.
- Local simulation via `.sim/network_down.flag` and `make net-down/net-up`.

## Observability Model

- Structured domain logs (`[app]`, `[mqtt]`, `[ui]`, `[music]`, `[network]`, etc).
- Per-domain log level overrides via settings.
- Optional Sentry integration (safe fallback when unavailable).
