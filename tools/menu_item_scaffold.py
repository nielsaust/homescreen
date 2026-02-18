#!/usr/bin/env python3
"""Interactive menu item wizard with create/edit/remove/verify flows."""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ui.menu_config_loader import load_menu_config, save_local_menu_config

ACTION_DISPATCHER = ROOT / "app" / "controllers" / "action_dispatcher.py"
SETTINGS_EXAMPLE = ROOT / "settings.json.example"
SETTINGS_LOCAL = ROOT / "local_config" / "settings.json"
BUTTON_IMAGES_DIR = ROOT / "images" / "buttons"
QR_ITEMS_PATH = ROOT / "local_config" / "qr_items.json"
CAMERAS_PATH = ROOT / "local_config" / "cameras.json"
MQTT_TOPICS_LOCAL = ROOT / "local_config" / "mqtt_topics.json"
MQTT_TOPICS_EXAMPLE = ROOT / "local_config" / "mqtt_topics.json.example"
MQTT_ROUTES_LOCAL = ROOT / "local_config" / "mqtt_routes.json"


class UserCanceled(Exception):
    """Raised when user aborts interactive input."""


def _prompt(text: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        value = input(f"{text}{suffix}: ").strip()
    except (KeyboardInterrupt, EOFError) as exc:
        raise UserCanceled from exc
    return value if value else default


def _prompt_required(text: str, default: str = "") -> str:
    while True:
        value = _prompt(text, default)
        if value:
            return value
        print("Value is required.")


def _prompt_choice(text: str, options: list[str], default: str) -> str:
    allowed = "/".join(options)
    while True:
        value = _prompt(f"{text} ({allowed})", default).lower()
        if value in options:
            return value
        print(f"Invalid choice '{value}'. Allowed: {allowed}")


def _prompt_optional(text: str, default: str = "") -> str:
    return _prompt(text, default).strip()


def _select_from_list(title: str, rows: list[dict[str, Any]], allow_cancel: bool = True) -> dict[str, Any] | None:
    if not rows:
        return None
    print(f"\n{title}")
    for idx, row in enumerate(rows, start=1):
        print(f"{idx:2d}) {row['label']}")
    if allow_cancel:
        print(" 0) Back")
    while True:
        raw = _prompt("Choose number")
        if not raw and allow_cancel:
            return None
        if raw.isdigit():
            num = int(raw)
            if allow_cancel and num == 0:
                return None
            if 1 <= num <= len(rows):
                return rows[num - 1]
        print("Invalid selection.")


def _icon_choices() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if BUTTON_IMAGES_DIR.exists():
        for path in sorted(BUTTON_IMAGES_DIR.glob("*.png")):
            rows.append({"label": path.name, "value": path.name})
    return rows


def _choose_icon(default: str = "tools.png") -> str:
    while True:
        print("\nIcon selection")
        print("1) choose from available icon files")
        print("2) type filename manually")
        mode = _prompt_choice("Choose icon input mode", ["1", "2"], "1")
        if mode == "1":
            rows = _icon_choices()
            if not rows:
                print("[menu-item] no .png files found in images/buttons; switching to manual mode.")
                continue
            filter_text = _prompt("Filter icons by text (leave empty for all)", "")
            if filter_text:
                needle = filter_text.lower()
                rows = [row for row in rows if needle in str(row["label"]).lower()]
                if not rows:
                    print(f"[menu-item] no icons match filter '{filter_text}'.")
                    continue
            selected = _select_from_list("Available icons (images/buttons)", rows)
            if selected is None:
                print("[menu-item] icon selection canceled; returning to mode choice.")
                continue
            return str(selected["value"])

        filename = _prompt_required("Icon filename", default)
        if not (BUTTON_IMAGES_DIR / filename).exists():
            print(f"[menu-item] warning: images/buttons/{filename} does not exist.")
            if _prompt_choice("Use this filename anyway?", ["y", "n"], "n") != "y":
                continue
        return filename


def _load_menu_config_data() -> dict[str, Any]:
    return copy.deepcopy(load_menu_config())


def _load_menu_schema(config: dict[str, Any]) -> list[dict[str, Any]]:
    return copy.deepcopy(config.get("menu_schema", []))


def _load_legacy_action_specs(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return copy.deepcopy(config.get("action_specs", {}))


def _save_menu_config_data(config: dict[str, Any], schema: list[dict[str, Any]], action_specs: dict[str, dict[str, Any]]) -> None:
    config["menu_schema"] = schema
    inline_specs = _collect_inline_action_specs(schema)
    compact_legacy = {
        key: value for key, value in action_specs.items() if key not in inline_specs
    }
    # Keep legacy top-level store only for actions that are not yet migrated inline.
    config["action_specs"] = compact_legacy
    save_local_menu_config(config)


def _iter_entries(schema: list[dict[str, Any]]):
    for entry in schema:
        if not isinstance(entry, dict):
            continue
        yield entry
        children = entry.get("screen")
        if isinstance(children, list):
            yield from _iter_entries(children)


def _collect_inline_action_specs(schema: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for entry in _iter_entries(schema):
        action_id = str(entry.get("action", "")).strip()
        if not action_id or action_id in ("back", "open_page"):
            continue
        spec = entry.get("action_spec")
        if isinstance(spec, dict) and spec:
            out[action_id] = copy.deepcopy(spec)
    return out


def _all_action_specs(schema: list[dict[str, Any]], action_specs: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    merged = copy.deepcopy(action_specs)
    merged.update(_collect_inline_action_specs(schema))
    return merged


def _entry_action_spec(entry: dict[str, Any], action_specs: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    inline = entry.get("action_spec")
    if isinstance(inline, dict):
        return inline
    action_id = str(entry.get("action", "")).strip()
    if action_id and action_id in action_specs:
        return action_specs[action_id]
    return None


def _get_container(schema: list[dict[str, Any]], container_path: list[int]) -> list[dict[str, Any]]:
    container = schema
    for idx in container_path:
        container = container[idx].setdefault("screen", [])
    return container


def _get_entry(schema: list[dict[str, Any]], entry_path: list[int]) -> dict[str, Any]:
    if not entry_path:
        raise ValueError("entry_path cannot be empty")
    container = _get_container(schema, entry_path[:-1])
    return container[entry_path[-1]]


def _collect_entries(schema: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def walk(entries: list[dict[str, Any]], path: list[int], prefix: str) -> None:
        for idx, entry in enumerate(entries):
            p = path + [idx]
            label = f"{prefix}/{entry.get('id')} ({entry.get('text')})"
            rows.append({"path": p, "label": label, "entry": entry})
            children = entry.get("screen") or []
            if children:
                walk(children, p, label)

    walk(schema, [], "root")
    return rows


def _collect_containers(schema: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [{"path": [], "label": "root (top level MENU_SCHEMA)"}]
    for row in _collect_entries(schema):
        entry = row["entry"]
        if "screen" in entry and isinstance(entry["screen"], list):
            rows.append(
                {
                    "path": row["path"],
                    "label": f"{row['label']} -> screen[]",
                }
            )
    return rows


def _collect_entries_in_container(schema: list[dict[str, Any]], container_path: list[int]) -> list[dict[str, Any]]:
    container = _get_container(schema, container_path)
    rows: list[dict[str, Any]] = []
    for idx, entry in enumerate(container):
        entry_path = container_path + [idx]
        rows.append(
            {
                "path": entry_path,
                "label": f"{entry.get('id')} ({entry.get('text')})",
                "entry": entry,
            }
        )
    return rows


def _select_container_then_entry(schema: list[dict[str, Any]], action_label: str) -> dict[str, Any] | None:
    while True:
        container = _select_from_list(f"Select container for {action_label}", _collect_containers(schema))
        if container is None:
            return None
        rows = _collect_entries_in_container(schema, container["path"])
        if not rows:
            print("[menu-item] selected container has no items. Choose another container.")
            continue
        row = _select_from_list(f"Select item to {action_label} in {container['label']}", rows)
        if row is None:
            # Back from item list -> go back to container selection.
            continue
        return row


def _sanitize_identifier(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_]", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "custom_action"


def _add_custom_handler_stub(name: str) -> None:
    method_name = f"_{_sanitize_identifier(name)}"
    text = ACTION_DISPATCHER.read_text(encoding="utf-8")
    if f"def {method_name}(self)" in text:
        return
    map_marker = '            "music_show_title": self._music_show_title,'
    if map_marker in text and f'"{name}": self.{method_name},' not in text:
        text = text.replace(map_marker, f'{map_marker}\n            "{name}": self.{method_name},')
    stub = (
        f"\n    def {method_name}(self) -> None:\n"
        f'        logger.info("Custom action stub triggered: {name}")\n'
    )
    text = text.rstrip() + stub + "\n"
    ACTION_DISPATCHER.write_text(text, encoding="utf-8")


def _set_setting_defaults(key: str, value: Any) -> None:
    for path in (SETTINGS_EXAMPLE, SETTINGS_LOCAL):
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        if key not in data:
            data[key] = value
            path.write_text(json.dumps(data, indent=4) + "\n", encoding="utf-8")


def _remove_setting_key(key: str) -> None:
    for path in (SETTINGS_EXAMPLE, SETTINGS_LOCAL):
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        if key in data:
            del data[key]
            path.write_text(json.dumps(data, indent=4) + "\n", encoding="utf-8")


def _load_json_object(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _save_json_object(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _load_cameras() -> dict[str, Any]:
    payload = _load_json_object(CAMERAS_PATH) or {}
    cameras = payload.get("cameras")
    if isinstance(cameras, dict):
        return cameras
    return {}


def _save_cameras(cameras: dict[str, Any]) -> None:
    _save_json_object(CAMERAS_PATH, {"cameras": cameras})


def _collect_referenced_values(
    schema: list[dict[str, Any]],
    action_specs: dict[str, dict[str, Any]],
    kind: str,
    field: str,
) -> set[str]:
    out: set[str] = set()
    for spec in _all_action_specs(schema, action_specs).values():
        if spec.get("kind") != kind:
            continue
        value = str(spec.get(field, "")).strip()
        if value:
            out.add(value)
    return out


def _topic_key_is_used_in_routes(topic_key: str) -> bool:
    routes = _load_json_object(MQTT_ROUTES_LOCAL)
    if not routes:
        return False
    entries = routes.get("routes")
    if not isinstance(entries, list):
        return False
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("topic_key", "")).strip() == topic_key:
            return True
    return False


def _cleanup_unreferenced_action_spec(
    action_id: str,
    schema: list[dict[str, Any]],
    action_specs: dict[str, dict[str, Any]],
) -> None:
    all_specs = _all_action_specs(schema, action_specs)
    spec = all_specs.get(action_id)
    if not spec:
        return

    if _prompt_choice(f"Action '{action_id}' is now unreferenced. Remove action spec?", ["y", "n"], "y") != "y":
        return

    if action_id in action_specs:
        spec = action_specs.pop(action_id)
    kind = str(spec.get("kind", "")).strip()

    if kind == "setting_toggle":
        setting_key = str(spec.get("attr", "")).strip()
        if setting_key and _prompt_choice(
            f"Remove setting key '{setting_key}' from settings files?",
            ["y", "n"],
            "n",
        ) == "y":
            _remove_setting_key(setting_key)
        return

    if kind == "show_qr":
        item_id = str(spec.get("item_id", "")).strip()
        if not item_id:
            return
        qr_items = _load_json_object(QR_ITEMS_PATH)
        if not qr_items or item_id not in qr_items:
            return
        still_used = item_id in _collect_referenced_values(schema, action_specs, "show_qr", "item_id")
        if still_used:
            return
        if _prompt_choice(
            f"QR item '{item_id}' exists in local_config/qr_items.json but is no longer referenced. Remove it?",
            ["y", "n"],
            "n",
        ) == "y":
            del qr_items[item_id]
            _save_json_object(QR_ITEMS_PATH, qr_items)
        return

    if kind == "show_camera":
        camera_id = str(spec.get("camera_id", "")).strip()
        if not camera_id:
            return
        cameras = _load_cameras()
        if not cameras or camera_id not in cameras:
            return
        still_used = camera_id in _collect_referenced_values(schema, action_specs, "show_camera", "camera_id")
        if still_used:
            return
        if _prompt_choice(
            f"Camera '{camera_id}' exists in local_config/cameras.json but is no longer referenced. Remove it?",
            ["y", "n"],
            "n",
        ) == "y":
            del cameras[camera_id]
            _save_cameras(cameras)
        return

    if kind in ("mqtt_action", "mqtt_publish", "mqtt_message"):
        topic_key = str(spec.get("topic_key", "")).strip()
        if not topic_key:
            return
        topics = _load_json_object(MQTT_TOPICS_LOCAL)
        if not topics:
            return
        topics_block = topics.get("topics")
        if not isinstance(topics_block, dict) or topic_key not in topics_block:
            return
        topic_key_refs = set()
        for candidate in _all_action_specs(schema, action_specs).values():
            if not isinstance(candidate, dict):
                continue
            key = str(candidate.get("topic_key", "")).strip()
            if key:
                topic_key_refs.add(key)
        if topic_key in topic_key_refs or _topic_key_is_used_in_routes(topic_key):
            return
        if _prompt_choice(
            f"MQTT topic key '{topic_key}' in local_config/mqtt_topics.json is no longer referenced by actions/routes. Remove it?",
            ["y", "n"],
            "n",
        ) == "y":
            del topics_block[topic_key]
            _save_json_object(MQTT_TOPICS_LOCAL, topics)


def _build_submenu(action_id: str, label: str) -> list[dict[str, Any]]:
    base = _sanitize_identifier(action_id)
    return [
        {
            "id": f"{base}_back",
            "text": "Back",
            "image": "back.png",
            "action": "back",
            "action_spec": {"kind": "menu_nav", "command": "back"},
        },
        {"id": f"{base}_todo", "text": f"TODO: {label}", "image": "tools.png", "action": f"{base}_todo"},
    ]


def _ensure_action_spec(action_specs: dict[str, dict[str, Any]], action_id: str, item_type: str) -> tuple[dict[str, Any], str | None]:
    if action_id in action_specs:
        return action_specs, None

    if item_type == "setting_toggle":
        setting_key = _prompt_required("Setting key to toggle", action_id)
        default_true = _prompt_choice("Default setting true?", ["y", "n"], "n") == "y"
        action_specs[action_id] = {"kind": "setting_toggle", "attr": setting_key}
        _set_setting_defaults(setting_key, True if default_true else False)
        return action_specs, setting_key

    if item_type == "mqtt_action":
        mqtt_action = _prompt_required("MQTT action payload", action_id)
        action_specs[action_id] = {"kind": "mqtt_action", "action": mqtt_action}
        return action_specs, None

    if item_type == "mqtt_message":
        topic = _prompt_required("MQTT topic", "screen_commands/outgoing")
        action_specs[action_id] = {"kind": "mqtt_message", "topic": topic, "payload": None}
        return action_specs, None

    if item_type == "mqtt_publish":
        mode = _prompt_choice("Use topic key or explicit topic?", ["topic_key", "topic"], "topic_key")
        spec: dict[str, Any] = {"kind": "mqtt_publish", "payload": None}
        if mode == "topic_key":
            spec["topic_key"] = _prompt_required(
                "MQTT topic key (from local_config/mqtt_topics.json)",
                "actions_outgoing",
            )
        else:
            spec["topic"] = _prompt_required("MQTT topic", "screen_commands/outgoing")
        payload_raw = _prompt_optional("Payload (blank for none, JSON object/array, or plain string)", "")
        if payload_raw:
            try:
                if payload_raw.startswith("{") or payload_raw.startswith("["):
                    spec["payload"] = json.loads(payload_raw)
                else:
                    spec["payload"] = payload_raw
            except Exception:
                spec["payload"] = payload_raw
        action_specs[action_id] = spec
        return action_specs, None

    if item_type == "show_image":
        image_file = _prompt_required("Image file to show", "qr-wifi.png")
        action_specs[action_id] = {"kind": "show_image", "image": image_file}
        return action_specs, None

    if item_type == "show_qr":
        qr_item_id = _prompt_required("QR item id (from local_config/qr_items.json)", action_id)
        action_specs[action_id] = {"kind": "show_qr", "item_id": qr_item_id}
        return action_specs, None

    if item_type == "show_camera":
        camera_id = _prompt_required("Camera id (from local_config/cameras.json)", action_id)
        action_specs[action_id] = {"kind": "show_camera", "camera_id": camera_id}
        return action_specs, None

    if item_type == "custom":
        handler_name = _prompt_required("Custom handler name", action_id)
        action_specs[action_id] = {"kind": "custom", "name": handler_name}
        _add_custom_handler_stub(handler_name)
        return action_specs, None

    if item_type == "submenu":
        action_specs[action_id] = {"kind": "custom", "name": f"{_sanitize_identifier(action_id)}_todo"}
        _add_custom_handler_stub(f"{_sanitize_identifier(action_id)}_todo")
        return action_specs, None

    raise RuntimeError(f"Unsupported item type: {item_type}")


def _create_item() -> int:
    config = _load_menu_config_data()
    schema = _load_menu_schema(config)
    action_specs = _load_legacy_action_specs(config)

    container = _select_from_list("Select target container", _collect_containers(schema))
    if container is None:
        print("[menu-item] create canceled")
        return 0

    item_id = _prompt_required("Menu item id (snake_case)")
    existing_ids = {entry["entry"].get("id") for entry in _collect_entries(schema)}
    if item_id in existing_ids:
        print(f"[menu-item] id already exists: {item_id}")
        return 1

    label = _prompt_required("Menu label")
    icon = _choose_icon("tools.png")
    action_id = _prompt_required("Action id", item_id)
    item_type = _prompt_choice(
        "Item type",
        ["setting_toggle", "mqtt_action", "mqtt_message", "mqtt_publish", "show_image", "show_qr", "show_camera", "custom", "submenu"],
        "show_qr",
    )

    action_specs_all = _all_action_specs(schema, action_specs)
    if action_id not in action_specs_all:
        action_specs, _ = _ensure_action_spec(action_specs, action_id, item_type)
        action_specs_all = _all_action_specs(schema, action_specs)

    new_entry = {"id": item_id, "text": label, "image": icon, "action": action_id}
    if _prompt_choice("Mark as dev-only item?", ["y", "n"], "n") == "y":
        new_entry["dev_only"] = True
    if item_type == "submenu":
        new_entry["action"] = "open_page"
        new_entry["screen"] = _build_submenu(action_id, label)
    else:
        spec = action_specs_all.get(action_id)
        if isinstance(spec, dict):
            new_entry["action_spec"] = copy.deepcopy(spec)

    target = _get_container(schema, container["path"])
    target.append(new_entry)

    _save_menu_config_data(config, schema, action_specs)
    print(f"[menu-item] created '{item_id}' in {container['label']}")
    return 0


def _verify_item() -> int:
    config = _load_menu_config_data()
    schema = _load_menu_schema(config)
    action_specs = _load_legacy_action_specs(config)
    row = _select_container_then_entry(schema, "verify")
    if row is None:
        print("[menu-item] verify canceled")
        return 0
    entry = row["entry"]
    action_id = entry.get("action")
    spec = _entry_action_spec(entry, action_specs)
    if action_id not in ("back", "open_page") and not isinstance(spec, dict):
        print(f"[menu-item] missing action spec for '{action_id}'")
        return 1
    if isinstance(spec, dict):
        kind = str(spec.get("kind", "")).strip()
        if kind == "show_qr":
            item_id = str(spec.get("item_id", "")).strip()
            items = _load_json_object(QR_ITEMS_PATH) or {}
            if item_id and item_id not in items:
                print(f"[menu-item] warning: qr item '{item_id}' not found in local_config/qr_items.json")
        elif kind == "show_camera":
            camera_id = str(spec.get("camera_id", "")).strip()
            cameras = _load_cameras()
            if camera_id and camera_id not in cameras:
                print(f"[menu-item] warning: camera '{camera_id}' not found in local_config/cameras.json")
        elif kind == "setting_toggle":
            setting_key = str(spec.get("attr", "")).strip()
            local_settings = _load_json_object(SETTINGS_LOCAL) or {}
            example_settings = _load_json_object(SETTINGS_EXAMPLE) or {}
            if setting_key and setting_key not in local_settings and setting_key not in example_settings:
                print(f"[menu-item] warning: setting key '{setting_key}' missing in settings files")
        elif kind in ("mqtt_action", "mqtt_publish", "mqtt_message"):
            topic_key = str(spec.get("topic_key", "")).strip()
            if topic_key:
                topics = _load_json_object(MQTT_TOPICS_LOCAL) or _load_json_object(MQTT_TOPICS_EXAMPLE) or {}
                topic_block = topics.get("topics") if isinstance(topics.get("topics"), dict) else {}
                if topic_key not in topic_block:
                    print(f"[menu-item] warning: mqtt topic key '{topic_key}' missing in mqtt_topics.json")
    print(f"[menu-item] verify OK id='{entry.get('id')}' action='{action_id}'")
    return 0


def _edit_item() -> int:
    config = _load_menu_config_data()
    schema = _load_menu_schema(config)
    action_specs = _load_legacy_action_specs(config)
    row = _select_container_then_entry(schema, "edit")
    if row is None:
        print("[menu-item] edit canceled")
        return 0

    entry = _get_entry(schema, row["path"])
    old_action = entry.get("action")
    old_dev_only = bool(entry.get("dev_only", False))
    old_hidden = bool(entry.get("hidden", False))
    print("Press Enter to keep current value.")
    new_text = _prompt("Label", entry.get("text", ""))
    keep_icon = _prompt_choice("Keep current icon?", ["y", "n"], "y")
    if keep_icon == "y":
        new_image = entry.get("image", "tools.png")
    else:
        new_image = _choose_icon(entry.get("image", "tools.png"))
    new_action = _prompt("Action id", old_action)
    new_dev_only = _prompt_choice(
        "Mark as dev-only item?",
        ["y", "n"],
        "y" if old_dev_only else "n",
    ) == "y"
    new_hidden = _prompt_choice(
        "Hide this item from runtime menu?",
        ["y", "n"],
        "y" if old_hidden else "n",
    ) == "y"
    entry["text"] = new_text
    entry["image"] = new_image
    entry["action"] = new_action
    if new_dev_only:
        entry["dev_only"] = True
    else:
        entry.pop("dev_only", None)
    if new_hidden:
        entry["hidden"] = True
    else:
        entry.pop("hidden", None)

    action_specs_all = _all_action_specs(schema, action_specs)
    if new_action != old_action and new_action not in ("back", "open_page") and new_action not in action_specs_all:
        create_spec = _prompt_choice("New action spec not found. Create now?", ["y", "n"], "y")
        if create_spec == "y":
            action_type = _prompt_choice(
                "Action type",
                ["setting_toggle", "mqtt_action", "mqtt_message", "mqtt_publish", "show_image", "show_qr", "show_camera", "custom"],
                "custom",
            )
            action_specs, _ = _ensure_action_spec(action_specs, new_action, action_type)
        else:
            print("[menu-item] edit aborted: action spec missing")
            return 1

    action_specs_all = _all_action_specs(schema, action_specs)
    if new_action not in ("back", "open_page"):
        spec = action_specs_all.get(new_action)
        if isinstance(spec, dict):
            entry["action_spec"] = copy.deepcopy(spec)
    elif new_action == "back":
        entry["action_spec"] = {"kind": "menu_nav", "command": "back"}
    elif new_action == "open_page":
        entry.pop("action_spec", None)
    else:
        entry.pop("action_spec", None)

    if new_action != old_action:
        remaining_actions = {r["entry"].get("action") for r in _collect_entries(schema)}
        if old_action not in remaining_actions:
            _cleanup_unreferenced_action_spec(old_action, schema, action_specs)

    _save_menu_config_data(config, schema, action_specs)
    print(f"[menu-item] updated '{entry.get('id')}'")
    return 0


def _remove_item() -> int:
    config = _load_menu_config_data()
    schema = _load_menu_schema(config)
    action_specs = _load_legacy_action_specs(config)
    row = _select_container_then_entry(schema, "remove")
    if row is None:
        print("[menu-item] remove canceled")
        return 0

    path = row["path"]
    entry = _get_entry(schema, path)
    item_id = entry.get("id")
    action_id = entry.get("action")

    confirm = _prompt_choice(f"Remove item '{item_id}'?", ["y", "n"], "n")
    if confirm != "y":
        print("[menu-item] remove canceled")
        return 0

    container = _get_container(schema, path[:-1])
    del container[path[-1]]

    # Optional cleanup for unreferenced action specs + linked config artifacts.
    remaining_actions = {r["entry"].get("action") for r in _collect_entries(schema)}
    if action_id not in remaining_actions:
        _cleanup_unreferenced_action_spec(str(action_id), schema, action_specs)

    _save_menu_config_data(config, schema, action_specs)
    print(f"[menu-item] removed '{item_id}'")
    return 0


def _wizard() -> int:
    while True:
        print("[menu-item] Wizard")
        print("1) create: add a menu item and scaffold wiring")
        print("2) verify: verify one existing item wiring")
        print("3) edit: update an existing item")
        print("4) remove: remove an existing item")
        print("5) quit: exit wizard")
        mode = _prompt_choice("Choose mode", ["create", "verify", "edit", "remove", "quit"], "create")
        if mode == "quit":
            return 0
        if mode == "create":
            _create_item()
        elif mode == "verify":
            _verify_item()
        elif mode == "edit":
            _edit_item()
        else:
            _remove_item()


def main() -> int:
    parser = argparse.ArgumentParser(description="Menu item scaffolder")
    sub = parser.add_subparsers(dest="cmd", required=True)

    wizard = sub.add_parser("wizard", help="Interactive wizard")
    wizard.set_defaults(func=lambda _: _wizard())

    verify = sub.add_parser("verify", help="Interactive verify picker")
    verify.set_defaults(func=lambda _: _verify_item())

    args = parser.parse_args()
    try:
        return args.func(args)
    except UserCanceled:
        print("\n[menu-item] canceled by user.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
