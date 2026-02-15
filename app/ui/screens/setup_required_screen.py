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
        message = "Run 'make configuration' in your project root to setup the homescreen."

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

    def show(self):
        return True
