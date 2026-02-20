# Configuration Wizard

After cloning/pulling, run:

```bash
make install
make migrate-local-config  # one-time, only when migrating older local setup
make configuration
```

The wizard updates `local_config/settings.json` interactively.
MQTT topics are stored separately in `local_config/mqtt_topics.json`.
`make install` creates a default `local_config/menu.json` from `local_config/menu.json.example`.
If a local menu already exists, install asks whether it should be overwritten.
Built-in localization catalogs live in `app/locales/*.json` and are selected via `ui_locale`.
Optional per-install overrides can be placed in `local_config/i18n/<locale>.json`.

`app_environment` in `local_config/settings.json` controls visibility of dev-only menu items:

- `production` (default): hide items marked with `"dev_only": true`.
- non-production values (for example `development`): show dev-only items.

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
- Music topic (`music`, stored in `local_config/mqtt_topics.json`)
- Home Assistant API base URL (`home_assistant_api_base_url`)
- Music display toggles (`media_show_titles`, `media_show_album`, `media_sanitize_titles`)
- Startup refresh behavior
  - Configure startup-triggered MQTT calls in `local_config/startup_actions.json`.
  - Example includes refresh of current music state via topic key `update_music`.

3. Weather integration

- Enable/disable weather integration (`enable_weather`)
- Display weather when idle (`show_weather_on_idle`)
- OpenWeather API key (`weather_api_key`)
- City ID (`weather_city_id`)
- Language (`ui_locale`)
- Date locale for idle weather clock (`weather_time_locale`, e.g. `nl_NL.UTF-8`; enter `system` to use OS default)
- Date format for idle weather clock (`weather_date_format`, strftime format)
- OpenWeather/network resilience
  - Weather fetch runs async so temporary API outages do not block menu/idle interaction.
  - `network_check_refresh_interval_seconds` controls refresh interval for the in-app `Check network` screen.

Localization

- App locale (`ui_locale`, e.g. `en`, `nl`)
- Standard UI texts use i18n keys with fallback to English.
- Custom user-added menu item texts are not localized by this step.
- Full guide: `docs/localization.md`

4. Smart-home integration

- Device state topic (`devices`)
- Outgoing action topic (`actions_outgoing`)
- Alert topic (`alert`)
- Music refresh topic (`update_music`)
- Optional integrations (doorbell, calendar, printer)
  - When disabled, related MQTT topics are set to empty strings.
- Feature menu wiring
  - Music enabled: ensures `music` menu with media toggles exists.
  - Weather enabled: ensures `weather_options` menu with `show_weather_on_idle` exists.
  - If one of these items already exists, the wizard asks whether to overwrite it with the default structure.

5. Auto-start/update setup

- Linux/systemd only.
- On non-Linux platforms this option is shown as unavailable.
- On Raspberry Pi this is recommended:
  - installs/updates `homescreen.service` and deploy timer units
  - configures `DISPLAY=:0` + `XAUTHORITY`
  - configures a startup wait for X display availability (`/tmp/.X11-unix/X0`)
  - enables app autostart on `graphical.target`

## Dev Outage Simulation

For runtime resilience testing (without real outages), enable dev mode and use the dev-only toggles in `Opties`:

- `Sim internet outage`
- `Sim weather outage`
- `Sim MQTT outage`

Settings keys:

- `enable_network_simulation` (master switch)
- `simulate_outage_internet`
- `simulate_outage_weather_service`
- `simulate_outage_mqtt`

When enabled, the new `Check network` screen reflects simulated failures immediately.

## Related Commands

- `make service-setup`: Linux systemd setup wizard (optional)
- `make mqtt-topics`: interactive MQTT topic overview/edit wizard
- `make locale-setup`: Linux locale generator helper (`locale-gen`)
- `make menu-item-scaffold`: interactive menu item create/edit/remove/verify
- `make menu-contract-check`: validates menu/action/settings wiring
