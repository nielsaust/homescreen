#!/usr/bin/env python3
"""Mini migration for menu action specs toward declarative MQTT publishing fields."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ui.menu_config_loader import load_menu_config, save_local_menu_config

MQTT_TOPICS_LOCAL = ROOT / "local_config" / "mqtt_topics.json"
MQTT_TOPICS_EXAMPLE = ROOT / "local_config" / "mqtt_topics.json.example"


def _load_topics() -> dict[str, str]:
    for path in (MQTT_TOPICS_LOCAL, MQTT_TOPICS_EXAMPLE):
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        topics = payload.get("topics")
        if isinstance(topics, dict):
            return {str(k): str(v) for k, v in topics.items()}
    return {}


def _reverse_topic_map(topics: dict[str, str]) -> dict[str, str]:
    reverse: dict[str, str] = {}
    duplicate_values: set[str] = set()
    for key, topic in topics.items():
        if topic in reverse:
            duplicate_values.add(topic)
            continue
        reverse[topic] = key
    for topic in duplicate_values:
        reverse.pop(topic, None)
    return reverse


def migrate_menu_actions(normalize_mqtt_message_kind: bool = False) -> tuple[dict, list[str]]:
    config = copy.deepcopy(load_menu_config())
    action_specs = config.get("action_specs")
    if not isinstance(action_specs, dict):
        return config, []

    topics = _load_topics()
    reverse = _reverse_topic_map(topics)
    changes: list[str] = []

    for action_id, spec in action_specs.items():
        if not isinstance(spec, dict):
            continue
        kind = str(spec.get("kind", "")).strip()

        if kind == "mqtt_action":
            if not str(spec.get("topic", "")).strip() and not str(spec.get("topic_key", "")).strip():
                spec["topic_key"] = "actions_outgoing"
                changes.append(f"{action_id}: mqtt_action.topic_key=actions_outgoing")
            topic = str(spec.get("topic", "")).strip()
            if topic and not str(spec.get("topic_key", "")).strip() and topic in reverse:
                spec["topic_key"] = reverse[topic]
                changes.append(f"{action_id}: mqtt_action.topic_key={reverse[topic]} (from topic)")
            continue

        if kind == "mqtt_message":
            if "payload" not in spec:
                spec["payload"] = None
                changes.append(f"{action_id}: mqtt_message.payload=None")
            topic = str(spec.get("topic", "")).strip()
            if topic and not str(spec.get("topic_key", "")).strip() and topic in reverse:
                spec["topic_key"] = reverse[topic]
                changes.append(f"{action_id}: mqtt_message.topic_key={reverse[topic]} (from topic)")
            if normalize_mqtt_message_kind:
                spec["kind"] = "mqtt_publish"
                changes.append(f"{action_id}: kind mqtt_message -> mqtt_publish")
            continue

        if kind == "mqtt_publish":
            if "payload" not in spec:
                spec["payload"] = None
                changes.append(f"{action_id}: mqtt_publish.payload=None")
            topic = str(spec.get("topic", "")).strip()
            if topic and not str(spec.get("topic_key", "")).strip() and topic in reverse:
                spec["topic_key"] = reverse[topic]
                changes.append(f"{action_id}: mqtt_publish.topic_key={reverse[topic]} (from topic)")

    return config, changes


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate menu action specs to newer declarative MQTT fields")
    parser.add_argument("--apply", action="store_true", help="Write changes to local_config/menu.json")
    parser.add_argument(
        "--normalize-mqtt-message-kind",
        action="store_true",
        help="Convert mqtt_message kind to mqtt_publish",
    )
    args = parser.parse_args()

    config, changes = migrate_menu_actions(normalize_mqtt_message_kind=args.normalize_mqtt_message_kind)
    print("[menu-migrate] action spec migration")
    print(f"- changes: {len(changes)}")
    if changes:
        for line in changes:
            print(f"  - {line}")

    if not args.apply:
        print("[menu-migrate] dry-run only (pass --apply to write local_config/menu.json)")
        return 0

    if not changes:
        print("[menu-migrate] no changes to apply")
        return 0

    save_local_menu_config(config)
    print("[menu-migrate] wrote local_config/menu.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
