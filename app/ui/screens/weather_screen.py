from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import MainApp

import logging
import datetime
import locale
import pathlib
import threading
import tkinter as tk
from tkinter import font as tkFont
from PIL import Image, ImageTk
from io import BytesIO

from app.services.weather_service import WeatherService
from app.viewmodels.weather_view_model import build_weather_view_model
from app.observability.domain_logger import log_event

logger = logging.getLogger(__name__)


class WeatherScreen:
    def __init__(self, main_app: MainApp, frame, api_key="", city_id="", language="en", units="metric"):
        self.main_app = main_app
        self.frame = frame
        self.weather_update_job = None
        self.weather_fetch_inflight = False
        self.cache_icon_fetch_inflight = False

        self.is_showing = False
        self.is_created = False
        if not api_key or not city_id:
            raise ValueError("API key and city ID are required")

        self.idle = False
        self.api_key = api_key
        self.lang = language
        self.city_id = city_id
        self.units = units
        self.date_format = str(getattr(self.main_app.settings, "weather_date_format", "%-d %b") or "%-d %b")
        self.time_locale = str(getattr(self.main_app.settings, "weather_time_locale", "") or "").strip()
        self._locale_initialized = False
        self._locale_ok = False
        self.icon_size_large = 300
        self.last_updated = 0
        self.previous_condition_image_url = ""
        self.weather_now_image = None
        self.cached_weather_icon = None

        self.weather_service = WeatherService(
            settings=self.main_app.settings,
            is_network_available=lambda timeout=1: self.main_app.is_network_available(timeout=timeout),
            on_network_status=self.update_network_availability,
        )

        background_color = self.main_app.settings.menu_background_color.get("weather")
        if background_color is None:
            background_color = "black"
        foreground_color = "white"

        width = self.main_app.settings.screen_width
        height = self.main_app.settings.screen_height

        timedate_font = tkFont.Font(family="Helvetica", size=60, weight="bold")
        temp_font = tkFont.Font(family="Helvetica", size=100, weight="bold")
        description_font = tkFont.Font(family="Helvetica", size=50)
        minmax_font = tkFont.Font(family="Helvetica", size=30)

        self.main_frame = tk.Frame(self.frame, background=background_color, width=width, height=height)
        self.time_frame = tk.Frame(self.main_frame, background=background_color, width=width, height=130)
        self.sub_frame = tk.Frame(self.main_frame, background=background_color, width=width, height=540)
        self.bottom_frame = tk.Frame(self.main_frame, background=background_color, width=width, height=50)
        self.temp_frame = tk.Frame(self.sub_frame, background=background_color, width=width, height=200)

        self.sub_frame.grid_propagate(False)
        self.time_frame.grid_propagate(False)
        self.bottom_frame.grid_propagate(False)
        self.temp_frame.grid_propagate(False)

        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.time_frame.grid(row=0, column=0, sticky="nsew")
        self.sub_frame.grid(row=1, column=0, sticky="nsew")
        self.bottom_frame.grid(row=2, column=0, sticky="nsew")

        self.label_time = tk.Label(self.time_frame, text="00:00", font=timedate_font, bg=background_color, fg=foreground_color, padx=30, pady=30)
        self.label_date = tk.Label(self.time_frame, text="ma 1 jan", font=timedate_font, bg=background_color, fg=foreground_color, padx=30, pady=30)

        self.label_time.place(relx=0, rely=0, x=18, y=10, anchor=tk.NW)
        self.label_date.place(relx=1, rely=0, x=-18, y=10, anchor=tk.NE)

        self.label_temperature = tk.Label(self.temp_frame, text="--\u00b0C", font=temp_font, bg=background_color, fg=foreground_color, padx=20, pady=20)
        self.label_min = tk.Label(self.temp_frame, text="\u25bc --\u00b0C", font=minmax_font, bg=background_color, fg=foreground_color, padx=20, pady=10)
        self.label_max = tk.Label(self.temp_frame, text="\u25b2 --\u00b0C", font=minmax_font, bg=background_color, fg=foreground_color, padx=20, pady=10)

        relx = 0.6
        rely_correction = 0
        if not self.main_app.system_info["is_desktop"]:
            rely_correction = 0.05
        self.label_temperature.place(relx=relx, rely=0.5 + rely_correction, anchor=tk.E)
        self.label_max.place(relx=relx, rely=0.5, anchor=tk.SW)
        self.label_min.place(relx=relx, rely=0.5, anchor=tk.NW)

        self.label_condition = tk.Label(self.sub_frame, text="IMAGE", bg=background_color, fg=foreground_color)
        self.label_description = tk.Label(self.sub_frame, text="mooi weer", font=description_font, bg=background_color, fg=foreground_color)
        self.cached_weather_badge = tk.Frame(
            self.main_frame,
            bg="white",
            padx=8,
            pady=4,
            highlightthickness=1,
            highlightbackground="#d0d0d0",
        )
        self.cached_weather_icon_label = tk.Label(
            self.cached_weather_badge,
            bg="white",
        )
        self.cached_weather_label = tk.Label(
            self.cached_weather_badge,
            text="",
            font=tkFont.Font(family="Helvetica", size=12, weight="bold"),
            bg="white",
            fg="black",
            padx=4,
            pady=0,
        )
        self.cached_weather_icon_label.pack(side=tk.LEFT)
        self.cached_weather_label.pack(side=tk.LEFT)
        self._load_cached_weather_icon()

        self.label_condition.grid(row=0, column=0)
        self.temp_frame.grid(row=1, column=0)
        self.label_description.grid(row=2, column=0)
        self.cached_weather_badge.place_forget()

        self.time_frame.grid_columnconfigure(0, weight=1)
        self.sub_frame.grid_columnconfigure(0, weight=1)
        self.bottom_frame.grid_columnconfigure(0, weight=1)
        self.time_frame.grid_rowconfigure(0, weight=1)
        self.sub_frame.grid_rowconfigure(0, weight=1)
        self.bottom_frame.grid_rowconfigure(0, weight=1)

        self.is_created = True
        self.recurring_job = None
        self.blink_id = None
        self.update_time_inteval = 10 * 1000

    def show(self):
        if hasattr(self.main_app, "is_weather_enabled"):
            weather_enabled = bool(self.main_app.is_weather_enabled())
        else:
            weather_enabled = bool(getattr(self.main_app.settings, "enable_weather", True))
        if not weather_enabled:
            log_event(logger, logging.INFO, "weather", "screen.show_skipped", reason="enable_weather_false")
            return False
        self._render_cached_weather_bootstrap()
        self.update_weather_loop()
        self.update_time_loop()
        return True

    def _render_cached_weather_bootstrap(self):
        snapshot = self.weather_service.load_cached_snapshot()
        if not snapshot:
            return
        payload = snapshot.get("payload")
        if not isinstance(payload, dict):
            return
        try:
            vm = build_weather_view_model(payload, snapshot.get("cached_at_text"))
        except Exception as exc:
            log_event(logger, logging.WARNING, "weather", "cache.bootstrap_render_failed", error=exc)
            return

        self.update_weather_gui(vm, snapshot.get("icon_bytes"))
        self.main_app.publish_event(
            "weather.updated",
            {"source": "cache", "cached_at_text": snapshot.get("cached_at_text")},
            source="weather_screen",
        )
        log_event(
            logger,
            logging.INFO,
            "weather",
            "cache.bootstrap_applied",
            has_icon=bool(snapshot.get("icon_bytes")),
            cached_at=snapshot.get("cached_at_text"),
        )

        icon_code = snapshot.get("icon_code")
        if not snapshot.get("icon_bytes") and icon_code:
            self._warm_cached_icon(icon_code)

    def update_weather_loop(self):
        try:
            if self.weather_update_job is not None:
                self.main_frame.after_cancel(self.weather_update_job)
                log_event(logger, logging.DEBUG, "weather", "update.job_canceled")

            self.update_weather()
            self.weather_update_job = self.main_frame.after(
                self.main_app.settings.weather_update_interval * 1000,
                self.update_weather_loop,
            )
            log_event(
                logger,
                logging.DEBUG,
                "weather",
                "update.job_scheduled",
                interval_seconds=self.main_app.settings.weather_update_interval,
            )
        except Exception as e:
            log_event(logger, logging.ERROR, "weather", "update.loop_failed", error=e)
            self.weather_update_job = None

    def update_time_loop(self):
        self.update_time()
        self.time_update_job = self.main_frame.after(self.update_time_inteval, self.update_time_loop)

    def update_network_availability(self, network_available):
        if not network_available:
            log_event(logger, logging.WARNING, "network", "weather.network_unavailable")
        self.main_app.publish_event(
            "network.status",
            {"online": bool(network_available)},
            source="weather_service",
        )

    def show_cached_weather_label(self, cached_at_text):
        self.cached_weather_label.configure(text=f"{cached_at_text}")
        self.cached_weather_badge.place(x=12, rely=1.0, y=-12, anchor=tk.SW)
        self.cached_weather_badge.lift()

    def hide_cached_weather_label(self):
        self.cached_weather_badge.place_forget()

    def _load_cached_weather_icon(self):
        icon_path = pathlib.Path(__file__).resolve().parents[3] / "images" / "buttons" / "weather.png"
        if not icon_path.exists():
            return
        try:
            icon = Image.open(icon_path).convert("RGBA").resize((18, 18), Image.LANCZOS)
            self.cached_weather_icon = ImageTk.PhotoImage(icon)
            self.cached_weather_icon_label.configure(image=self.cached_weather_icon)
        except Exception as e:
            log_event(logger, logging.DEBUG, "weather", "cached_label.icon_load_failed", error=e)

    def update_weather(self):
        if self.weather_fetch_inflight:
            log_event(logger, logging.DEBUG, "weather", "update.skipped", reason="fetch_inflight")
            return
        self.weather_fetch_inflight = True
        threading.Thread(target=self._update_weather_worker, daemon=True).start()

    def _update_weather_worker(self):
        try:
            result = self.weather_service.fetch_weather(
                api_key=self.api_key,
                city_id=self.city_id,
                language=self.lang,
                units=self.units,
            )
        except Exception as exc:
            log_event(logger, logging.ERROR, "weather", "update.worker_failed", error=exc)
            result = None
        self.main_app.root.after(0, lambda: self._apply_weather_result(result))

    def _apply_weather_result(self, result):
        self.weather_fetch_inflight = False
        if result is None:
            return

        if result.recovery_action:
            threshold = getattr(self.main_app.settings, "weather_api_call_reboot_after_retries", 0)
            log_event(
                logger,
                logging.CRITICAL,
                "weather",
                "update.recovery_action",
                threshold=threshold,
                action=result.recovery_action,
            )
            if result.recovery_action == "reboot":
                self.main_app.touch_controller.reboot(ask=True)
            elif result.recovery_action == "restart_app":
                self.main_app.touch_controller.quit_app()
            else:
                log_event(logger, logging.WARNING, "weather", "update.degraded_mode_continue")

        if result.payload is None:
            self.main_app.publish_event(
                "weather.updated",
                {"source": "none", "cached_at_text": None},
                source="weather_screen",
            )
            log_event(
                logger,
                logging.ERROR,
                "weather",
                "update.no_data_no_cache",
                retry_seconds=self.main_app.settings.weather_update_interval,
            )
            return

        self.last_updated = datetime.datetime.now().timestamp()
        vm = build_weather_view_model(result.payload, result.cached_at_text)
        self.main_app.publish_event(
            "weather.updated",
            {"source": result.source, "cached_at_text": result.cached_at_text},
            source="weather_screen",
        )

        self.update_weather_gui(vm, result.icon_bytes)
        if result.source == "cache" and not result.icon_bytes:
            icon_code = self.weather_service.extract_icon_code(result.payload)
            if icon_code:
                self._warm_cached_icon(icon_code)

    def update_weather_gui(self, vm, icon_bytes=None):
        self._apply_icon_bytes(icon_bytes)
        self.label_temperature.configure(text=vm.temperature_text)
        self.label_max.configure(text=vm.max_text)
        self.label_min.configure(text=vm.min_text)
        self.label_description.configure(text=vm.description_text)

    def _apply_icon_bytes(self, icon_bytes):
        if not icon_bytes:
            return
        try:
            condition_image_bytes = BytesIO(icon_bytes)
            condition_image = Image.open(condition_image_bytes)
            condition_image = condition_image.resize(
                (self.icon_size_large, self.icon_size_large),
                ImageTk.Image.LANCZOS,
            )
            self.weather_now_image = ImageTk.PhotoImage(condition_image)
        except Exception as e:
            log_event(logger, logging.ERROR, "weather", "icon.decode_failed", error=e)
            return

        if self.weather_now_image is not None:
            self.label_condition.configure(image=self.weather_now_image)

    def _warm_cached_icon(self, icon_code):
        if self.cache_icon_fetch_inflight:
            return
        self.cache_icon_fetch_inflight = True
        threading.Thread(target=self._warm_cached_icon_worker, args=(icon_code,), daemon=True).start()

    def _warm_cached_icon_worker(self, icon_code):
        try:
            icon_bytes = self.weather_service.fetch_icon_for_code(icon_code)
        except Exception as exc:
            log_event(logger, logging.DEBUG, "weather", "cache.icon_warm_failed", error=exc, icon_code=icon_code)
            icon_bytes = None
        self.main_app.root.after(0, lambda: self._apply_warmed_icon(icon_bytes, icon_code))

    def _apply_warmed_icon(self, icon_bytes, icon_code):
        self.cache_icon_fetch_inflight = False
        if not icon_bytes:
            return
        self._apply_icon_bytes(icon_bytes)
        log_event(logger, logging.INFO, "weather", "cache.icon_warmed", icon_code=icon_code)

    def update_time(self):
        self._ensure_time_locale()

        current_time = datetime.datetime.now()
        time_string = current_time.strftime("%H:%M")
        date_string = self._format_date(current_time)

        try:
            self.label_time.configure(text=time_string)
            self.label_date.configure(text=date_string)
        except Exception as e:
            log_event(logger, logging.ERROR, "weather", "time.render_failed", error=e)

    def _ensure_time_locale(self):
        if self._locale_initialized:
            return
        self._locale_initialized = True
        if not self.time_locale:
            self._locale_ok = True
            return
        try:
            locale.setlocale(locale.LC_TIME, self.time_locale)
            self._locale_ok = True
            log_event(logger, logging.INFO, "weather", "time.locale_applied", locale=self.time_locale)
        except Exception as exc:
            self._locale_ok = False
            log_event(
                logger,
                logging.WARNING,
                "weather",
                "time.locale_apply_failed",
                locale=self.time_locale,
                error=exc,
            )

    def _format_date(self, dt: datetime.datetime) -> str:
        fmt = self.date_format
        if not fmt:
            fmt = "%-d %b"
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
        try:
            return dt.strftime("%-d %b")
        except Exception:
            return dt.strftime("%d %b")

    def set_idle(self, idle=True):
        if idle:
            self.frame.backlight.set_power(False)
        else:
            self.frame.backlight.set_power(True)

        self.idle = idle
