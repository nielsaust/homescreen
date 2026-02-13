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
