from __future__ import annotations

import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOCAL_MAPPING_PATH = ROOT / "local_config" / "device_state_mapping.json"
EXAMPLE_MAPPING_PATH = ROOT / "local_config" / "device_state_mapping.json.example"


DEFAULT_DEVICE_STATE_MAPPING: dict = {
    "fields": {
        "harmony_state": {"source": "harmony_state", "type": "string", "default": "Off"},
        "cover_kitchen": {"source": "cover_kitchen", "type": "float", "default": 0},
        "living_room_temp": {"source": "living_room_temp", "type": "float", "default": 15},
        "light_tafel": {"source": "light_tafel", "type": "light"},
        "light_keuken": {"source": "light_keuken", "type": "light"},
        "light_kleur": {"source": "light_kleur", "type": "light"},
        "light_woonkamer": {"source": "light_woonkamer", "type": "light"},
        "sleep_mode": {
            "source": "sleep_mode",
            "type": "on_off_bool",
            "default": False,
            "track_original": True,
        },
        "trash_warning": {"source": "trash_warning", "type": "on_off_bool", "default": False},
        "bed_heating_on": {"source": "bed_heating_on", "type": "on_off_bool", "default": False},
        "playstation_power": {"source": "playstation_power", "type": "on_off_bool", "default": False},
        "playstation_available": {
            "source": "playstation_power",
            "type": "availability",
            "unavailable_value": "unavailable",
            "default": True,
        },
    }
}


def _read_mapping(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    fields = payload.get("fields")
    if not isinstance(fields, dict):
        return None
    return payload


def load_device_state_mapping() -> dict:
    # File-first: example sets baseline; local file overrides.
    mapping = _read_mapping(EXAMPLE_MAPPING_PATH) or copy.deepcopy(DEFAULT_DEVICE_STATE_MAPPING)
    local_mapping = _read_mapping(LOCAL_MAPPING_PATH)
    if local_mapping is not None:
        mapping = local_mapping
    return mapping
