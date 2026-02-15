# Menu System

This project now uses a schema-driven menu setup.

## Where Things Live

- Menu layout and buttons:
  - `/Users/niels/Documents/Workspace/Personal/homescreen/app/ui/menu_registry.py`
- Action behavior mapping:
  - `/Users/niels/Documents/Workspace/Personal/homescreen/app/controllers/action_registry.py`
- Dynamic button state/labels (active/inactive/available/text updates):
  - `/Users/niels/Documents/Workspace/Personal/homescreen/app/ui/menu_state_resolver.py`
- Action execution engine:
  - `/Users/niels/Documents/Workspace/Personal/homescreen/app/controllers/action_dispatcher.py`

## Add A New Button

1. Add button in `MENU_SCHEMA` in `/Users/niels/Documents/Workspace/Personal/homescreen/app/ui/menu_registry.py`.

```python
{"id": "my_feature", "text": "Mijn feature", "image": "tools.png", "action": "my_feature"}
```

2. Add action spec in `/Users/niels/Documents/Workspace/Personal/homescreen/app/controllers/action_registry.py`.

```python
"my_feature": {"kind": "mqtt_action", "action": "my_feature_toggle"},
```

3. Optional: add dynamic state/label in `/Users/niels/Documents/Workspace/Personal/homescreen/app/ui/menu_state_resolver.py`.

```python
self._spec(
    "my_feature",
    active_flag,
    action_text="[my_feature_action]",
    on_text="uit",
    off_text="aan",
)
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
- `show_image`
- `custom` (includes action-dispatcher stub method)
- `submenu` (includes placeholder child action + custom stub)

Files updated automatically (as needed):
- `app/ui/menu_registry.py`
- `app/controllers/action_registry.py`
- `app/ui/menu_state_resolver.py` (for `setting_toggle`)
- `app/controllers/action_dispatcher.py` (for `custom` stubs)
- `settings.json.example` and `settings.json` (for new setting keys)

Validation:

```bash
make menu-item-verify-toggle ITEM_ID=my_item
make menu-contract-check
make settings-check
```

Notes:
- Selection is done via numbered options in the terminal (not arrow-key navigation).
- You can add items to top-level or any existing submenu container listed by the wizard.
- Icon guidelines live in `images/buttons/README.md`.

## Supported Action Kinds

Defined in `/Users/niels/Documents/Workspace/Personal/homescreen/app/controllers/action_registry.py`.

- `menu_nav`
  - Example:
  - `{"kind": "menu_nav", "command": "back"}`
- `mqtt_action`
  - Example:
  - `{"kind": "mqtt_action", "action": "scene_movie"}`
- `mqtt_message`
  - Example:
  - `{"kind": "mqtt_message", "topic": "screen_commands/doorbell"}`
- `show_image`
  - Example:
  - `{"kind": "show_image", "image": "qr-wifi.png"}`
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
  - Implemented in `/Users/niels/Documents/Workspace/Personal/homescreen/app/controllers/action_dispatcher.py` (`_custom_handlers` + method).

## Add A Submenu

Add a `screen` list to a menu entry in `/Users/niels/Documents/Workspace/Personal/homescreen/app/ui/menu_registry.py`:

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
  - Check `action` exists in `/Users/niels/Documents/Workspace/Personal/homescreen/app/controllers/action_registry.py`.
- Label does not change (e.g., `[music_action]` still visible):
  - Add/update resolver rule in `/Users/niels/Documents/Workspace/Personal/homescreen/app/ui/menu_state_resolver.py`.
- Wrong light percentage or unavailable state:
  - Check incoming device payload parsing in `/Users/niels/Documents/Workspace/Personal/homescreen/app/models/device_states.py`.
- Icon missing:
  - Ensure image exists in `/Users/niels/Documents/Workspace/Personal/homescreen/images/buttons/`.

## Quick Validation

Run:

```bash
python3 -m py_compile \
  app/ui/menu_registry.py \
  app/ui/menu_state_resolver.py \
  app/controllers/action_registry.py \
  app/controllers/action_dispatcher.py

python3 tools/smoke.py --compile-only
```
