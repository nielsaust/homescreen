from __future__ import annotations

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCAL_STARTUP_ACTIONS_PATH = ROOT / "local_config" / "startup_actions.json"
EXAMPLE_STARTUP_ACTIONS_PATH = ROOT / "local_config" / "startup_actions.json.example"

DEFAULT_STARTUP_ACTIONS: dict = {"actions": []}


def _read(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    actions = payload.get("actions")
    if not isinstance(actions, list):
        return None
    return payload


def load_startup_actions_config() -> dict:
    config = _read(EXAMPLE_STARTUP_ACTIONS_PATH) or copy.deepcopy(DEFAULT_STARTUP_ACTIONS)
    local = _read(LOCAL_STARTUP_ACTIONS_PATH)
    if local is not None:
        config = local
    return config


def get_startup_actions() -> list[dict]:
    actions = load_startup_actions_config().get("actions", [])
    return [entry for entry in actions if isinstance(entry, dict)]
