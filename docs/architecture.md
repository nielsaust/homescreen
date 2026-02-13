# Architecture (Phase 2 Skeleton)

This project now has a minimal core layer to support gradual migration to a state-driven model.

## Core components

- `core/events.py`: immutable `AppEvent`
- `core/state.py`: immutable `AppState`
- `core/reducer.py`: pure `reduce_state(state, event)` transitions
- `core/store.py`: thread-safe store around reducer
- `core/event_bus.py`: in-process pub/sub bus

## Current integration status

- Existing app behavior is unchanged.
- `MainApp` publishes passive events for:
  - app start
  - network status
  - interaction input
  - screen changes
  - MQTT messages
  - music/device state updates
- Store updates in parallel, but UI and services still run legacy flow.

## Thread safety improvement (Phase 3)

- MQTT callback thread no longer updates UI state directly.
- MQTT messages are queued in `MainApp.enqueue_mqtt_message(...)`.
- `MainApp` drains queue on Tk main thread via `root.after(...)` pump.

## Network resilience + simulation (Phase 4)

- Startup internet wait is bounded (`startup_wait_for_internet_seconds`).
- App can continue in degraded mode when internet is unavailable.
- MQTT connect/reconnect uses exponential backoff with configurable min/max intervals.
- Network outage can be simulated via `.sim/network_down.flag` (see `tools/network_sim.py`).

## Action routing split (Phase 5)

- `TouchController` now handles input/gestures only.
- Menu action -> behavior routing moved to `action_dispatcher.py`.
- This reduces UI/input coupling and prepares further service extraction.

## Local state testing without UI

Use replay tool with JSONL:

```json
{"event_type":"app.started","payload":{"system_platform":"Darwin","is_desktop":true}}
{"event_type":"interaction.received","payload":{"interaction_type":"single_click"}}
{"event_type":"ui.screen.changed","payload":{"screen":"menu","is_display_on":true}}
```

Run:

```bash
python3 tools/event_replay.py /path/to/events.jsonl
```
