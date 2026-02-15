from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import MainApp

import tkinter as tk


class SetupRequiredScreen:
    def __init__(self, main_app: MainApp, frame):
        self.main_app = main_app
        self.frame = frame
        self._build()

    def _build(self):
        settings = self.main_app.settings
        fg = getattr(settings, "alert_default_foreground_color", "#000000")
        bg = getattr(settings, "alert_default_background_color", "#ffffff")
        width = int(settings.screen_width * 0.7)
        max_height = int(settings.screen_height * 0.7)
        pad = 24
        message = self._build_setup_message()

        self.frame.configure(bg="black")

        card = tk.Frame(
            self.frame,
            bg=bg,
            highlightthickness=0,
            width=width,
        )
        card.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        label = tk.Label(
            card,
            text=message,
            bg=bg,
            fg=fg,
            justify=tk.CENTER,
            font=("Helvetica", 24, "bold"),
            wraplength=int(width * 0.85),
        )
        # Measure required text height first, then size card dynamically while keeping center alignment.
        label.pack(padx=pad, pady=pad)
        self.frame.update_idletasks()
        target_height = min(max_height, label.winfo_reqheight() + (pad * 2))
        label.pack_forget()
        card.configure(height=target_height)
        card.pack_propagate(False)
        label.pack(expand=True, fill=tk.BOTH, padx=pad, pady=pad)

    def _build_setup_message(self):
        mqtt_enabled = bool(getattr(self.main_app.settings, "enable_mqtt", False))
        music_enabled = bool(getattr(self.main_app.settings, "enable_music", False))
        weather_enabled = bool(getattr(self.main_app.settings, "enable_weather", False))

        weather_ready = weather_enabled and bool(getattr(self.main_app.settings, "weather_api_key", "")) and bool(
            getattr(self.main_app.settings, "weather_city_id", "")
        )

        mqtt_line = "MQTT: enabled" if mqtt_enabled else "MQTT: disabled"
        music_line = "Music: enabled" if music_enabled else "Music: disabled"
        weather_line = "Weather: configured" if weather_ready else ("Weather: enabled (missing API key/city)" if weather_enabled else "Weather: disabled")

        return (
            "Run 'make configuration' in your project root to setup the homescreen.\n\n"
            f"{mqtt_line}\n{music_line}\n{weather_line}"
        )

    def show(self):
        return True
