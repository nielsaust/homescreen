# Music Integration (MQTT + Home Assistant)

## Blueprint Import

State-change blueprint import link:

`https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https://github.com/nielsaust/homescreen/blob/main/homeassistant/media_player_to_mqtt_music_blueprint.yaml`

Manual refresh blueprint import link:

`https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https://github.com/nielsaust/homescreen/blob/main/homeassistant/manual_music_refresh_to_mqtt_blueprint.yaml`

Then create automations from these blueprints and configure:

- `media_player_entity`: the player to track
- `mqtt_topic`: `music`
- `include_music_assistant_art`:
  - `true` for Music Assistant players
  - `false` for regular players
- Manual refresh blueprint defaults:
  - request topic: `screen_commands/update_music`
  - publish topic: `music`

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
5. For all available HA blueprints in this repo, see:
   - `docs/home-assistant-blueprints.md`

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
