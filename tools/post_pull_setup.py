#!/usr/bin/env python3
"""Post-pull/project bootstrap tasks that should always be safe and idempotent."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SETTINGS = ROOT / "local_config" / "settings.json"
SETTINGS_EXAMPLE = ROOT / "settings.json.example"
MQTT_TOPICS = ROOT / "local_config" / "mqtt_topics.json"
MQTT_TOPICS_EXAMPLE = ROOT / "local_config" / "mqtt_topics.json.example"
MQTT_ROUTES = ROOT / "local_config" / "mqtt_routes.json"
MQTT_ROUTES_EXAMPLE = ROOT / "local_config" / "mqtt_routes.json.example"
DEVICE_STATE_MAPPING = ROOT / "local_config" / "device_state_mapping.json"
DEVICE_STATE_MAPPING_EXAMPLE = ROOT / "local_config" / "device_state_mapping.json.example"


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=4) + "\n", encoding="utf-8")


def ensure_settings_file() -> None:
    if SETTINGS.exists():
        return
    SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SETTINGS_EXAMPLE, SETTINGS)
    print("[setup] created local_config/settings.json from settings.json.example")


def ensure_mqtt_topics_file() -> None:
    if MQTT_TOPICS.exists():
        return
    MQTT_TOPICS.parent.mkdir(parents=True, exist_ok=True)
    if MQTT_TOPICS_EXAMPLE.exists():
        shutil.copy2(MQTT_TOPICS_EXAMPLE, MQTT_TOPICS)
        print("[setup] created local_config/mqtt_topics.json from local_config/mqtt_topics.json.example")


def ensure_mqtt_routes_file() -> None:
    if MQTT_ROUTES.exists():
        return
    MQTT_ROUTES.parent.mkdir(parents=True, exist_ok=True)
    if MQTT_ROUTES_EXAMPLE.exists():
        shutil.copy2(MQTT_ROUTES_EXAMPLE, MQTT_ROUTES)
        print("[setup] created local_config/mqtt_routes.json from local_config/mqtt_routes.json.example")


def ensure_device_state_mapping_file() -> None:
    if DEVICE_STATE_MAPPING.exists():
        return
    DEVICE_STATE_MAPPING.parent.mkdir(parents=True, exist_ok=True)
    if DEVICE_STATE_MAPPING_EXAMPLE.exists():
        shutil.copy2(DEVICE_STATE_MAPPING_EXAMPLE, DEVICE_STATE_MAPPING)
        print(
            "[setup] created local_config/device_state_mapping.json "
            "from local_config/device_state_mapping.json.example"
        )


def ensure_settings_keys() -> None:
    local = _load_json(SETTINGS)
    example = _load_json(SETTINGS_EXAMPLE)
    missing = [key for key in example.keys() if key not in local]
    if not missing:
        return
    for key in missing:
        local[key] = example[key]
    _save_json(SETTINGS, local)
    print(f"[setup] added missing settings keys to local_config/settings.json: {len(missing)}")


def ensure_directories() -> None:
    for rel in ("logs", ".sim", "local_config"):
        path = ROOT / rel
        path.mkdir(parents=True, exist_ok=True)
        print(f"[setup] ensured directory: {rel}")


def main() -> int:
    ensure_settings_file()
    ensure_mqtt_topics_file()
    ensure_mqtt_routes_file()
    ensure_device_state_mapping_file()
    ensure_settings_keys()
    ensure_directories()
    print("[setup] post-pull setup complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
