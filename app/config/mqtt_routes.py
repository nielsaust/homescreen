from __future__ import annotations

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCAL_ROUTES_PATH = ROOT / "local_config" / "mqtt_routes.json"
EXAMPLE_ROUTES_PATH = ROOT / "local_config" / "mqtt_routes.json.example"


DEFAULT_ROUTES: list[dict] = [
    {"topic_key": "music", "handler": "music_update", "phase": "essential"},
    {"topic_key": "devices", "handler": "device_states_update", "phase": "essential"},
    {"topic_key": "doorbell", "handler": "overlay_camera", "camera_id": "doorbell", "phase": "nonessential"},
    {"topic_key": "printer_progress", "handler": "printer_progress", "phase": "nonessential"},
    {"topic_key": "calendar", "handler": "overlay_calendar", "phase": "nonessential"},
    {"topic_key": "alert", "handler": "overlay_alert", "phase": "nonessential"},
    {"topic_key": "print_start", "handler": "print_status_show", "reset": True, "phase": "nonessential"},
    {"topic_key": "print_done", "handler": "print_attention", "phase": "nonessential"},
    {"topic_key": "print_change_filament", "handler": "print_attention", "phase": "nonessential"},
    {"topic_key": "print_cancelled", "handler": "print_close", "phase": "nonessential"},
    {"topic_key": "print_change_z", "handler": "print_cancel_attention", "phase": "nonessential"},
]


def load_mqtt_routes() -> list[dict]:
    routes = copy.deepcopy(DEFAULT_ROUTES)
    for path in (EXAMPLE_ROUTES_PATH, LOCAL_ROUTES_PATH):
        if not path.exists():
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        candidate = raw.get("routes")
        if isinstance(candidate, list):
            routes = [entry for entry in candidate if isinstance(entry, dict)]
    return routes


def resolve_topic_routes(topics: dict[str, str], routes: list[dict]) -> list[dict]:
    resolved: list[dict] = []
    for route in routes:
        topic_key = str(route.get("topic_key", "")).strip()
        if not topic_key:
            continue
        topic = str(topics.get(topic_key, "")).strip()
        if not topic:
            continue
        item = copy.deepcopy(route)
        item["topic"] = topic
        resolved.append(item)
    return resolved
