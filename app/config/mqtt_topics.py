from __future__ import annotations

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCAL_TOPICS_PATH = ROOT / "local_config" / "mqtt_topics.json"
EXAMPLE_TOPICS_PATH = ROOT / "local_config" / "mqtt_topics.json.example"

TOPIC_DEFAULTS: dict[str, str] = {
    "mqtt_topic_music": "music",
    "mqtt_topic_devices": "screen_commands/incoming",
    "mqtt_topic_actions_outgoing": "screen_commands/outgoing",
    "mqtt_topic_update_music": "screen_commands/update_music",
    "mqtt_topic_alert": "screen_commands/alert",
    "mqtt_topic_doorbell_command": "",
    "mqtt_topic_doorbell": "",
    "mqtt_topic_printer_progress": "",
    "mqtt_topic_calendar": "",
    "mqtt_topic_print_start": "",
    "mqtt_topic_print_done": "",
    "mqtt_topic_print_cancelled": "",
    "mqtt_topic_print_change_filament": "",
    "mqtt_topic_print_change_z": "",
}


def _normalize_raw(raw) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    source = raw.get("topics")
    if not isinstance(source, dict):
        return {}
    out: dict[str, str] = {}
    for key in TOPIC_DEFAULTS:
        if key in source:
            out[key] = str(source.get(key, "") or "").strip()
    return out


def load_mqtt_topics() -> dict[str, str]:
    topics = copy.deepcopy(TOPIC_DEFAULTS)

    for path in (EXAMPLE_TOPICS_PATH, LOCAL_TOPICS_PATH):
        if path.exists():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            topics.update(_normalize_raw(raw))
    return topics


def save_local_mqtt_topics(topics: Mapping[str, object]) -> None:
    data = {"topics": {}}
    for key in TOPIC_DEFAULTS:
        data["topics"][key] = str(topics.get(key, TOPIC_DEFAULTS[key]) or "")
    LOCAL_TOPICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOCAL_TOPICS_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def apply_mqtt_topics_to_settings(settings_obj) -> dict[str, str]:
    topics = load_mqtt_topics()
    for key, value in topics.items():
        setattr(settings_obj, key, value)
    return topics
