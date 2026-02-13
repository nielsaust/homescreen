# Settings Workflow

Use this workflow to keep `settings.json` and `settings.json.example` aligned without leaking secrets.

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

Remove local-only keys from `settings.json`:

```bash
make settings-prune-local
```

## Recommended routine

1. Add/change settings in `settings.json` while developing.
2. Run `make settings-update-example`.
3. Review `settings.json.example` and commit.
4. Run `make settings-check` to confirm both files are aligned.
5. Optionally run `make settings-prune-local-preview` and `make settings-prune-local` to remove stale local-only keys.

## Logging-related settings

Useful runtime keys:
- `log_profile`: logging profile preset (`default`, `dev`, `pi`, `quiet`)
- `log_console_level`: console/journal verbosity
- `log_file_level`: date-based file log verbosity
- `log_noisy_third_party_debug`: enable noisy third-party debug logs
- `log_noisy_loggers`: list of logger names to treat as noisy
- `log_domain_levels`: per-logger explicit levels map (e.g. `"app.controllers.mqtt_controller": "WARNING"`)

Legacy keys (`console_log_level`, `file_log_level`, `logger_levels`, `log_level`) are still accepted for backward compatibility.

## Secret safety

- `settings.json` is gitignored.
- `settings-update-example` uses placeholder values for sensitive keys (`password`, `secret`, `token`, `api_key`, `dsn`).
- The check output shows only paths and types, never secret values.
- `settings-prune-local-preview` is a dry run; removal only happens with `settings-prune-local` (apply mode).
