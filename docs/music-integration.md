# Music Integration (MQTT + Home Assistant)

## Blueprint Import

Use this import link format in Home Assistant:

`https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https://mijn-github-url-naar-de-yaml`

For this repository, publish and reference:

`homeassistant/media_player_to_mqtt_music_blueprint.yaml`

Then create an automation from that blueprint and configure:

- `media_player_entity`: the player to track
- `mqtt_topic`: `music`
- `include_music_assistant_art`:
  - `true` for Music Assistant players
  - `false` for regular players

## App Configuration (Homescreen)

Ensure the app is configured to consume the same MQTT topic:

1. Run `make configuration`
2. Enable:
   - `enable_mqtt: true`
   - `enable_music: true`
3. Ensure topic mapping includes:
   - `music` topic key -> `music` (in `local_config/mqtt_topics.json`)
4. If you include Music Assistant artwork field in the blueprint:
   - set `prefer_music_assistant_url: true` in `local_config/settings.json`

## Expected MQTT Payload

The app consumes music messages on the configured `music` topic with this shape:

```json
{
  "state": "playing|paused|idle",
  "title": "Track title",
  "artist": "Artist name",
  "album": "Album name",
  "channel": "Optional channel/source",
  "album_art_api_url": "/api/media_player_proxy/... or full URL",
  "album_art_music_assistant_url": "https://... (optional)"
}
```

Notes:

- `album_art_music_assistant_url` is preferred when `prefer_music_assistant_url=true`.
- The app also accepts legacy alias `album_art_api_url_music_assistant`.

## Optional Script Generator

Generate a Home Assistant script snippet from current local settings:

```bash
python3 tools/generate_ha_music_script.py
```
