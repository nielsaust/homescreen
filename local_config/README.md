# Local Config

This directory contains machine-local config that should not be committed.

Primary files:
- `settings.json`: app runtime settings
- `mqtt_topics.json`: MQTT topic mapping
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

## Cameras

1. Copy `cameras.json.example` to `cameras.json`.
2. Fill in your local values.
3. Reference camera ids from menu actions using action kind `show_camera`.

Optional fields per camera:
- `command_topic`: publish topic when opening the camera.
- `command_payload`: payload to publish to `command_topic`.
- `overlay_data`: payload passed to camera overlay (defaults to `{"active": true}`).
