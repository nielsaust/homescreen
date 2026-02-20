# Localization

This app uses a simple key-based i18n system for **system-defined UI text**.
Custom user-added menu item texts are not translated automatically.

## Runtime Sources

- Built-in catalogs (used at runtime):
  - `app/locales/en.json`
  - `app/locales/nl.json`
- Optional local overrides (runtime, gitignored):
  - `local_config/i18n/<locale>.json`

## Active Locale

Set in `local_config/settings.json`:

```json
{
  "ui_locale": "en"
}
```

Supported now: `en`, `nl` (fallback to `en`).

## How To Use In Code

Use `self.main_app.t(...)` in screens/controllers/services that have access to `main_app`.

Simple:

```python
text = self.main_app.t("status_check.title", default="Check Status")
```

With placeholders:

```python
msg = self.main_app.t(
    "feedback.setup_required",
    default="First complete {setup_name} setup",
    setup_name="MQTT",
)
```

## Placeholder Rules

- Placeholders use Python format style: `{name}`
- Pass values as keyword args to `t(...)`
- Missing keys fall back to `default`, then to the key itself
- Missing placeholder values are left as `{placeholder}`

## Scope Policy

Translate:
- System banners, dialogs, warnings
- System screen titles/labels
- System edit controls (where fixed by app)

Do not auto-translate:
- Custom user button text from `menu.json`
- User-provided payload content (e.g. external event text)

## Adding New Translation Keys

1. Add key to `app/locales/en.json`.
2. Add same key to `app/locales/nl.json`.
3. Replace hardcoded string in code with `self.main_app.t(...)`.
4. Keep a useful `default=...` fallback for robustness.
