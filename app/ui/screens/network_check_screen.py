from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import MainApp

import datetime
import logging
import threading
import tkinter as tk
from tkinter import font as tkFont

import requests

from app.observability.domain_logger import log_event

logger = logging.getLogger(__name__)


class NetworkCheckScreen:
    def __init__(self, main_app: MainApp, frame):
        self.main_app = main_app
        self.frame = frame
        self.check_job = None
        self.check_inflight = False
        self.last_result = {
            "internet": None,
            "openweather": None,
            "mqtt": None,
            "checked_at": None,
        }

        bg = self.main_app.settings.menu_background_color.get("menu") or "black"
        fg = "white"
        title_font = tkFont.Font(family="Helvetica", size=40, weight="bold")
        row_font = tkFont.Font(family="Helvetica", size=28, weight="bold")
        meta_font = tkFont.Font(family="Helvetica", size=18)

        self.main_frame = tk.Frame(self.frame, bg=bg)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.title_label = tk.Label(
            self.main_frame,
            text="Network Check",
            font=title_font,
            bg=bg,
            fg=fg,
            pady=24,
        )
        self.title_label.pack()

        self.internet_label = tk.Label(self.main_frame, text="", font=row_font, bg=bg, fg=fg, anchor="w")
        self.internet_label.pack(fill=tk.X, padx=36, pady=10)

        self.openweather_label = tk.Label(self.main_frame, text="", font=row_font, bg=bg, fg=fg, anchor="w")
        self.openweather_label.pack(fill=tk.X, padx=36, pady=10)

        self.mqtt_label = tk.Label(self.main_frame, text="", font=row_font, bg=bg, fg=fg, anchor="w")
        self.mqtt_label.pack(fill=tk.X, padx=36, pady=10)

        self.help_label = tk.Label(
            self.main_frame,
            text="Unavailable menu items stay grey until required connectivity is back.",
            font=meta_font,
            bg=bg,
            fg="#b5b5b5",
            wraplength=int(self.main_app.settings.screen_width * 0.85),
            justify=tk.LEFT,
            anchor="w",
        )
        self.help_label.pack(fill=tk.X, padx=36, pady=(16, 4))

        self.capability_label = tk.Label(
            self.main_frame,
            text="",
            font=meta_font,
            bg=bg,
            fg="#e8e8e8",
            wraplength=int(self.main_app.settings.screen_width * 0.85),
            justify=tk.LEFT,
            anchor="w",
        )
        self.capability_label.pack(fill=tk.X, padx=36, pady=4)

        self.checked_at_label = tk.Label(self.main_frame, text="", font=meta_font, bg=bg, fg="#b5b5b5", anchor="w")
        self.checked_at_label.pack(fill=tk.X, padx=36, pady=4)

        self._render_status()

    def show(self):
        self._schedule_checks(immediate=True)
        return True

    def _refresh_interval_seconds(self):
        raw = getattr(self.main_app.settings, "network_check_refresh_interval_seconds", 20)
        try:
            return max(5, int(raw))
        except (TypeError, ValueError):
            return 20

    def _schedule_checks(self, immediate=False):
        if self.check_job is not None:
            try:
                self.main_frame.after_cancel(self.check_job)
            except Exception:
                pass
            self.check_job = None
        delay_ms = 1 if immediate else self._refresh_interval_seconds() * 1000
        self.check_job = self.main_frame.after(delay_ms, self._tick)

    def _tick(self):
        if self.main_app.display_controller.get_screen_state() != "network_check":
            self.check_job = None
            return
        self._run_checks_async()
        self._schedule_checks(immediate=False)

    def _run_checks_async(self):
        if self.check_inflight:
            return
        self.check_inflight = True
        threading.Thread(target=self._collect_status_worker, daemon=True).start()

    def _collect_status_worker(self):
        settings = self.main_app.settings
        simulation_enabled = bool(getattr(settings, "enable_network_simulation", True))
        simulate_weather = simulation_enabled and bool(getattr(settings, "simulate_outage_weather_service", False))
        simulate_mqtt = simulation_enabled and bool(getattr(settings, "simulate_outage_mqtt", False))

        weather_enabled = bool(getattr(settings, "enable_weather", False))
        mqtt_enabled = bool(getattr(settings, "enable_mqtt", False))

        internet_ok = bool(self.main_app.is_network_available(timeout=2))
        mqtt_ok = None if not mqtt_enabled else (False if simulate_mqtt else bool(self.main_app.is_mqtt_connected()))
        openweather_ok = None

        if weather_enabled:
            if simulate_weather:
                openweather_ok = False
            elif not internet_ok:
                openweather_ok = False
            else:
                try:
                    response = requests.get("https://api.openweathermap.org", timeout=3)
                    openweather_ok = response.status_code < 500
                except requests.RequestException:
                    openweather_ok = False

        result = {
            "internet": internet_ok,
            "openweather": openweather_ok,
            "mqtt": mqtt_ok,
            "checked_at": datetime.datetime.now(),
        }
        self.main_app.root.after(0, lambda: self._apply_result(result))

    def _apply_result(self, result):
        self.check_inflight = False
        self.last_result = result
        self._render_status()
        self.main_app.publish_event(
            "menu.refresh.requested",
            {"reason": "network_check.updated"},
            source="network_check",
        )

    def _status_text(self, label, value, enabled=True):
        if not enabled:
            return f"{label}: disabled", "#8f8f8f"
        if value is None:
            return f"{label}: checking...", "#d8d8d8"
        if value:
            return f"{label}: OK", "#35c759"
        return f"{label}: unavailable", "#ff6b6b"

    def _render_status(self):
        internet_text, internet_color = self._status_text("Internet", self.last_result.get("internet"), enabled=True)
        owm_text, owm_color = self._status_text(
            "OpenWeather",
            self.last_result.get("openweather"),
            enabled=bool(getattr(self.main_app.settings, "enable_weather", False)),
        )
        mqtt_text, mqtt_color = self._status_text(
            "MQTT",
            self.last_result.get("mqtt"),
            enabled=bool(getattr(self.main_app.settings, "enable_mqtt", False)),
        )
        self.internet_label.configure(text=internet_text, fg=internet_color)
        self.openweather_label.configure(text=owm_text, fg=owm_color)
        self.mqtt_label.configure(text=mqtt_text, fg=mqtt_color)

        available = ["Base UI"]
        if bool(getattr(self.main_app.settings, "enable_weather", False)) and bool(self.last_result.get("openweather")):
            available.append("Weather updates")
        if bool(getattr(self.main_app.settings, "enable_mqtt", False)) and bool(self.last_result.get("mqtt")):
            available.append("MQTT actions/state")
        self.capability_label.configure(text=f"Available now: {', '.join(available)}")

        checked_at = self.last_result.get("checked_at")
        if checked_at is None:
            self.checked_at_label.configure(text="Last check: pending")
        else:
            self.checked_at_label.configure(text=f"Last check: {checked_at.strftime('%Y-%m-%d %H:%M:%S')}")
        log_event(
            logger,
            logging.DEBUG,
            "network",
            "health.render",
            internet=self.last_result.get("internet"),
            openweather=self.last_result.get("openweather"),
            mqtt=self.last_result.get("mqtt"),
        )
