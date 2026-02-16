# Menu System

This project now uses a schema-driven menu setup.
Startup-triggered actions are configured separately in `local_config/startup_actions.json`.

## Where Things Live

- Menu layout and buttons:
  - `local_config/menu.json` (local, gitignored)
  - `local_config/menu.json.example` (template)
- Action behavior mapping:
  - `action_specs` section inside `local_config/menu.json`
- Dynamic button state/labels (active/inactive/available/text updates):
  - `state_specs` section inside `local_config/menu.json`
- Action execution engine:
  - `app/controllers/action_dispatcher.py`

## Add A New Button

1. Add button in `menu_schema` in `local_config/menu.json`.

```python
{"id": "my_feature", "text": "Mijn feature", "image": "tools.png", "action": "my_feature"}
```

2. Add action spec in `action_specs` in `local_config/menu.json`.

```python
"my_feature": {"kind": "mqtt_action", "action": "my_feature_toggle"},
```

3. Optional: add dynamic state/label in `state_specs` in `local_config/menu.json`.

```python
{
  "button_id": "my_feature",
  "type": "setting_bool",
  "source": "my_feature_enabled",
  "action_text": "[my_feature_action]",
  "on_text": "uit",
  "off_text": "aan"
}
```

## Step-By-Step Helper (Make)

Use the new scaffolder:

```bash
make menu-item-scaffold
```

Wizard modes:
- `create`: creates a menu item and updates required files automatically.
- `edit`: edits an existing item (label/icon/action) and can scaffold missing action specs.
- `remove`: removes an existing item and optionally removes unreferenced action/settings keys.
- `verify`: checks one item wiring.

Supported item types in `create`:
- `setting_toggle`
- `mqtt_action`
- `mqtt_message`
- `mqtt_publish`
- `show_image`
- `show_qr` (reads payload from `local_config/qr_items.json`)
- `show_camera` (reads payload from `local_config/cameras.json`)
- `custom` (includes action-dispatcher stub method)
- `submenu` (includes placeholder child action + custom stub)

Files updated automatically (as needed):
- `local_config/menu.json`
- `app/controllers/action_dispatcher.py` (for `custom` stubs)
- `settings.json.example` and `local_config/settings.json` (for new setting keys)

Validation:

```bash
make menu-item-verify-toggle ITEM_ID=my_item
make menu-contract-check
make menu-migrate-actions
make settings-check
```

Notes:
- Selection is done via numbered options in the terminal (not arrow-key navigation).
- You can add items to top-level or any existing submenu container listed by the wizard.
- Icon guidelines live in `images/buttons/README.md`.

## Supported Action Kinds

Defined in `action_specs` in `local_config/menu.json`.

- `menu_nav`
  - Example:
  - `{"kind": "menu_nav", "command": "back"}`
- `mqtt_action`
  - Example:
  - `{"kind": "mqtt_action", "action": "scene_movie"}`
  - Optional:
  - `topic_key` (e.g. `"actions_outgoing"`, default for `mqtt_action`)
  - `topic` (explicit topic string, overrides `topic_key`)
  - `value` (included as `{"value": ...}`)
  - `extra` (object merged into outgoing payload)
- `mqtt_message`
  - Example:
  - `{"kind": "mqtt_message", "topic": "screen_commands/doorbell", "payload": {"active": true}}`
  - Optional:
  - `topic_key` (resolve via `mqtt_topics.json`)
- `mqtt_publish`
  - Alias of `mqtt_message` (same behavior) for clearer naming in new configs.
  - Example:
  - `{"kind": "mqtt_publish", "topic_key": "actions_outgoing", "payload": {"action": "scene_movie"}}`
- `show_image`
  - Example:
  - `{"kind": "show_image", "image": "qr-wifi.png"}`
- `show_qr`
  - Example:
  - `{"kind": "show_qr", "item_id": "wifi_home"}`
- `show_camera`
  - Example:
  - `{"kind": "show_camera", "camera_id": "doorbell"}`
  - Optional override fields:
  - `command_topic`, `command_payload`
- `setting_toggle`
  - Example:
  - `{"kind": "setting_toggle", "attr": "media_show_titles"}`
- `media`
  - Examples:
  - `{"kind": "media", "op": "play_pause"}`
  - `{"kind": "media", "op": "volume", "arg": "up"}`
  - `{"kind": "media", "op": "skip", "arg": "next"}`
- `overlay`
  - Example:
  - `{"kind": "overlay", "command": OverlayCommand.SHOW_CAM}`
- `shell`
  - Example:
  - `{"kind": "shell", "op": "reboot"}`
- `app_exit`
  - Example:
  - `{"kind": "app_exit"}`
- `custom`
  - Example:
  - `{"kind": "custom", "name": "doorbell"}`
  - Implemented in `app/controllers/action_dispatcher.py` (`_custom_handlers` + method).

## Add A Submenu

Add a `screen` list to a menu entry in `local_config/menu.json`:

```python
{
    "id": "my_menu",
    "text": "Mijn submenu",
    "image": "tools.png",
    "action": "open_page",
    "screen": [
        {"id": "my_menu_back", "text": "Terug", "image": "back.png", "action": "back"},
        {"id": "my_menu_action", "text": "Doe iets", "image": "run.png", "action": "my_feature"},
    ],
}
```

## Common Issues

- Button shows but does nothing:
  - Check `action` exists in `action_specs` in `local_config/menu.json`.
- Label does not change (e.g., `[music_action]` still visible):
  - Add/update entry in `state_specs` in `local_config/menu.json`.
- Wrong light percentage or unavailable state:
  - Check incoming device payload parsing in `app/models/device_states.py`.
- Icon missing:
  - Ensure image exists in `images/buttons/`.

## Quick Validation

Run:

```bash
python3 -m py_compile \
  app/ui/menu_registry.py \
  app/ui/menu_state_resolver.py \
  app/controllers/action_registry.py \
  app/controllers/action_dispatcher.py

python3 tools/smoke.py --compile-only
python3 tools/menu_contract_check.py
```
