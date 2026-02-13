from __future__ import annotations

import os
import pathlib
import tkinter as tk

from PIL import Image, ImageTk


class NetworkStatusWidget:
    """Global network indicator widget, independent from screen implementations."""

    def __init__(self, root, icon_size):
        self.root = root
        image_path = os.fspath(pathlib.Path(__file__).parent / "images/buttons/no-wifi-white.png")
        image = Image.open(image_path)
        image = image.resize(icon_size)
        self.icon = ImageTk.PhotoImage(image)

        self.label = tk.Label(self.root, image=self.icon, bg="black")
        self.label.image = self.icon
        self.label.configure(image=self.icon, width=icon_size[0], height=icon_size[1])
        self.visible = False

    def set_online(self, online: bool) -> None:
        if online:
            self.hide()
        else:
            self.show()

    def show(self) -> None:
        if self.visible:
            return
        self.label.place(relx=0.95, rely=0.95, anchor="se")
        self.visible = True

    def hide(self) -> None:
        if not self.visible:
            return
        self.label.place_forget()
        self.visible = False
