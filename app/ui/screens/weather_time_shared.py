from __future__ import annotations

import datetime
import locale


class WeatherTimeSharedLogic:
    """Shared settings/time/weather helpers for idle weather/time screens."""

    def __init__(self, main_app):
        self.main_app = main_app
        self.date_format = str(getattr(self.main_app.settings, "date_format", "%-d %b") or "%-d %b")
        self.time_locale = str(getattr(self.main_app.settings, "time_locale", "") or "").strip()
        self._locale_initialized = False

    def ensure_time_locale(self) -> tuple[bool, str]:
        if self._locale_initialized:
            return True, ""
        self._locale_initialized = True
        if not self.time_locale:
            return True, ""
        try:
            locale.setlocale(locale.LC_TIME, self.time_locale)
            return True, self.time_locale
        except Exception as exc:
            return False, str(exc)

    def format_date(self, dt: datetime.datetime) -> str:
        fmt = self.date_format or "%-d %b"
        candidates = [fmt]
        if "%-d" in fmt:
            candidates.append(fmt.replace("%-d", "%#d"))
        if "%#d" in fmt:
            candidates.append(fmt.replace("%#d", "%-d"))
        if "%e" in fmt:
            candidates.append(fmt.replace("%e", "%d"))

        seen = set()
        for candidate in candidates:
            if candidate in seen:
                continue
            seen.add(candidate)
            try:
                return dt.strftime(candidate)
            except Exception:
                continue
        return dt.strftime("%d %b")

    def is_24h_time_enabled(self) -> bool:
        raw = str(getattr(self.main_app.settings, "time_format", "24h") or "24h").strip().lower()
        if raw in {"12h", "12"}:
            return False
        return True

    def format_time(self, dt: datetime.datetime) -> str:
        main, meridiem = self.format_time_parts(dt)
        if not meridiem:
            return main
        return f"{main} {meridiem}"

    def format_time_parts(self, dt: datetime.datetime) -> tuple[str, str]:
        if self.is_24h_time_enabled():
            return dt.strftime("%H:%M"), ""
        try:
            main = dt.strftime("%-I:%M")
        except Exception:
            main = dt.strftime("%I:%M").lstrip("0")
        # Keep meridiem stable and locale-independent.
        meridiem = "AM" if dt.hour < 12 else "PM"
        return main, meridiem

    def weather_units(self) -> str:
        raw = str(getattr(self.main_app.settings, "weather_units", "metric") or "metric").strip().lower()
        if raw in {"imperial", "metric"}:
            return raw
        return "metric"

    def is_weather_render_enabled(self) -> bool:
        if not bool(getattr(self.main_app, "enable_weather", False)):
            return False
        api_key = str(getattr(self.main_app.settings, "weather_api_key", "") or "").strip()
        city_id = str(getattr(self.main_app.settings, "weather_city_id", "") or "").strip()
        if not api_key or api_key == "CHANGE_ME":
            return False
        if not city_id or city_id == "CHANGE_ME":
            return False
        return True
