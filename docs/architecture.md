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

## Network visualization split (Phase 5.1)

- Offline icon rendering moved to app-level `network_status_widget.py`.
- Weather screen no longer owns the network indicator widget.
- Network status polling and visualization are now controlled in `MainApp`.

## Offline weather cache + deferred MQTT (Phase 5.2)

- Weather payload is cached to `.cache/weather_last.json`.
- On offline boot/outage, weather screen renders last known data from cache.
- MQTT initialization is deferred until network is available.
- Before MQTT init, a no-op controller prevents crashes on user actions.

## Weather split (Phase 5.4)

- `weather_screen.py` now focuses on Tk rendering/timers.
- Weather IO/cache/retry logic moved to `app/services/weather_service.py`.
- Display text mapping moved to `app/viewmodels/weather_view_model.py`.

## Music event coalescing (Phase 5.5)

- Incoming music MQTT payloads are now debounced and coalesced (`latest wins`) before UI updates.
- Duplicate payloads can be dropped via `music_drop_duplicate_payloads`.
- Normalization/signature logic lives in `app/services/music_service.py`.

## Music priority update path (Phase 5.7)

- Transport updates (`state`) can bypass debounce (`music_apply_transport_immediately`).
- Metadata/art updates remain debounced/coalesced.
- This keeps play/pause/track state responsive while reducing event-burst churn.

## Music stale-art guard + counters (Phase 5.8)

- Album-art apply now validates track signature before rendering to avoid stale images.
- Music pipeline and artwork counters are tracked and periodically logged.

## Music split (Phase 5.9)

- `music_screen.py` now focuses on Tk render/orchestration.
- Album-art HTTP fetch logic moved to `app/services/music_art_service.py`.
- Overlay text composition/sanitization moved to `app/viewmodels/music_view_model.py`.

## State-driven render loop start (Phase 6.0)

- `MainApp` now subscribes to store updates and translates selected state changes into UI intents.
- UI intents are queued thread-safe and applied on the Tk main thread only.
- First migrated slice:
  - global network icon visibility (`network.status`)
  - weather cached-data label (`weather.updated`)
- This removes direct Tk updates from non-UI paths and is the baseline for further screen migrations.

## State-driven music render intent (Phase 6.1)

- `music.updated` now carries full metadata (state/title/artist/channel/album/art URL).
- Store tracks this metadata; `MainApp` maps it to a `music.render` UI intent.
- Music screen applies metadata updates via `apply_state_update(...)` on Tk thread.
- Music UI intent dedupe prevents redundant re-renders on unchanged payload signatures.

## State-driven music screen navigation (Phase 6.2)

- `update_music_object(...)` no longer switches screens directly.
- `music.updated` now also emits a playback UI intent (`ui.music.playback`).
- Tk-thread intent apply decides `switch_to_music()` vs `switch_to_idle()` based on music state.
- Playback-state dedupe avoids repeated screen switch calls for unchanged state.

## State-driven screen apply (Phase 6.3)

- `ui.screen.changed` is now translated to a dedicated `ui.screen.changed` UI intent.
- `switch_to_idle`, `switch_to_music`, and `switch_to_menu` publish intent-driving events only.
- Tk-thread intent apply is now the single path that calls `display_controller.show_screen(...)` / `turn_off()`.
- Screen intent dedupe keeps screen transitions stable and avoids repeated re-apply on identical state.

## State-driven menu refresh (Phase 6.4)

- Direct `update_menu_states()` calls from action/device/music flows were replaced by `menu.refresh.requested` events.
- `MainApp` maps these events to a `menu.refresh` UI intent.
- Menu button state recalculation now runs via Tk-thread intent apply, consistent with other UI updates.

## State-driven menu navigation (Phase 6.5)

- Menu navigation actions now publish `menu.navigation.requested` events (`page_prev`, `page_next`, `back`, `exit`).
- `MainApp` maps these to `menu.navigate` UI intents and applies them on Tk thread.
- Gesture and action-dispatcher paths no longer call menu navigation methods directly.

## Music pause grace window (Phase 6.6)

- `ui.music.playback` handling now treats `paused` with a grace delay before switching to idle.
- If `playing` arrives within the grace window, pending idle switch is canceled.
- Grace duration is configurable via `music_pause_grace_ms` (default `1200`).

## Screen namespace bootstrap (Phase 8.0)

- Added `app/ui/screens/` package as the target namespace for screen modules.
- `DisplayController` now imports screens from `app.ui.screens.*`.
- Current screen modules are compatibility wrappers to keep behavior stable before physically moving screen implementations out of root.

## Weather screen move (Phase 8.1)

- `weather_screen.py` implementation was moved to `app/ui/screens/weather_screen.py`.
- Root `weather_screen.py` now acts as a backward-compatible shim import.
- This keeps runtime behavior stable while reducing root-level module ownership.

## Music screen move (Phase 8.2)

- `music_screen.py` implementation was moved to `app/ui/screens/music_screen.py`.
- Root `music_screen.py` now acts as a backward-compatible shim import.

## Menu screen move (Phase 8.3)

- `menu_screen.py` implementation was moved to `app/ui/screens/menu_screen.py`.
- Root `menu_screen.py` now acts as a backward-compatible shim import.

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
