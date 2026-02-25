from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import MainApp

import datetime
import logging
import threading
import tkinter as tk
from io import BytesIO
from tkinter import font as tkFont

from PIL import Image, ImageTk

from app.observability.domain_logger import log_event
from app.services.weather_service import WeatherService
from app.ui.screens.weather_time_shared import WeatherTimeSharedLogic
from app.viewmodels.weather_view_model import build_weather_view_model

logger = logging.getLogger(__name__)


class TimeScreen:
    def __init__(self, main_app: MainApp, frame, language: str = "en"):
        self.main_app = main_app
        self.frame = frame
        self.lang = language
        self.time_update_job = None
        self.weather_update_job = None
        self.weather_fetch_inflight = False
        self.weather_icon_image = None
        self.shared = WeatherTimeSharedLogic(self.main_app)
        self._meridiem_pack_pady = self._compute_meridiem_pack_pady()
        self._weather_icon_pack_pady = self._compute_weather_icon_pack_pady()

        background_color = self.main_app.settings.menu_background_color.get("weather") or "black"
        foreground_color = "white"

        width = int(self.main_app.settings.screen_width)
        height = int(self.main_app.settings.screen_height)

        time_font = tkFont.Font(family="Helvetica", size=160, weight="bold")
        ampm_font = tkFont.Font(family="Helvetica", size=24, weight="bold")
        date_font = tkFont.Font(family="Helvetica", size=56, weight="bold")
        weather_font = tkFont.Font(family="Helvetica", size=44, weight="bold")
        weather_desc_font = tkFont.Font(family="Helvetica", size=34)
        weather_divider_font = tkFont.Font(family="Helvetica", size=30, weight="bold")

        self.main_frame = tk.Frame(self.frame, background=background_color, width=width, height=height)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        self.main_frame.pack_propagate(False)

        self.center_frame = tk.Frame(self.main_frame, background=background_color)
        self.center_frame.place(relx=0.5, rely=0.45, anchor=tk.CENTER)

        self.time_line_frame = tk.Frame(self.center_frame, background=background_color)
        self.time_line_frame.pack(anchor=tk.CENTER)

        self.label_time = tk.Label(
            self.time_line_frame,
            text="00:00",
            font=time_font,
            bg=background_color,
            fg=foreground_color,
        )
        self.label_meridiem = tk.Label(
            self.time_line_frame,
            text="",
            font=ampm_font,
            bg=background_color,
            fg=foreground_color,
            anchor="s",
        )
        self.label_date = tk.Label(
            self.center_frame,
            text="",
            font=date_font,
            bg=background_color,
            fg=foreground_color,
        )
        self.label_time.pack(side=tk.LEFT, anchor=tk.S)
        self.label_meridiem.pack(side=tk.LEFT, anchor=tk.S, padx=(8, 0), pady=self._meridiem_pack_pady)
        self.label_date.pack(anchor=tk.CENTER, pady=(12, 0))

        self.weather_frame = tk.Frame(self.main_frame, background=background_color)
        self.weather_frame.place(relx=0.5, rely=1.0, y=-24, anchor=tk.S)
        self.weather_line_frame = tk.Frame(self.weather_frame, background=background_color)
        self.weather_line_frame.pack(anchor=tk.CENTER)

        self.label_weather_icon = tk.Label(self.weather_line_frame, text="", bg=background_color, fg=foreground_color)
        self.label_weather = tk.Label(
            self.weather_line_frame,
            text="",
            font=weather_font,
            bg=background_color,
            fg=foreground_color,
        )
        self.label_weather_description = tk.Label(
            self.weather_line_frame,
            text="",
            font=weather_desc_font,
            bg=background_color,
            fg=foreground_color,
        )
        self.label_weather_separator = tk.Label(
            self.weather_line_frame,
            text=" • ",
            font=weather_divider_font,
            bg=background_color,
            fg=foreground_color,
        )
        self.label_weather_icon.pack(side=tk.LEFT, padx=(0, 10), pady=self._weather_icon_pack_pady)
        self.label_weather.pack(side=tk.LEFT)
        self.label_weather_separator.pack(side=tk.LEFT, padx=(8, 8))
        self.label_weather_description.pack(side=tk.LEFT)

        self.weather_service = WeatherService(
            settings=self.main_app.settings,
            is_network_available=lambda timeout=1: self.main_app.is_network_available(timeout=timeout),
            on_network_status=self._on_network_status,
        )

    def show(self):
        self._apply_time_format_layout()
        self._update_time_loop()
        self._render_cached_weather()
        self._update_weather_loop()
        return True

    def _is_weather_render_enabled(self) -> bool:
        return self.shared.is_weather_render_enabled()

    def _on_network_status(self, network_available):
        if not network_available:
            log_event(logger, logging.WARNING, "network", "time_screen.weather.network_unavailable")

    def _update_time_loop(self):
        self.update_time()
        self.time_update_job = self.main_frame.after(10 * 1000, self._update_time_loop)

    def update_time(self):
        self._apply_time_format_layout()
        self._ensure_time_locale()
        now = datetime.datetime.now()
        try:
            time_text, meridiem = self.shared.format_time_parts(now)
            self.label_time.configure(text=time_text)
            if meridiem:
                self.label_meridiem.configure(text=meridiem)
                if not self.label_meridiem.winfo_ismapped():
                    self.label_meridiem.pack(side=tk.LEFT, anchor=tk.S, padx=(8, 0), pady=self._meridiem_pack_pady)
            else:
                if self.label_meridiem.winfo_ismapped():
                    self.label_meridiem.pack_forget()
            self.label_date.configure(text=self.shared.format_date(now))
        except Exception as exc:
            log_event(logger, logging.ERROR, "time", "render.failed", error=exc)

    def _apply_time_format_layout(self):
        if self.shared.is_24h_time_enabled():
            self.label_meridiem.configure(text="")
            if self.label_meridiem.winfo_ismapped():
                self.label_meridiem.pack_forget()
            return
        if not self.label_meridiem.winfo_ismapped():
            self.label_meridiem.pack(side=tk.LEFT, anchor=tk.S, padx=(8, 0), pady=self._meridiem_pack_pady)

    def _is_desktop_runtime(self) -> bool:
        system_info = getattr(self.main_app, "system_info", None)
        if isinstance(system_info, dict):
            return bool(system_info.get("is_desktop", False))
        return False

    def _pi_shift_up_px(self, setting_key: str, default_value: int) -> int:
        if self._is_desktop_runtime():
            return 0
        try:
            return int(getattr(self.main_app.settings, setting_key, default_value) or 0)
        except Exception:
            return int(default_value)

    def _shift_up_to_pady(self, shift_up_px: int, base_bottom: int = 0) -> tuple[int, int]:
        # Positive value means "move up": increase bottom padding.
        # Negative value means "move down": add top padding and reduce bottom when possible.
        if shift_up_px >= 0:
            return (0, max(0, base_bottom + shift_up_px))
        down_px = abs(shift_up_px)
        return (down_px, max(0, base_bottom - down_px))

    def _compute_meridiem_pack_pady(self) -> tuple[int, int]:
        shift_up_px = self._pi_shift_up_px("time_screen_pi_meridiem_shift_up_px", 10)
        return self._shift_up_to_pady(shift_up_px, base_bottom=30)

    def _compute_weather_icon_pack_pady(self) -> tuple[int, int]:
        shift_up_px = self._pi_shift_up_px("time_screen_pi_weather_icon_shift_up_px", 10)
        return self._shift_up_to_pady(shift_up_px, base_bottom=0)

    def _ensure_time_locale(self):
        ok, info = self.shared.ensure_time_locale()
        if ok and info:
            log_event(logger, logging.INFO, "time", "locale.applied", locale=info)
        if not ok:
            log_event(logger, logging.WARNING, "time", "locale.apply_failed", locale=self.shared.time_locale, error=info)

    def _render_cached_weather(self):
        if not self._is_weather_render_enabled():
            self.weather_frame.place_forget()
            return
        snapshot = self.weather_service.load_cached_snapshot()
        if not snapshot or not isinstance(snapshot.get("payload"), dict):
            return
        try:
            vm = build_weather_view_model(
                snapshot.get("payload"),
                snapshot.get("cached_at_text"),
                units=self.shared.weather_units(),
            )
            self._render_weather_line(vm.temperature_text, vm.description_text, snapshot.get("icon_bytes"))
        except Exception as exc:
            log_event(logger, logging.DEBUG, "time", "weather.cache_render_failed", error=exc)

    def _update_weather_loop(self):
        if self.weather_update_job is not None:
            try:
                self.main_frame.after_cancel(self.weather_update_job)
            except Exception:
                pass
        if self._is_weather_render_enabled():
            self._update_weather()
        else:
            self.weather_frame.place_forget()
        interval_ms = int(getattr(self.main_app.settings, "weather_update_interval", 300) or 300) * 1000
        self.weather_update_job = self.main_frame.after(interval_ms, self._update_weather_loop)

    def _update_weather(self):
        if self.weather_fetch_inflight:
            return
        self.weather_fetch_inflight = True
        threading.Thread(target=self._update_weather_worker, daemon=True).start()

    def _update_weather_worker(self):
        try:
            result = self.weather_service.fetch_weather(
                api_key=str(getattr(self.main_app.settings, "weather_api_key", "") or "").strip(),
                city_id=str(getattr(self.main_app.settings, "weather_city_id", "") or "").strip(),
                language=self.lang,
                units=self.shared.weather_units(),
            )
        except Exception as exc:
            log_event(logger, logging.ERROR, "time", "weather.fetch_failed", error=exc)
            result = None
        self.main_app.root.after(0, lambda: self._apply_weather_result(result))

    def _apply_weather_result(self, result):
        self.weather_fetch_inflight = False
        if result is None:
            return
        if result.payload is None:
            self.main_app.publish_event(
                "weather.updated",
                {"source": "none", "cached_at_text": None},
                source="time_screen",
            )
            return
        try:
            vm = build_weather_view_model(
                result.payload,
                result.cached_at_text,
                units=self.shared.weather_units(),
            )
            self.main_app.publish_event(
                "weather.updated",
                {"source": result.source, "cached_at_text": result.cached_at_text},
                source="time_screen",
            )
            self._render_weather_line(vm.temperature_text, vm.description_text, result.icon_bytes)
        except Exception as exc:
            log_event(logger, logging.WARNING, "time", "weather.render_failed", error=exc)

    def _render_weather_line(self, temperature_text: str, description_text: str, icon_bytes=None):
        self.weather_frame.place(relx=0.5, rely=1.0, y=-24, anchor=tk.S)
        self.label_weather.configure(text=temperature_text)
        self.label_weather_description.configure(text=description_text)
        self._apply_weather_icon(icon_bytes)

    def _apply_weather_icon(self, icon_bytes):
        if not icon_bytes:
            self.label_weather_icon.configure(image="", text="")
            self.weather_icon_image = None
            return
        try:
            condition_image = Image.open(BytesIO(icon_bytes)).convert("RGBA")
            condition_image = condition_image.resize((86, 86), Image.LANCZOS)
            self.weather_icon_image = ImageTk.PhotoImage(condition_image)
            self.label_weather_icon.configure(image=self.weather_icon_image, text="")
        except Exception as exc:
            self.label_weather_icon.configure(image="", text="")
            self.weather_icon_image = None
            log_event(logger, logging.DEBUG, "time", "weather.icon_decode_failed", error=exc)
