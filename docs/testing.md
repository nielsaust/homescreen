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
