import logging
logger = logging.getLogger(__name__)

from tkinter import font as tkFont
import tkinter as tk


class AlertScreen:
    def __init__(self, main_app):
        self.main_app = main_app
        self.window = None
        self.alert_updater = None
        self.is_showing = False
        self.show_seconds = self.main_app.settings.alert_default_show_seconds
        self.current_seconds_visible = 0

    def tick_alert(self): 
        if not self.is_showing:
            logger.error("can't update alert; not showing")
            return

        if self.current_seconds_visible > self.show_seconds:
            self.destroy()
            return
        
        self.current_seconds_visible += 1
        self.alert_updater = self.window.after(1000, self.tick_alert)
        
    def show(self, data):
        logger.debug(f"show in alert screen: {data}")
        
        # Cancel any running timer
        if self.alert_updater and self.window:
            try:
                self.window.after_cancel(self.alert_updater)
            except Exception:
                pass

        self.current_seconds_visible = 0
        self.title = data.get("title", "")

        if self.title != "":
            # Prioriteit: argument > data > default
            self.show_seconds = data.get("show_seconds", self.main_app.settings.alert_default_show_seconds)
            self.default_foreground_color = data.get(
                "foreground_color",
                self.main_app.settings.alert_default_foreground_color
            )
            self.default_background_color = data.get(
                "background_color",
                self.main_app.settings.alert_default_background_color
            )

            self.is_showing = True
            
            self.window = tk.Toplevel(self.main_app.root, bg=self.default_background_color)
            
            if not self.main_app.system_info["is_desktop"]:
                self.window.attributes('-fullscreen', True)
            else:
                self.window.geometry(f"{self.main_app.settings.screen_width}x{self.main_app.settings.screen_height}")

            # Determine font size based on word length
            words = self.title.split()
            longest_word = max(words, key=len)
            longest_word_size = len(longest_word)
            total_string_length = len(self.title)
            if total_string_length > 20 or longest_word_size > 7:
                title_font_size = max(20, 100 - (longest_word_size * 4))
            else:
                title_font_size = 95

            title_font = tkFont.Font(family="Helvetica", size=title_font_size, weight="bold")

            self.label_title = tk.Label(
                self.window,
                text=self.title.upper(),
                font=title_font,
                bg=self.default_background_color,
                fg=self.default_foreground_color,
                wraplength=650
            )
            self.label_title.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

            # Click to dismiss
            self.window.bind("<Button-1>", self.destroy)
            
            # Start timer immediately
            self.tick_alert()
        else:
            self.destroy()

        return True

    def destroy(self, event=None):
        if not self.is_showing or not self.window:
            return
        self.main_app.display_controller.check_idle()
        if self.alert_updater:
            try:
                self.window.after_cancel(self.alert_updater)
            except Exception:
                pass
        self.is_showing = False
        self.window.destroy()