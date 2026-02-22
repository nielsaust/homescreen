# Settings Workflow

Use this workflow to keep `local_config/settings.json` and `settings.json.example` aligned without leaking secrets.

Note: MQTT topics and camera credentials/URLs are stored in:

- `local_config/mqtt_topics.json`
- `local_config/cameras.json`

## Commands

Check differences (keys and type mismatches):

```bash
make settings-check
```

Update example with keys that exist only in local settings:

```bash
make settings-update-example
```

Update local settings with keys that exist only in example:

```bash
make settings-update-local
```

Preview keys that exist only in local settings (and could be removed):

```bash
make settings-prune-local-preview
```

Remove local-only keys from `local_config/settings.json`:

```bash
make settings-prune-local
```

## Recommended routine

1. Add/change settings in `local_config/settings.json` while developing.
2. If migrating from older setup, run `make migrate-local-config` once.
3. Run `make settings-update-example`.
4. Review `settings.json.example` and commit.
5. Run `make settings-check` to confirm both files are aligned.
6. Optionally run `make settings-prune-local-preview` and `make settings-prune-local` to remove stale local-only keys.

The sync tool preserves key ordering based on `settings.json.example`, so new keys remain predictable across environments.

## Logging-related settings

Useful runtime keys:

- `log_profile`: logging profile preset (`default`, `dev`, `pi`, `quiet`)
- `log_debug_enabled`: single global debug switch (`true` => root/console/file all `DEBUG`)
- `log_console_level`: console/journal verbosity
- `log_file_level`: date-based file log verbosity
- `log_noisy_third_party_debug`: enable noisy third-party debug logs
- `log_noisy_loggers`: list of logger names to treat as noisy
- `log_enable_domain_levels`: opt-in for per-logger overrides (default `false`)
- `log_domain_levels`: per-logger explicit levels map (used only when `log_enable_domain_levels=true`)
- `app_environment`: controls dev-only menu visibility (`production` hides `dev_only` items)
- `ui_locale`: UI language for system texts (`en`, `nl`; fallback to English)
- `menu_edit_hold_ms`: long-press duration (ms) to open runtime menu edit mode
- `media_show_album`: show/hide album title in music overlay text
- `weather_time_locale`: locale used for weather date rendering (LC_TIME)
- `weather_date_format`: strftime format string for weather date label

## Weather date/locale options

- `weather_time_locale` examples:
  - `nl_NL.UTF-8`
  - `en_US.UTF-8`
  - `de_DE.UTF-8`
  - empty string (`""`) to use system default locale
- `weather_date_format` examples:
  - `%-d %b` -> `14 feb`
  - `%a %-d %b` -> `vr 14 feb`
  - `%d-%m` -> `14-02`
  - `%A %-d %B` -> `vrijdag 14 februari`

Space guidance for the idle weather top-right label:

- Prefer short formats for 720x720 screens.
- `%A` (full weekday) and `%B` (full month) can be long in some locales.
- If text clips/overlaps, use shorter format (`%-d %b` or `%a %-d %b`).

Locale setup:

- On Linux/Pi, run `make locale-setup` to enable/generate missing locales.
- On macOS/Windows, install locales via OS settings/package manager.

UI localization catalogs:

- Built-in runtime catalogs: `app/locales/en.json`, `app/locales/nl.json`
- Optional local overrides: `local_config/i18n/<locale>.json`
- Usage guide and coding pattern: `docs/localization.md`

## Secret safety

- `local_config/settings.json` is local-only and gitignored.
- `settings-update-example` uses placeholder values for sensitive keys (`password`, `secret`, `token`, `api_key`, `dsn`).
- The check output shows only paths and types, never secret values.
- `settings-prune-local-preview` is a dry run; removal only happens with `settings-prune-local` (apply mode).
