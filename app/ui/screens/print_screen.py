import pathlib
import sys
import logging
logger = logging.getLogger(__name__)

from requests.auth import HTTPDigestAuth
from PIL import Image, ImageTk
from io import BytesIO
import requests
import tkinter as tk
from tkinter import font as tkFont

'''
todo: 
- fix issues with show print or delete option
- estimated time left
- 

2023-12-17 14:11:16,578 - INFO - Checking print status (99%)
2023-12-17 14:11:16,582 - INFO - Show cam with data: {'location': 'local', 'path': 'pencilHolderMidQ_0.2mm_PLA_MK3S_1h52m.gcode', 'progress': 99, '_timestamp': 1702818676}, url=http://octopi.local/webcam/?action=snapshot
2023-12-17 14:11:22,101 - INFO - On MQTT message: (1702818682.1016395) - music
2023-12-17 14:11:22,143 - ERROR - Error retrieving album art from Home Assistant API (Attempt 1/3): Cannot connect to host doornena.duckdns.orgnone:443 ssl:default [Name or service not known]
2023-12-17 14:11:22,180 - ERROR - Error retrieving album art from Home Assistant API (Attempt 2/3): Cannot connect to host doornena.duckdns.orgnone:443 ssl:default [Name or service not known]
2023-12-17 14:11:22,202 - ERROR - Error retrieving album art from Home Assistant API (Attempt 3/3): Cannot connect to host doornena.duckdns.orgnone:443 ssl:default [Name or service not known]

Komt daarna nog eens omhoog:
2023-12-17 14:11:22,472 - INFO - time since boot: 76756.65379047394

>> kijken waar dit vandaan komt?
2023-12-17 14:11:22,473 - WARNING - Unknown or untimely topic received: music
2023-12-17 14:11:23,366 - INFO - On MQTT message: (1702818683.365946) - music
2023-12-17 14:11:23,407 - INFO - time since boot: 76757.9180958271
2023-12-17 14:11:23,408 - WARNING - Unknown or untimely topic received: music
2023-12-17 14:13:33,679 - INFO - On MQTT message: (1702818813.6793475) - octoPrint/progress/printing
2023-12-17 14:13:33,680 - INFO - time since boot: 76888.2314991951
2023-12-17 14:13:33,681 - INFO - Checking print status (100%)
2023-12-17 14:13:33,682 - INFO - Show cam with data: {'location': 'local', 'path': 'pencilHolderMidQ_0.2mm_PLA_MK3S_1h52m.gcode', 'progress': 100, '_timestamp': 1702818813}, url=http://octopi.local/webcam/?action=snapshot
2023-12-17 14:13:34,305 - INFO - On MQTT message: (1702818814.3049552) - octoPrint/progress/printing
2023-12-17 14:13:34,306 - INFO - time since boot: 76888.8571062088
2023-12-17 14:13:34,307 - INFO - Checking print status (100%)
2023-12-17 14:13:34,354 - INFO - Show cam with data: {'location': 'local', 'path': 'pencilHolderMidQ_0.2mm_PLA_MK3S_1h52m.gcode', 'progress': 100, '_timestamp': 1702818813}, url=http://octopi.local/webcam/?action=snapshot

> hiernaar luisteren ipv percent

2023-12-17 14:13:36,437 - INFO - On MQTT message: (1702818816.4376583) - octoPrint/event/PrintDone
2023-12-17 14:13:36,438 - INFO - time since boot: 76890.9898121357
2023-12-17 14:15:11,234 - INFO - On MQTT message: (1702818911.2341585) - octoPrint/progress/printing
2023-12-17 14:15:11,235 - INFO - time since boot: 76985.78630948067
2023-12-17 14:15:11,236 - INFO - Checking print status (0%)
'''

class PrintScreen:
    def __init__(self, main_app):
        self.main_app = main_app
        self.url = None
        self.print_window = None
        self.is_showing = False
        self.percent_label = None
        self.current_progress = 0

        self.is_blinking = False
        self.blink_id = None
        self.blink_time = 500
        self.background_color = "#000000"
        self.percentage_color = "#3a86ff"

    def update(self, progress):
        if self.current_progress!=0 and progress==0:
            self.current_progress = progress
            logger.debug("destroyed print screen")
            self.destroy() # destroy when reset to 0%
            return
        
        if self.percent_label and self.is_showing:
            self.percent_label.configure(text=f"{progress}%")
            self.current_progress = progress

    def show(self, progress):                
        logger.debug(f"Show cam with percentage: {progress}")
        self.is_showing = True
        self.print_window = tk.Toplevel(self.main_app.root, bg=self.background_color)
        if(not self.main_app.system_info["is_desktop"]):
            self.print_window.attributes('-fullscreen', True)  # Make it fullscreen
        else:
            self.print_window.geometry(f"{self.main_app.settings.screen_width}x{self.main_app.settings.screen_height}")

        # Create a frame to hold the labels
        frame = tk.Frame(self.print_window, bg="#000000")

        title_font = tk.font.Font(family="Helvetica", size=100, weight="bold")
        title_label = tk.Label(frame, bg="black", fg="#ffffff", font=title_font, text=f"PRINT")
        title_label.pack()

        subtitle_font = tk.font.Font(family="Helvetica", size=52, weight="bold")
        subtitle_label = tk.Label(frame, bg="black", fg="#ffffff", font=subtitle_font, text=f"PROGRESS")
        subtitle_label.pack()

        progress_font = tk.font.Font(family="Helvetica", size=150, weight="bold")
        self.percent_label = tk.Label(frame, font=progress_font, bg="black", fg="#3a86ff")
        self.percent_label.pack(pady=10)

        self.update(progress)

        frame.place(relx=0.5, rely=0.5, anchor="center")

        if self.is_blinking:
            self.blink_percentage()

        self.main_app.print_memory_usage()

        # Bind function to destroy the QR code overlay
        fullscreen_cam_bind = self.print_window.bind("<ButtonRelease-1>", self.destroy)

    def blink_percentage(self):
        self.is_blinking = True
        if not self.is_showing or not self.percent_label:
            return
        
        if self.percent_label.cget("foreground") == self.percentage_color:
            self.percent_label.config(foreground=self.background_color)
        else:
            self.percent_label.config(foreground=self.percentage_color)
            
        self.blink_id = self.print_window.after(self.blink_time, self.blink_percentage)
        return self.blink_id

    def cancel_blink(self):
        if self.blink_id:
            self.print_window.after_cancel(self.blink_id)
        
        self.is_blinking = False

        if self.percent_label and self.is_showing:
            self.percent_label.config(foreground=self.percentage_color)

    
    def destroy(self, event=None):
        if(self.is_showing):
            self.is_showing = False
            self.cancel_blink()
            self.percent_label = None
            self.main_app.display_controller.check_idle()
            self.print_window.destroy()