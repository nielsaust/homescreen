# Configuration Wizard

After cloning/pulling, run:

```bash
make install
make configuration
```

The wizard updates `local_config/settings.json` interactively.
MQTT topics are stored separately in `local_config/mqtt_topics.json`.

## Sections

1. MQTT base
- Enable/disable MQTT integration (`enable_mqtt`)
- Broker host/IP
- Port
- Username/password
- QoS
  - If MQTT is disabled, music/smart-home sections require: `First complete MQTT setup`.

2. Music integration
- Enable/disable music integration (`enable_music`)
- Music topic (`mqtt_topic_music`, stored in `local_config/mqtt_topics.json`)
- Home Assistant API base URL (`home_assistant_api_base_url`)
- Music display toggles (`media_show_titles`, `media_sanitize_titles`)

3. Weather integration
- Enable/disable weather integration (`enable_weather`)
- Display weather when idle (`show_weather_on_idle`)
- OpenWeather API key (`weather_api_key`)
- City ID (`weather_city_id`)
- Language (`weather_langage`)

4. Smart-home integration
- Device state topic (`mqtt_topic_devices`)
- Outgoing action topic (`mqtt_topic_actions_outgoing`)
- Alert topic (`mqtt_topic_alert`)
- Music refresh topic (`mqtt_topic_update_music`)
- Optional integrations (doorbell, calendar, printer)
  - When disabled, related MQTT topics are set to empty strings.
- Feature menu wiring
  - Music enabled: ensures `music` menu with media toggles exists.
  - Weather enabled: ensures `weather_options` menu with `show_weather_on_idle` exists.

5. Auto-start/update setup
- Linux/systemd only.
- On non-Linux platforms this option is shown as unavailable.

## Related Commands

- `make service-setup`: Linux systemd setup wizard (optional)
- `make mqtt-topics`: interactive MQTT topic overview/edit wizard
- `make menu-item-scaffold`: interactive menu item create/edit/remove/verify
- `make menu-contract-check`: validates menu/action/settings wiring
