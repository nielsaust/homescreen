from __future__ import annotations

import datetime
import os
import pathlib
import tkinter as tk
from tkinter import TclError

from PIL import Image, ImageTk


class NetworkStatusWidget:
    """Global network indicator widget, independent from screen implementations."""

    def __init__(self, main_app, root, icon_size):
        self.main_app = main_app
        self.root = root
        project_root = pathlib.Path(__file__).resolve().parents[3]
        image_path = os.fspath(project_root / "images" / "buttons" / "no-wifi-white.png")
        banner_icon_size = (14, 14)
        image = Image.open(image_path).convert("RGBA").resize(banner_icon_size, Image.LANCZOS)
        alpha = image.split()[-1]
        black_icon = Image.new("RGBA", image.size, (0, 0, 0, 255))
        black_icon.putalpha(alpha)
        self.icon = ImageTk.PhotoImage(black_icon)

        self.banner = tk.Frame(self.root, bg="#f4c542", highlightthickness=0)
        self.content = tk.Frame(self.banner, bg="#f4c542")
        self.content.place(relx=0.5, rely=0.5, anchor="center")

        self.icon_label = tk.Label(self.content, image=self.icon, bg="#f4c542")
        self.icon_label.image = self.icon
        self.icon_label.pack(side=tk.LEFT, padx=(0, 6), pady=2)

        self.text_label = tk.Label(
            self.content,
            text="",
            bg="#f4c542",
            fg="black",
            font=("Helvetica", 11, "bold"),
            anchor="w",
        )
        self.text_label.pack(side=tk.LEFT, pady=2)

        self.lost_at_text = None
        self.visible = False
        self.banner_height = 32
        self.banner_pad_x = 14
        self.root.bind("<Configure>", self._on_root_resize, add="+")

    def _on_root_resize(self, _event=None) -> None:
        if not self.visible:
            return
        try:
            if self.banner.winfo_exists() and self.content.winfo_exists():
                self._place_centered_banner()
        except TclError:
            # Widget tree may be in teardown while root resize events still arrive.
            return

    def _place_centered_banner(self) -> None:
        # Keep banner compact around icon+text with horizontal padding.
        self.banner.update_idletasks()
        content_width = max(self.content.winfo_reqwidth(), 1)
        width = content_width + (self.banner_pad_x * 2)
        self.banner.place(relx=0.5, x=0, y=0, anchor="n", width=width, height=self.banner_height)
        self.banner.lift()

    def set_online(self, online: bool) -> None:
        if online:
            self.hide()
        else:
            self.show()

    def show(self) -> None:
        if self.lost_at_text is None:
            self.lost_at_text = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.text_label.configure(
            text=self.main_app.t(
                "network_banner.connection_lost_at",
                default="Connection lost at {timestamp}",
                timestamp=self.lost_at_text,
            )
        )
        if self.visible:
            self._place_centered_banner()
            return
        self._place_centered_banner()
        self.visible = True

    def hide(self) -> None:
        if not self.visible:
            return
        self.banner.place_forget()
        self.lost_at_text = None
        self.visible = False
