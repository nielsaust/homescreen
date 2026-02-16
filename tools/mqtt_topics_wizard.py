#!/usr/bin/env python3
"""Interactive MQTT topics overview/edit helper."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config.mqtt_topics import TOPIC_DEFAULTS, load_mqtt_topics, save_local_mqtt_topics

SETTINGS_PATH = ROOT / "local_config" / "settings.json"
SETTINGS_EXAMPLE_PATH = ROOT / "settings.json.example"


def _load_settings() -> dict:
    path = SETTINGS_PATH if SETTINGS_PATH.exists() else SETTINGS_EXAMPLE_PATH
    return json.loads(path.read_text(encoding="utf-8"))


def _prompt(text: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{text}{suffix}: ").strip()
    return value if value else default


def _print_topics(topics: dict) -> list[str]:
    keys = list(TOPIC_DEFAULTS.keys())
    print("\n[mqtt-topics] Current topics")
    for idx, key in enumerate(keys, start=1):
        print(f"{idx:2d}) {key} = {topics.get(key, '')!r}")
    return keys


def _edit_topic(topics: dict) -> None:
    keys = _print_topics(topics)
    raw = _prompt("Choose topic number to edit (or Enter to cancel)", "")
    if not raw:
        return
    if not raw.isdigit() or not (1 <= int(raw) <= len(keys)):
        print("[mqtt-topics] invalid selection")
        return
    key = keys[int(raw) - 1]
    topics[key] = _prompt(f"New value for {key}", str(topics.get(key, "")))
    print(f"[mqtt-topics] updated {key}")


def main() -> int:
    _ = _load_settings()
    topics = load_mqtt_topics()

    try:
        while True:
            print("\n=== MQTT Topics Wizard ===")
            print("1) Overview")
            print("2) Edit one topic")
            print("3) Reset all to defaults")
            print("4) Save and exit")
            print("5) Exit without saving")
            choice = _prompt("Choose option", "1")

            if choice == "1":
                _print_topics(topics)
            elif choice == "2":
                _edit_topic(topics)
            elif choice == "3":
                topics = dict(TOPIC_DEFAULTS)
                print("[mqtt-topics] reset to defaults")
            elif choice == "4":
                save_local_mqtt_topics(topics)
                print("[mqtt-topics] saved to local_config/mqtt_topics.json")
                return 0
            elif choice == "5":
                print("[mqtt-topics] exiting without saving")
                return 0
            else:
                print("Invalid option.")
    except KeyboardInterrupt:
        print("\n[mqtt-topics] canceled by user.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
