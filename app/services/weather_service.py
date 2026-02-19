from __future__ import annotations

import datetime
import json
import logging
import pathlib
import time
from dataclasses import dataclass
from typing import Callable

import requests
from urllib3.exceptions import InsecureRequestWarning
import warnings

logger = logging.getLogger(__name__)


@dataclass
class WeatherFetchResult:
    payload: dict | None
    icon_bytes: bytes | None
    source: str  # live | cache | none
    cached_at_text: str | None
    recovery_action: str | None
    network_available: bool


class WeatherService:
    def __init__(
        self,
        settings,
        is_network_available: Callable[[int], bool],
        on_network_status: Callable[[bool], None] | None = None,
    ):
        self.settings = settings
        self.is_network_available = is_network_available
        self.on_network_status = on_network_status
        self.api_failure_count = 0
        self.img_base_url = "https://openweathermap.org/img/wn/"

        self.cache_root = pathlib.Path(__file__).resolve().parents[2] / ".cache"
        self.cache_root.mkdir(parents=True, exist_ok=True)
        self.weather_cache_file = self.cache_root / "weather_last.json"
        self.weather_cache_meta_file = self.cache_root / "weather_last_meta.json"

    def fetch_weather(self, api_key: str, city_id: str, language: str, units: str = "metric") -> WeatherFetchResult:
        if not api_key or not city_id:
            return WeatherFetchResult(None, None, "none", None, None, False)

        payload = self._fetch_live_payload(api_key, city_id, language, units)
        recovery_action = None

        if payload is None:
            self.api_failure_count += 1
            threshold = int(getattr(self.settings, "weather_api_call_reboot_after_retries", 0) or 0)
            if threshold > 0 and self.api_failure_count >= threshold:
                recovery_action = str(getattr(self.settings, "weather_api_failure_action", "none"))
            payload = self._load_cached_weather()
            if payload is None:
                return WeatherFetchResult(None, None, "none", None, recovery_action, False)

            icon_code = self._extract_icon_code(payload)
            icon_bytes = self._load_cached_icon(icon_code) if icon_code else None
            return WeatherFetchResult(
                payload=payload,
                icon_bytes=icon_bytes,
                source="cache",
                cached_at_text=self._format_cached_timestamp(payload),
                recovery_action=recovery_action,
                network_available=False,
            )

        self.api_failure_count = 0
        self._save_cached_weather(payload)
        icon_code = self._extract_icon_code(payload)
        icon_bytes = self._fetch_live_icon(icon_code)
        if icon_bytes is None and icon_code:
            icon_bytes = self._load_cached_icon(icon_code)

        return WeatherFetchResult(
            payload=payload,
            icon_bytes=icon_bytes,
            source="live",
            cached_at_text=None,
            recovery_action=None,
            network_available=True,
        )

    def _fetch_live_payload(self, api_key: str, city_id: str, language: str, units: str) -> dict | None:
        url = (
            "https://api.openweathermap.org/data/2.5/weather"
            f"?id={city_id}&appid={api_key}&units={units}&lang={language}"
        )
        body = self._request_with_retries(url)
        if body is None:
            return None

        try:
            return json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            logger.error("Error parsing weather JSON: %s", exc)
            return None

    def _fetch_live_icon(self, icon_code: str | None) -> bytes | None:
        if not icon_code:
            return None
        icon_url = f"{self.img_base_url}{icon_code}@4x.png"
        body = self._request_with_retries(icon_url)
        if body:
            self._save_icon_cache(icon_code, body)
        return body

    def _request_with_retries(self, url: str) -> bytes | None:
        retries = int(getattr(self.settings, "weather_api_call_direct_retries", 1) or 1)
        verify_ssl = bool(getattr(self.settings, "verify_ssl_on_trusted_sources", True))
        if bool(getattr(self.settings, "enable_network_simulation", True)) and bool(
            getattr(self.settings, "simulate_outage_weather_service", False)
        ):
            logger.warning("Weather request simulated outage enabled; skipping call to %s", url)
            return None

        if not verify_ssl:
            warnings.filterwarnings("ignore", category=InsecureRequestWarning)

        for attempt in range(retries):
            if not self.is_network_available(1):
                self._update_network_availability(False)
                return None
            try:
                response = requests.get(url, timeout=10, verify=verify_ssl)
                if response.status_code == 200:
                    self._update_network_availability(True)
                    return response.content
                logger.error("HTTP error %s for URL: %s", response.status_code, url)
            except requests.Timeout:
                logger.error("Timeout when calling %s (attempt %s/%s)", url, attempt + 1, retries)
            except requests.RequestException as exc:
                logger.error("Request exception for %s (attempt %s/%s): %s", url, attempt + 1, retries, exc)
            self._update_network_availability(False)
        return None

    def _update_network_availability(self, available: bool):
        if self.on_network_status:
            try:
                self.on_network_status(available)
            except Exception:
                pass

    def _save_cached_weather(self, payload: dict):
        try:
            self.weather_cache_file.write_text(json.dumps(payload))
            self.weather_cache_meta_file.write_text(json.dumps({"cached_at": int(time.time())}))
        except Exception as exc:
            logger.warning("Could not save weather cache: %s", exc)

    def _load_cached_weather(self):
        if not self.weather_cache_file.exists():
            return None
        try:
            return json.loads(self.weather_cache_file.read_text())
        except Exception as exc:
            logger.warning("Could not read weather cache: %s", exc)
            return None

    def _icon_cache_path(self, icon_code: str):
        return self.cache_root / f"weather_icon_{icon_code}.png"

    def _save_icon_cache(self, icon_code: str, image_bytes: bytes):
        try:
            self._icon_cache_path(icon_code).write_bytes(image_bytes)
        except Exception as exc:
            logger.warning("Could not save weather icon cache: %s", exc)

    def _load_cached_icon(self, icon_code: str):
        path = self._icon_cache_path(icon_code)
        if not path.exists():
            return None
        try:
            return path.read_bytes()
        except Exception as exc:
            logger.warning("Could not read weather icon cache: %s", exc)
            return None

    def _extract_icon_code(self, payload: dict) -> str | None:
        try:
            return payload["weather"][0]["icon"]
        except Exception:
            return None

    def _format_cached_timestamp(self, payload: dict) -> str:
        try:
            ts = payload.get("dt")
            if ts:
                return datetime.datetime.fromtimestamp(ts).strftime("%d-%m %H:%M")
        except Exception:
            pass
        try:
            if self.weather_cache_meta_file.exists():
                meta = json.loads(self.weather_cache_meta_file.read_text())
                ts = meta.get("cached_at")
                if ts:
                    return datetime.datetime.fromtimestamp(ts).strftime("%d-%m %H:%M")
        except Exception:
            pass
        try:
            return datetime.datetime.fromtimestamp(self.weather_cache_file.stat().st_mtime).strftime("%d-%m %H:%M")
        except Exception:
            return "onbekend"
