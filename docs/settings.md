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

## Recommended routine

1. Add/change settings in `settings.json` while developing.
2. Run `make settings-update-example`.
3. Review `settings.json.example` and commit.
4. Run `make settings-check` to confirm both files are aligned.

## Secret safety

- `settings.json` is gitignored.
- `settings-update-example` uses placeholder values for sensitive keys (`password`, `secret`, `token`, `api_key`, `dsn`).
- The check output shows only paths and types, never secret values.
