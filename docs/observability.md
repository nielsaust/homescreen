# Observability

## Local logging

The app always writes local logs via `logger.py`:
- console output
- date-rotated log files in `logs/`

## Optional Sentry

Sentry is optional and off by default.

Add these settings in `settings.json`:

```json
{
  "do_sentry_logging": true,
  "sentry_dsn": "https://<public_key>@o<org>.ingest.sentry.io/<project_id>",
  "sentry_environment": "development",
  "sentry_breadcrumb_level": "INFO",
  "sentry_event_level": "ERROR",
  "sentry_traces_sample_rate": 0.0,
  "sentry_send_default_pii": false,
  "sentry_ignore_loggers": ["PIL.PngImagePlugin", "urllib3.connectionpool"]
}
```

Recommended values:
- `do_sentry_logging`: `true` on test/prod devices, `false` when debugging offline
- `sentry_breadcrumb_level`: default `INFO`; set to `WARNING` on noisy devices
- `sentry_event_level`: keep `ERROR` (or `CRITICAL` for very strict signal-only mode)
- `sentry_traces_sample_rate`: start with `0.0` (errors only), later `0.05` if you want performance traces
- `sentry_send_default_pii`: keep `false` unless you explicitly need user identifiers
- `sentry_ignore_loggers`: ignore noisy loggers for breadcrumbs/events in Sentry

## What to prepare in Sentry

Create:
1. New project
2. Platform: **Python**
3. Name: e.g. `homescreen-pi`
4. Environment tags you will use: `development`, `staging`, `production`

Collect:
1. DSN (required)
2. Project ID (part of DSN)
3. Optional alert rules (recommended: new issue alert to email/Slack)

## Notes

- Logging events at `ERROR` and above are forwarded to Sentry.
- A redaction filter masks common sensitive fields (`password`, `token`, `secret`, `authorization`, `api_key`, `dsn`) before sending.

## Local Log Verbosity

For local verbosity control, these settings are available:

```json
{
  "log_profile": "default",
  "log_level": "INFO",
  "console_log_level": "INFO",
  "file_log_level": "DEBUG",
  "log_noisy_third_party_debug": false,
  "log_noisy_loggers": ["PIL.PngImagePlugin", "urllib3.connectionpool"],
  "logger_levels": {
    "app.controllers.mqtt_controller": "WARNING",
    "app.ui.screens.music_screen": "INFO"
  }
}
```

- `log_profile`: baseline preset (`default`, `dev`, `pi`, `quiet`).
- `console_log_level`: keep lower noise on Pi terminal/journal.
- `file_log_level`: usually `DEBUG` to preserve diagnostics in log files.
- `log_noisy_third_party_debug`: when `false`, noisy third-party loggers are set to `WARNING`.
- `logger_levels`: per-logger overrides after profile/global levels are applied.

## UI Trace Logging (local diagnosis)

For intermittent Tk rendering issues (blank/gray frames, delayed button/text paint), enable:

```json
{
  "ui_trace_logging": true,
  "ui_trace_followup_ms": 80
}
```

This logs `[ui-trace]` events for:
- screen show requests
- `screen_object.show()` outcome
- frame/widget mapped/size state right after pack
- mapped/size state after delayed follow-up snapshot
- UI intent pump throughput

How this helps with direction:
- `show_ok=true` + `mapped=false` after delay suggests Tk mapping/render delay (event loop/compositor issue).
- `mapped=true` but width/height `0` suggests layout/geometry timing race.
- missing `screen.after_pack` for a screen request suggests logic path interruption before pack.
