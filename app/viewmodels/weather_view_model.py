from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WeatherViewModel:
    temperature_text: str
    min_text: str
    max_text: str
    description_text: str
    cached_label_text: str | None


def build_weather_view_model(payload: dict, cached_at_text: str | None = None) -> WeatherViewModel:
    degrees = "\u00b0"
    arrow_up = "\u25b2"
    arrow_down = "\u25bc"

    temperature = round(payload["main"]["temp"])
    temp_min = round(payload["main"]["temp_min"])
    temp_max = round(payload["main"]["temp_max"])
    description = payload["weather"][0]["description"].capitalize()

    cached_label = f"Laatste weer: {cached_at_text}" if cached_at_text else None
    return WeatherViewModel(
        temperature_text=f"{temperature}{degrees}C",
        min_text=f"{arrow_down}{temp_min}{degrees}C",
        max_text=f"{arrow_up}{temp_max}{degrees}C",
        description_text=description,
        cached_label_text=cached_label,
    )
