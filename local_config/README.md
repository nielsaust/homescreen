# Local Config

This directory contains machine-local config that should not be committed.

Primary files:
- `settings.json`: app runtime settings
- `mqtt_topics.json`: MQTT topic mapping
- `mqtt_routes.json`: topic -> behavior routing
- `startup_actions.json`: startup-triggered actions (e.g., MQTT refresh calls)
- `device_state_mapping.json`: mapping for incoming device-state payload fields
- `cameras.json`: camera URLs/credentials
- `menu.json`: personal menu schema/actions/state
- `qr_items.json`: personal QR payloads

## Menu config

1. Copy `menu.json.example` to `menu.json`.
2. Keep personal button layout/actions in `menu.json` (gitignored).
3. Use `make menu-item-scaffold` to create/edit/remove items; it writes to `menu.json`.

## QR items

1. Copy `qr_items.json.example` to `qr_items.json`.
2. Fill in your local values.
3. Reference item ids from menu actions using action kind `show_qr`.

Supported types:
- `url`: fields `url`
- `wifi`: fields `ssid`, `password`, optional `auth` (`WPA`, `WEP`, `nopass`), optional `hidden` (`true`/`false`)

## MQTT topics

1. Copy `mqtt_topics.json.example` to `mqtt_topics.json`.
2. Set only the topics you use.
3. Use `make mqtt-topics` for interactive overview/edit.

## MQTT routes

1. Copy `mqtt_routes.json.example` to `mqtt_routes.json`.
2. Define how incoming topics map to app behavior.
3. Keep `topic_key` values aligned with keys in `mqtt_topics.json`.

Route fields:
- `topic_key`: key from `mqtt_topics.json`.
- `phase`: `essential` or `nonessential` (startup defer applies to nonessential).
- `action`: behavior to run. Supported:
  - `music_update`
  - `device_states_update`
  - `printer_progress_update`
  - `overlay_command`
- `overlay_command` (for `action=overlay_command`):
  - `show_cam` (requires `camera_id`)
  - `show_calendar`
  - `show_alert`
  - `show_print_status` (optional `reset: true/false`)
  - `print_screen_attention`
  - `close_print_screen`
  - `cancel_attention`

## Startup actions

1. Copy `startup_actions.json.example` to `startup_actions.json`.
2. Define actions that should run after app startup.

Action fields:
- `id`: unique action id for logging.
- `kind`: action type currently supporting `mqtt_publish` and `mqtt_action`.
- `topic_key` or `topic`: publish destination.
- `payload`/`action`/`value`/`extra`: action payload fields depending on kind.
- `delay_ms`: optional startup delay.
- `require_mqtt`: wait for MQTT controller readiness before execution.
- `enabled`: quick on/off toggle.

## Cameras

1. Copy `cameras.json.example` to `cameras.json`.
2. Fill in your local values.
3. Reference camera ids from menu actions using action kind `show_camera`.

Optional fields per camera:
- `command_topic`: publish topic when opening the camera.
- `command_payload`: payload to publish to `command_topic`.
- `overlay_data`: payload passed to camera overlay (defaults to `{"active": true}`).

## Device state mapping

1. Copy `device_state_mapping.json.example` to `device_state_mapping.json`.
2. Configure how incoming device-state payload fields are mapped/coerced into `DeviceStates`.

Field spec:
- `source`: key in incoming payload.
- `type`: one of `string`, `float`, `on_off_bool`, `light`, `availability`.
- `default`: optional fallback.
- `track_original`: optional (useful for edge-trigger behavior like `in_bed`).
