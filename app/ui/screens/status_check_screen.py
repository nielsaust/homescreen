from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import MainApp

import datetime
import logging
import subprocess
import threading
import tkinter as tk
from tkinter import font as tkFont
from pathlib import Path

import requests

from app.observability.domain_logger import log_event

logger = logging.getLogger(__name__)


class StatusCheckScreen:
    """Overlay-style status check (same lifecycle style as cam/alert)."""

    def __init__(self, main_app: MainApp):
        self.main_app = main_app
        self.window = None
        self.main_frame = None
        self.check_job = None
        self.check_inflight = False
        self.is_showing = False

        self.internet_label = None
        self.openweather_label = None
        self.mqtt_label = None
        self.capability_label = None
        self.checked_at_label = None
        self.version_label = None
        self.last_update_label = None

        self.last_result = {
            "internet": None,
            "openweather": None,
            "mqtt": None,
            "checked_at": None,
        }
        self._version_text, self._last_update_text = self._resolve_build_metadata_text()

    def _git_capture(self, repo_root: Path, args: list[str], timeout_seconds: float = 1.5) -> str:
        try:
            proc = subprocess.run(
                ["git", "-C", str(repo_root)] + args,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
            if proc.returncode != 0:
                return ""
            return proc.stdout.strip()
        except Exception:
            return ""

    def _resolve_build_metadata_text(self) -> tuple[str, str]:
        version = str(getattr(self.main_app.settings, "version", "dev") or "dev")
        repo_root = Path(__file__).resolve().parents[3]

        pull_date_text = ""
        reflog_lines = self._git_capture(
            repo_root,
            ["reflog", "--date=iso", "--format=%gs\t%cd", "-n", "120"],
            timeout_seconds=2.0,
        )
        if reflog_lines:
            for line in reflog_lines.splitlines():
                if "\t" not in line:
                    continue
                msg, date_text = line.split("\t", 1)
                msg_l = msg.lower()
                if "pull" not in msg_l and "clone" not in msg_l:
                    continue
                date_text = date_text.strip()
                if not date_text:
                    continue
                try:
                    pull_dt = datetime.datetime.fromisoformat(date_text.replace("Z", "+00:00"))
                    pull_date_text = pull_dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    pull_date_text = date_text
                break

        update_text = ""
        if pull_date_text:
            update_text = self.main_app.t(
                "status_check.last_update",
                default="Last update: {timestamp} ({source})",
                timestamp=pull_date_text,
                source=self.main_app.t("status_check.last_update_source.pull", default="from local git update"),
            )
        else:
            update_text = self.main_app.t(
                "status_check.last_update_pending",
                default="Last update: unknown",
            )

        build_text = self.main_app.t(
            "status_check.build",
            default="Version: {version}",
            version=version,
        )
        return build_text, update_text

    def _refresh_interval_seconds(self):
        raw = getattr(self.main_app.settings, "network_check_refresh_interval_seconds", 20)
        try:
            return max(5, int(raw))
        except (TypeError, ValueError):
            return 20

    def show(self):
        self.destroy()
        self._version_text, self._last_update_text = self._resolve_build_metadata_text()

        bg = self.main_app.settings.menu_background_color.get("menu") or "black"
        fg = "white"
        title_font = tkFont.Font(family="Helvetica", size=40, weight="bold")
        row_font = tkFont.Font(family="Helvetica", size=28, weight="bold")
        meta_font = tkFont.Font(family="Helvetica", size=18)

        self.window = tk.Toplevel(self.main_app.root, bg=bg)
        if not self.main_app.system_info["is_desktop"]:
            self.window.attributes("-fullscreen", True)
        else:
            self.window.geometry(f"{self.main_app.settings.screen_width}x{self.main_app.settings.screen_height}")

        self.main_frame = tk.Frame(self.window, bg=bg)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        title_label = tk.Label(
            self.main_frame,
            text=self.main_app.t("status_check.title", default="Check Status"),
            font=title_font,
            bg=bg,
            fg=fg,
            pady=24,
        )
        title_label.pack()

        self.internet_label = tk.Label(self.main_frame, text="", font=row_font, bg=bg, fg=fg, anchor="w")
        self.internet_label.pack(fill=tk.X, padx=36, pady=10)

        self.openweather_label = tk.Label(self.main_frame, text="", font=row_font, bg=bg, fg=fg, anchor="w")
        self.openweather_label.pack(fill=tk.X, padx=36, pady=10)

        self.mqtt_label = tk.Label(self.main_frame, text="", font=row_font, bg=bg, fg=fg, anchor="w")
        self.mqtt_label.pack(fill=tk.X, padx=36, pady=10)

        help_label = tk.Label(
            self.main_frame,
            text=self.main_app.t(
                "status_check.help",
                default="Unavailable menu items stay grey until required connectivity is back.",
            ),
            font=meta_font,
            bg=bg,
            fg="#b5b5b5",
            wraplength=int(self.main_app.settings.screen_width * 0.85),
            justify=tk.LEFT,
            anchor="w",
        )
        help_label.pack(fill=tk.X, padx=36, pady=(16, 4))

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

        self.version_label = tk.Label(self.main_frame, text="", font=meta_font, bg=bg, fg="#9f9f9f", anchor="w")
        self.version_label.pack(fill=tk.X, padx=36, pady=(4, 12))
        self.last_update_label = tk.Label(self.main_frame, text="", font=meta_font, bg=bg, fg="#9f9f9f", anchor="w")
        self.last_update_label.pack(fill=tk.X, padx=36, pady=(0, 12))

        # Tap anywhere to close.
        self.window.bind("<ButtonRelease-1>", self.destroy)
        self.is_showing = True
        self.main_app.display_controller.check_idle(True)
        self._render_status()
        self._schedule_checks(immediate=True)
        return True

    def destroy(self, _event=None):
        if not self.is_showing:
            return
        self.is_showing = False
        self.check_inflight = False

        if self.check_job is not None and self.window is not None:
            try:
                self.window.after_cancel(self.check_job)
            except Exception:
                pass
            self.check_job = None

        if self.window is not None:
            try:
                self.window.destroy()
            except Exception:
                pass
            self.window = None
        self.main_frame = None

        self.main_app.display_controller.check_idle()
        self.main_app.root.focus_set()

        touch = getattr(self.main_app, "touch_controller", None)
        if touch is not None:
            touch.click_time = None
            touch.start_x = 0
            touch.start_y = 0
            touch.ignore_next_click = False
            touch.ignore_click_until = 0.0

    def _schedule_checks(self, immediate=False):
        if not self.is_showing or self.window is None:
            self.check_job = None
            return
        if self.check_job is not None:
            try:
                self.window.after_cancel(self.check_job)
            except Exception:
                pass
            self.check_job = None
        delay_ms = 1 if immediate else self._refresh_interval_seconds() * 1000
        self.check_job = self.window.after(delay_ms, self._tick)

    def _tick(self):
        if not self.is_showing or self.window is None:
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
        if not self.is_showing or self.window is None:
            return
        self.last_result = result
        self._render_status()
        self.main_app.publish_event(
            "menu.refresh.requested",
            {"reason": "status_check.updated"},
            source="status_check",
        )

    def _status_text(self, label, value, enabled=True):
        if not enabled:
            return self.main_app.t("status_check.row.disabled", default="{label}: disabled", label=label), "#8f8f8f"
        if value is None:
            return self.main_app.t("status_check.row.checking", default="{label}: checking...", label=label), "#d8d8d8"
        if value:
            return self.main_app.t("status_check.row.ok", default="{label}: OK", label=label), "#35c759"
        return self.main_app.t("status_check.row.unavailable", default="{label}: unavailable", label=label), "#ff6b6b"

    def _render_status(self):
        if not self.is_showing:
            return
        if any(widget is None for widget in (self.internet_label, self.openweather_label, self.mqtt_label, self.capability_label, self.checked_at_label, self.version_label, self.last_update_label)):
            return

        internet_text, internet_color = self._status_text(
            self.main_app.t("status_check.label.internet", default="Internet"),
            self.last_result.get("internet"),
            enabled=True,
        )
        owm_text, owm_color = self._status_text(
            self.main_app.t("status_check.label.openweather", default="OpenWeather"),
            self.last_result.get("openweather"),
            enabled=bool(getattr(self.main_app.settings, "enable_weather", False)),
        )
        mqtt_text, mqtt_color = self._status_text(
            self.main_app.t("status_check.label.mqtt", default="MQTT"),
            self.last_result.get("mqtt"),
            enabled=bool(getattr(self.main_app.settings, "enable_mqtt", False)),
        )
        self.internet_label.configure(text=internet_text, fg=internet_color)
        self.openweather_label.configure(text=owm_text, fg=owm_color)
        self.mqtt_label.configure(text=mqtt_text, fg=mqtt_color)

        available = [self.main_app.t("status_check.available.base_ui", default="Base UI")]
        if bool(getattr(self.main_app.settings, "enable_weather", False)) and bool(self.last_result.get("openweather")):
            available.append(self.main_app.t("status_check.available.weather", default="Weather updates"))
        if bool(getattr(self.main_app.settings, "enable_mqtt", False)) and bool(self.last_result.get("mqtt")):
            available.append(self.main_app.t("status_check.available.mqtt", default="MQTT actions/state"))
        self.capability_label.configure(
            text=self.main_app.t(
                "status_check.available.now",
                default="Available now: {items}",
                items=", ".join(available),
            )
        )

        checked_at = self.last_result.get("checked_at")
        if checked_at is None:
            self.checked_at_label.configure(
                text=self.main_app.t("status_check.last_check_pending", default="Last check: pending")
            )
        else:
            self.checked_at_label.configure(
                text=self.main_app.t(
                    "status_check.last_check",
                    default="Last check: {timestamp}",
                    timestamp=checked_at.strftime("%Y-%m-%d %H:%M:%S"),
                )
            )
        self.version_label.configure(text=self._version_text)
        self.last_update_label.configure(text=self._last_update_text)
        log_event(
            logger,
            logging.DEBUG,
            "network",
            "health.render",
            internet=self.last_result.get("internet"),
            openweather=self.last_result.get("openweather"),
            mqtt=self.last_result.get("mqtt"),
        )
