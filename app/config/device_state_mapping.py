from __future__ import annotations

import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOCAL_MAPPING_PATH = ROOT / "local_config" / "device_state_mapping.json"
EXAMPLE_MAPPING_PATH = ROOT / "local_config" / "device_state_mapping.json.example"


# Keep code generic: actual device fields live in local_config/device_state_mapping*.json
DEFAULT_DEVICE_STATE_MAPPING: dict = {"fields": {}}


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
