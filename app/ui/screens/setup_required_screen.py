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
        height = int(settings.screen_height * 0.7)

        self.frame.configure(bg="black")

        card = tk.Frame(
            self.frame,
            bg=bg,
            highlightthickness=0,
            width=width,
            height=height,
        )
        card.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        card.pack_propagate(False)

        label = tk.Label(
            card,
            text="Run 'make configuration' in your project root\nto setup the homescreen.",
            bg=bg,
            fg=fg,
            justify=tk.CENTER,
            font=("Helvetica", 24, "bold"),
            wraplength=int(width * 0.85),
        )
        label.pack(expand=True, fill=tk.BOTH, padx=24, pady=24)

    def show(self):
        return True
