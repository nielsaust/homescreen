from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import MainApp

import logging
import datetime
import locale
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

        self.is_showing = False
        self.is_created = False
        if not api_key or not city_id:
            raise ValueError("API key and city ID are required")

        self.idle = False
        self.api_key = api_key
        self.lang = language
        self.city_id = city_id
        self.units = units
        self.icon_size_large = 300
        self.last_updated = 0
        self.previous_condition_image_url = ""
        self.weather_now_image = None

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

        self.label_time.place(relx=0, rely=0, anchor=tk.NW)
        self.label_date.place(relx=1, rely=0, anchor=tk.NE)

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
        self.cached_weather_label = tk.Label(
            self.main_frame,
            text="",
            font=tkFont.Font(family="Helvetica", size=18, weight="bold"),
            bg=background_color,
            fg="#b0b0b0",
            padx=20,
            pady=10,
        )

        self.label_condition.grid(row=0, column=0)
        self.temp_frame.grid(row=1, column=0)
        self.label_description.grid(row=2, column=0)
        self.cached_weather_label.place_forget()

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
        self.update_weather_loop()
        self.update_time_loop()
        return True

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
        self.cached_weather_label.configure(text=f"Laatste weer: {cached_at_text}")
        self.cached_weather_label.place(relx=0.0, rely=1.0, anchor=tk.SW)
        self.cached_weather_label.lift()

    def hide_cached_weather_label(self):
        self.cached_weather_label.place_forget()

    def update_weather(self):
        result = self.weather_service.fetch_weather(
            api_key=self.api_key,
            city_id=self.city_id,
            language=self.lang,
            units=self.units,
        )

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

    def update_weather_gui(self, vm, icon_bytes=None):
        try:
            if icon_bytes:
                condition_image_bytes = BytesIO(icon_bytes)
                condition_image = Image.open(condition_image_bytes)
                condition_image = condition_image.resize(
                    (self.icon_size_large, self.icon_size_large),
                    ImageTk.Image.LANCZOS,
                )
                self.weather_now_image = ImageTk.PhotoImage(condition_image)
        except Exception as e:
            log_event(logger, logging.ERROR, "weather", "icon.decode_failed", error=e)
            self.weather_now_image = None

        if self.weather_now_image is not None:
            self.label_condition.configure(image=self.weather_now_image)

        self.label_temperature.configure(text=vm.temperature_text)
        self.label_max.configure(text=vm.max_text)
        self.label_min.configure(text=vm.min_text)
        self.label_description.configure(text=vm.description_text)

    def update_time(self):
        if not self.main_app.system_info["is_desktop"]:
            locale.setlocale(locale.LC_TIME, "nl_NL.UTF8")

        current_time = datetime.datetime.now()
        time_string = current_time.strftime("%H:%M")
        if self.main_app.system_info["system_platform"] == "Windows":
            date_string = current_time.strftime("%a %#d %b")
        else:
            date_string = current_time.strftime("%a %-d %b")

        try:
            self.label_time.configure(text=time_string)
            self.label_date.configure(text=date_string)
        except Exception as e:
            log_event(logger, logging.ERROR, "weather", "time.render_failed", error=e)

    def set_idle(self, idle=True):
        if idle:
            self.frame.backlight.set_power(False)
        else:
            self.frame.backlight.set_power(True)

        self.idle = idle
