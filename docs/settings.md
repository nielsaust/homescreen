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
- `log_console_level`: console/journal verbosity
- `log_file_level`: date-based file log verbosity
- `log_noisy_third_party_debug`: enable noisy third-party debug logs
- `log_noisy_loggers`: list of logger names to treat as noisy
- `log_domain_levels`: per-logger explicit levels map (e.g. `"app.controllers.mqtt_controller": "WARNING"`)

## Secret safety

- `local_config/settings.json` is local-only and gitignored.
- `settings-update-example` uses placeholder values for sensitive keys (`password`, `secret`, `token`, `api_key`, `dsn`).
- The check output shows only paths and types, never secret values.
- `settings-prune-local-preview` is a dry run; removal only happens with `settings-prune-local` (apply mode).
