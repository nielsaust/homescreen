from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import MainApp

import sys
import logging
logger = logging.getLogger(__name__)

import tkinter as tk
import os
import pathlib

class TurnedOffScreen:
    def __init__(self, main_app: MainApp, frame):
        self.main_app = main_app
        self.frame = frame

        self.create()

    def create(self):
        self.frame.configure(bg='white')
        image_path= os.fspath(pathlib.Path(__file__).parent / f'images/buttons/screen-off.png')
        off_image = tk.PhotoImage(file=image_path)
        off_icon = tk.Label(self.frame, bg="white", image=off_image, padx=0, pady=0)
        off_icon.image=off_image

        # Use the grid layout manager to center the label
        off_icon.grid(row=0, column=0)

        # Configure grid weights to center the label
        self.frame.grid_rowconfigure(0, weight=1)
        self.frame.grid_columnconfigure(0, weight=1)

    def show(self):
        print(f"Showing off screen")