# Home Assistant Blueprints

This repository provides ready-to-import Home Assistant automation blueprints for homescreen.

## 1) Music State -> MQTT (`music`)

Blueprint file:

- `homeassistant/media_player_to_mqtt_music_blueprint.yaml`

Import link:

- `https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https://github.com/nielsaust/homescreen/blob/main/homeassistant/media_player_to_mqtt_music_blueprint.yaml`
- [Import Blueprint into my Home Assistant](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https://github.com/nielsaust/homescreen/blob/main/homeassistant/media_player_to_mqtt_music_blueprint.yaml)

Use this when you want a media player to publish current track state/art to homescreen.

Required app-side config:

- `enable_mqtt: true`
- `enable_music: true`
- MQTT topic mapping key `music` -> topic `music` in `local_config/mqtt_topics.json`
- Optional: set `prefer_music_assistant_url: true` in `local_config/settings.json` if you publish Music Assistant artwork URL.

## 2) Device States -> MQTT (`screen_commands/incoming`)

Blueprint file:

- `homeassistant/device_states_to_mqtt_homescreen_blueprint.yaml`

Import link:

- `https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https://github.com/nielsaust/homescreen/blob/main/homeassistant/device_states_to_mqtt_homescreen_blueprint.yaml`
- [Import Blueprint into my Home Assistant](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https://github.com/nielsaust/homescreen/blob/main/homeassistant/device_states_to_mqtt_homescreen_blueprint.yaml)

Use this when you want to publish smart-home state fields (lights/covers/sleep/etc.) in one JSON payload for homescreen menus/actions.

Required app-side config:

- `enable_mqtt: true`
- MQTT topic mapping key `devices` -> topic `screen_commands/incoming` in `local_config/mqtt_topics.json`
- Ensure your `local_config/device_state_mapping.json` matches the payload field names you publish.

## 3) MQTT Commands -> Home Assistant (`screen_commands/outgoing`)

Blueprint file:

- `homeassistant/mqtt_commands_to_home_assistant_blueprint.yaml`

Import link:

- `https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https://github.com/nielsaust/homescreen/blob/main/homeassistant/mqtt_commands_to_home_assistant_blueprint.yaml`
- [Import Blueprint into my Home Assistant](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https://github.com/nielsaust/homescreen/blob/main/homeassistant/mqtt_commands_to_home_assistant_blueprint.yaml)

Use this when you want Home Assistant to listen for homescreen commands and execute mapped actions (covers, lights, scenes, media controls, scripts, automations, calendar publish).

Required app-side config:

- `enable_mqtt: true`
- MQTT topic mapping key `actions_outgoing` -> topic `screen_commands/outgoing` in `local_config/mqtt_topics.json`
- In the blueprint inputs, map the entities/scripts/automations you actually use. Unused inputs can stay empty.

## 4) Manual Music Refresh -> MQTT (`screen_commands/update_music`)

Blueprint file:

- `homeassistant/manual_music_refresh_to_mqtt_blueprint.yaml`

Import link:

- `https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https://github.com/nielsaust/homescreen/blob/main/homeassistant/manual_music_refresh_to_mqtt_blueprint.yaml`
- [Import Blueprint into my Home Assistant](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https://github.com/nielsaust/homescreen/blob/main/homeassistant/manual_music_refresh_to_mqtt_blueprint.yaml)

Use this when homescreen asks for an immediate music state publish (startup sync or manual refresh button).

Required app-side config:

- `enable_mqtt: true`
- `enable_music: true`
- MQTT topic mapping key `music` -> topic `music` in `local_config/mqtt_topics.json`
- The app publishes manual refresh requests to `screen_commands/update_music` (default in this blueprint).

## Notes

- All blueprints use modern Home Assistant automation YAML syntax (`triggers`/`actions`, `action: ...`).
- If your Home Assistant setup is older, update HA or adapt syntax manually.
