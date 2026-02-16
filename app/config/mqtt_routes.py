from __future__ import annotations

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCAL_ROUTES_PATH = ROOT / "local_config" / "mqtt_routes.json"
EXAMPLE_ROUTES_PATH = ROOT / "local_config" / "mqtt_routes.json.example"

def _read_routes(path: Path) -> list[dict] | None:
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    candidate = raw.get("routes")
    if not isinstance(candidate, list):
        return None
    return [entry for entry in candidate if isinstance(entry, dict)]


def load_mqtt_routes() -> list[dict]:
    # File-first: example provides baseline, local file can override.
    routes = _read_routes(EXAMPLE_ROUTES_PATH) or []
    local_routes = _read_routes(LOCAL_ROUTES_PATH)
    if local_routes is not None:
        routes = local_routes
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
