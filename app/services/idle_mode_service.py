from __future__ import annotations


VALID_IDLE_MODES = {"time", "weather", "off"}


def resolve_idle_mode(settings, weather_enabled: bool = False) -> str:
    raw = getattr(settings, "show_on_idle", None)
    mode = str(raw or "").strip().lower()

    if mode not in VALID_IDLE_MODES:
        mode = "time"

    if mode == "weather" and not weather_enabled:
        return "time"
    return mode


def is_idle_display_on(settings, weather_enabled: bool = False) -> bool:
    return resolve_idle_mode(settings, weather_enabled=weather_enabled) != "off"
