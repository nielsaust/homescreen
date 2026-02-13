# Testing

## Local (desktop)

Run a fast baseline check:

```bash
make install
make test-local
```

If dependencies are not available yet (or offline), run syntax-only baseline:

```bash
make baseline
```

Run app:

```bash
make run
```

## Raspberry Pi

Run device checks:

```bash
make test-device
```

This runs:
- dependency/config checks
- smoke imports/compile checks
- optional `systemd` status output (if available)
- MQTT broker socket reachability check (from `settings.json`)

## Notes

- `settings.json` is local-only and gitignored.
- Use `settings.json.example` as the template.
- These checks are intentionally quick and side-effect-light to support frequent runs during refactors.

## Simulate Network Outage

Use the built-in network simulation flag:

```bash
make net-down
make net-status
make net-up
```

Behavior:
- While down: startup and MQTT reconnect logic stay in degraded mode with retries/backoff.
- While up: normal internet checks and MQTT reconnect attempts resume.
- Offline icon is now rendered by a global network status widget (not weather-specific).
- Weather shows cached last-known data when API is unreachable and cache exists.

## Music Debug Logging

Enable in `settings.json`:

```json
{
  "music_debug_logging": true
}
```

Then run app and reproduce play/skip behavior.  
Share log lines containing:
- `[music] ...`
- `[music-screen] ...`

With debug enabled, periodic counters are logged, for example:
- `received`
- `coalesced`
- `dropped`
- `applied`
- `art_requests`
- `art_success`
- `art_stale_dropped`
- `art_placeholder`
- `art_errors`
