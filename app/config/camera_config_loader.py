from __future__ import annotations

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCAL_CAMERAS_PATH = ROOT / "local_config" / "cameras.json"
EXAMPLE_CAMERAS_PATH = ROOT / "local_config" / "cameras.json.example"


def _load_raw() -> dict:
    for path in (LOCAL_CAMERAS_PATH, EXAMPLE_CAMERAS_PATH):
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            cameras = data.get("cameras", {})
            if isinstance(cameras, dict):
                return {"cameras": cameras}
    return {"cameras": {}}


def load_camera_config() -> dict:
    return _load_raw()


def get_camera_specs() -> dict[str, dict]:
    return copy.deepcopy(load_camera_config().get("cameras", {}))
