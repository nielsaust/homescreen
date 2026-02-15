#!/usr/bin/env python3
"""Interactive menu item wizard with create/edit/remove/verify flows."""

from __future__ import annotations

import argparse
import ast
import copy
import json
import pprint
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.controllers.action_registry import ACTION_SPECS
from app.ui.menu_registry import MENU_SCHEMA

MENU_REGISTRY = ROOT / "app" / "ui" / "menu_registry.py"
ACTION_REGISTRY = ROOT / "app" / "controllers" / "action_registry.py"
ACTION_DISPATCHER = ROOT / "app" / "controllers" / "action_dispatcher.py"
SETTINGS_EXAMPLE = ROOT / "settings.json.example"
SETTINGS_LOCAL = ROOT / "settings.json"
BUTTON_IMAGES_DIR = ROOT / "images" / "buttons"


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


def _replace_assignment(path: Path, var_name: str, new_value: Any) -> None:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    target_node = None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == var_name:
                    target_node = node
                    break
        if target_node:
            break
    if target_node is None:
        raise RuntimeError(f"Could not find assignment for {var_name} in {path}")

    lines = text.splitlines()
    start = target_node.lineno - 1
    end = target_node.end_lineno
    replacement = f"{var_name} = {pprint.pformat(new_value, width=120, sort_dicts=False)}"
    new_lines = lines[:start] + [replacement] + lines[end:]
    path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def _load_menu_schema() -> list[dict[str, Any]]:
    return copy.deepcopy(MENU_SCHEMA)


def _load_action_specs() -> dict[str, dict[str, Any]]:
    return copy.deepcopy(ACTION_SPECS)


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


def _build_submenu(action_id: str, label: str) -> list[dict[str, Any]]:
    base = _sanitize_identifier(action_id)
    return [
        {"id": f"{base}_back", "text": "Back", "image": "back.png", "action": "back"},
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
        action_specs[action_id] = {"kind": "mqtt_message", "topic": topic}
        return action_specs, None

    if item_type == "show_image":
        image_file = _prompt_required("Image file to show", "qr-wifi.png")
        action_specs[action_id] = {"kind": "show_image", "image": image_file}
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
    schema = _load_menu_schema()
    action_specs = _load_action_specs()

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
        ["setting_toggle", "mqtt_action", "mqtt_message", "show_image", "custom", "submenu"],
        "custom",
    )

    action_specs, _ = _ensure_action_spec(action_specs, action_id, item_type)

    new_entry = {"id": item_id, "text": label, "image": icon, "action": action_id}
    if item_type == "submenu":
        new_entry["action"] = "open_page"
        new_entry["screen"] = _build_submenu(action_id, label)

    target = _get_container(schema, container["path"])
    target.append(new_entry)

    _replace_assignment(MENU_REGISTRY, "MENU_SCHEMA", schema)
    _replace_assignment(ACTION_REGISTRY, "ACTION_SPECS", action_specs)
    print(f"[menu-item] created '{item_id}' in {container['label']}")
    return 0


def _verify_item() -> int:
    schema = _load_menu_schema()
    action_specs = _load_action_specs()
    row = _select_container_then_entry(schema, "verify")
    if row is None:
        print("[menu-item] verify canceled")
        return 0
    entry = row["entry"]
    action_id = entry.get("action")
    if action_id not in ("back", "open_page") and action_id not in action_specs:
        print(f"[menu-item] missing action spec for '{action_id}'")
        return 1
    print(f"[menu-item] verify OK id='{entry.get('id')}' action='{action_id}'")
    return 0


def _edit_item() -> int:
    schema = _load_menu_schema()
    action_specs = _load_action_specs()
    row = _select_container_then_entry(schema, "edit")
    if row is None:
        print("[menu-item] edit canceled")
        return 0

    entry = _get_entry(schema, row["path"])
    old_action = entry.get("action")
    print("Press Enter to keep current value.")
    new_text = _prompt("Label", entry.get("text", ""))
    keep_icon = _prompt_choice("Keep current icon?", ["y", "n"], "y")
    if keep_icon == "y":
        new_image = entry.get("image", "tools.png")
    else:
        new_image = _choose_icon(entry.get("image", "tools.png"))
    new_action = _prompt("Action id", old_action)
    entry["text"] = new_text
    entry["image"] = new_image
    entry["action"] = new_action

    if new_action != old_action and new_action not in ("back", "open_page") and new_action not in action_specs:
        create_spec = _prompt_choice("New action spec not found. Create now?", ["y", "n"], "y")
        if create_spec == "y":
            action_type = _prompt_choice(
                "Action type",
                ["setting_toggle", "mqtt_action", "mqtt_message", "show_image", "custom"],
                "custom",
            )
            action_specs, _ = _ensure_action_spec(action_specs, new_action, action_type)
        else:
            print("[menu-item] edit aborted: action spec missing")
            return 1

    _replace_assignment(MENU_REGISTRY, "MENU_SCHEMA", schema)
    _replace_assignment(ACTION_REGISTRY, "ACTION_SPECS", action_specs)
    print(f"[menu-item] updated '{entry.get('id')}'")
    return 0


def _remove_item() -> int:
    schema = _load_menu_schema()
    action_specs = _load_action_specs()
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

    # Optional cleanup for unreferenced action specs
    remaining_actions = {
        row["entry"].get("action")
        for row in _collect_entries(schema)
    }
    if action_id in action_specs and action_id not in remaining_actions:
        if _prompt_choice(f"Action '{action_id}' is now unreferenced. Remove action spec?", ["y", "n"], "y") == "y":
            spec = action_specs.pop(action_id)
            if spec.get("kind") == "setting_toggle":
                setting_key = spec.get("attr")
                if setting_key and _prompt_choice(
                    f"Remove setting key '{setting_key}' from settings files?", ["y", "n"], "n"
                ) == "y":
                    _remove_setting_key(setting_key)

    _replace_assignment(MENU_REGISTRY, "MENU_SCHEMA", schema)
    _replace_assignment(ACTION_REGISTRY, "ACTION_SPECS", action_specs)
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
