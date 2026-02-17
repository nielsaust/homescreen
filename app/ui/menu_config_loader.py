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


def get_menu_schema(profile: str | None = None) -> list[dict]:
    config = load_menu_config()
    selected_profile = str(profile or "").strip().lower()

    if selected_profile in {"prod", "minimal"}:
        schema = config.get("minimal_menu_schema")
        if isinstance(schema, list):
            return copy.deepcopy(schema)

    if selected_profile in {"dev", "full"}:
        schema = config.get("dev_menu_schema")
        if isinstance(schema, list):
            return copy.deepcopy(schema)

    # Default profile or missing profile-specific schemas fall back to main schema.
    return copy.deepcopy(config.get("menu_schema", []))


def get_button_setting_requirements() -> dict[str, list[str]]:
    return copy.deepcopy(load_menu_config().get("button_setting_requirements", {}))


def get_action_specs() -> dict[str, dict]:
    return copy.deepcopy(load_menu_config().get("action_specs", {}))


def get_state_specs() -> list[dict]:
    return copy.deepcopy(load_menu_config().get("state_specs", []))
