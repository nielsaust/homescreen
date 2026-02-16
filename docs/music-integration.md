# Music Integration (MQTT + Home Assistant)

## Expected MQTT Payload

The app expects music messages on `mqtt_topic_music` (configured in `local_config/mqtt_topics.json`) with this JSON shape:

```json
{
  "state": "playing|paused|idle",
  "title": "Track title",
  "artist": "Artist name",
  "album": "Album name",
  "channel": "Optional channel/source",
  "album_art_api_url": "/api/media_player_proxy/..."
}
```

## Home Assistant Script Example

Generate the script snippet from current settings:

```bash
python3 tools/generate_ha_music_script.py
```

This uses your configured `mqtt_topic_music` from `local_config/mqtt_topics.json`.

## Blueprint

A reusable Home Assistant blueprint is planned.  
Until then, use the generated script snippet above.
