from __future__ import annotations

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCAL_MENU_PATH = ROOT / "local_config" / "menu.json"
EXAMPLE_MENU_PATH = ROOT / "local_config" / "menu.json.example"


def _load_raw() -> dict:
    if LOCAL_MENU_PATH.exists():
        return json.loads(LOCAL_MENU_PATH.read_text(encoding="utf-8"))
    if EXAMPLE_MENU_PATH.exists():
        return json.loads(EXAMPLE_MENU_PATH.read_text(encoding="utf-8"))
    return {
        "menu_schema": [],
        "button_setting_requirements": {},
        "action_specs": {},
        "state_specs": [],
    }


def load_menu_config() -> dict:
    return _load_raw()


def save_local_menu_config(data: dict) -> None:
    LOCAL_MENU_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOCAL_MENU_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def get_menu_schema() -> list[dict]:
    return copy.deepcopy(load_menu_config().get("menu_schema", []))


def _flatten_entries(entries: list[dict]) -> list[dict]:
    out: list[dict] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        out.append(entry)
        children = entry.get("screen") or []
        if isinstance(children, list):
            out.extend(_flatten_entries(children))
    return out


def get_button_setting_requirements() -> dict[str, list[str]]:
    config = load_menu_config()
    merged: dict[str, list[str]] = copy.deepcopy(config.get("button_setting_requirements", {}))
    entries = _flatten_entries(config.get("menu_schema", []))
    for entry in entries:
        button_id = str(entry.get("id", "")).strip()
        if not button_id:
            continue
        requirements = entry.get("setting_requirements")
        if isinstance(requirements, list):
            normalized = [str(item).strip() for item in requirements if str(item).strip()]
            if normalized:
                merged[button_id] = normalized
    return merged


def get_action_specs() -> dict[str, dict]:
    config = load_menu_config()
    merged: dict[str, dict] = copy.deepcopy(config.get("action_specs", {}))
    entries = _flatten_entries(config.get("menu_schema", []))
    for entry in entries:
        action_id = str(entry.get("action", "")).strip()
        if not action_id or action_id in ("back", "open_page"):
            continue
        spec = entry.get("action_spec")
        if isinstance(spec, dict) and spec:
            merged[action_id] = copy.deepcopy(spec)
    return merged


def get_state_specs() -> list[dict]:
    config = load_menu_config()
    merged: list[dict] = copy.deepcopy(config.get("state_specs", []))
    entries = _flatten_entries(config.get("menu_schema", []))
    for entry in entries:
        spec = entry.get("state_spec")
        if not isinstance(spec, dict):
            continue
        normalized = copy.deepcopy(spec)
        if not normalized.get("button_id"):
            button_id = str(entry.get("id", "")).strip()
            if button_id:
                normalized["button_id"] = button_id
        if normalized.get("button_id"):
            merged.append(normalized)
    return merged
