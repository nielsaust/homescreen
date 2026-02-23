from __future__ import annotations


VALID_IDLE_MODES = {"time", "weather", "off"}


def resolve_idle_mode(settings, weather_enabled: bool = False) -> str:
    raw = getattr(settings, "show_on_idle", None)
    mode = str(raw or "").strip().lower()

    if mode not in VALID_IDLE_MODES:
        legacy_show_weather = _to_bool(getattr(settings, "show_weather_on_idle", None), None)
        if legacy_show_weather is True:
            mode = "weather"
        elif legacy_show_weather is False:
            mode = "off"
        else:
            mode = "time"

    if mode == "weather" and not weather_enabled:
        return "time"
    return mode


def is_idle_display_on(settings, weather_enabled: bool = False) -> bool:
    return resolve_idle_mode(settings, weather_enabled=weather_enabled) != "off"


def _to_bool(value, default=False):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("1", "true", "yes", "on"):
            return True
        if lowered in ("0", "false", "no", "off"):
            return False
    if value is None:
        return default
    return bool(value)
