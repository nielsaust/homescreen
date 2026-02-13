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
  "sentry_traces_sample_rate": 0.0,
  "sentry_send_default_pii": false
}
```

Recommended values:
- `do_sentry_logging`: `true` on test/prod devices, `false` when debugging offline
- `sentry_traces_sample_rate`: start with `0.0` (errors only), later `0.05` if you want performance traces
- `sentry_send_default_pii`: keep `false` unless you explicitly need user identifiers

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
