#!/usr/bin/env python3
"""Generate a Home Assistant script YAML snippet for homescreen music MQTT payload."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SETTINGS_PATH = ROOT / "local_config" / "settings.json"
SETTINGS_EXAMPLE_PATH = ROOT / "settings.json.example"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config.mqtt_topics import load_mqtt_topics


def _load_settings() -> dict:
    path = SETTINGS_PATH if SETTINGS_PATH.exists() else SETTINGS_EXAMPLE_PATH
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    settings = _load_settings()
    topic = load_mqtt_topics(settings).get("mqtt_topic_music", "music")

    yaml_text = f"""script:
  action: mqtt.publish
  data_template:
    topic: {topic}
    payload: |-
      {{{{ {{
        "state": states('media_player.sonos_primary'),
        "title": state_attr('media_player.sonos_primary','media_title') | default(''),
        "artist": state_attr('media_player.sonos_primary','media_artist') | default(''),
        "album": state_attr('media_player.sonos_primary','media_album_name') | default(''),
        "channel": state_attr('media_player.sonos_primary','media_channel') | default(''),
        "album_art_api_url": state_attr('media_player.sonos_primary','entity_picture') | default('')
      }} | tojson }}}}
"""
    print(yaml_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
