import logging
logger = logging.getLogger(__name__)

import time
from tkinter import font as tkFont
import tkinter as tk
import datetime
import locale

class CalendarScreen:
    def __init__(self, main_app):
        self.main_app = main_app
        self.window = None
        self.calendar_updater = None
        self.is_showing = False
        self.colors = self.main_app.settings.calendar_party_colors
        self.default_color = self.main_app.settings.calendar_default_color

    def update_time(self):
        """
        sudo sed -i "s/# nl_NL.UTF-8/nl_NL.UTF-8/g" /etc/locale.gen
        sudo locale-gen
        """
        if(not self.main_app.system_info["is_desktop"]):
            language = str(getattr(self.main_app.settings, "language", "en") or "en").lower()
            desired = "nl_NL.UTF8" if language.startswith("nl") else "en_US.UTF8"
            try:
                locale.setlocale(locale.LC_TIME, desired)
            except Exception:
                pass

        current_time = datetime.datetime.now()
        time_string = current_time.strftime("%H:%M")
        date_string = current_time.strftime("%a %-d %b")

        # Load labels with new values
        try:
            self.label_time.configure(text=time_string)
            self.label_date.configure(text=date_string)
        except Exception as e:
            logger.error(f"[homecalendar] Could not update datetime GUI elements: {e}")
            
        self.main_app.root.update()

    # Define a function to change the text color
    def update_calendar(self): 
        if not self.is_showing:
            logger.error("can't update calendar; not showing")
            return
        
        # Update time     
        self.update_time()

        # Update bottom label
        today = datetime.date.today()
        event_is_tomorrow = self.event_start_date.date() == today + datetime.timedelta(days=1)
        event_is_this_week = self.event_start_date.date() < (today + datetime.timedelta(days=7))
        current_time = time.time()

        timeleft = self.event_start_date.timestamp() - current_time

        if current_time > self.event_end_date.timestamp():
            self.destroy(None)
            return

        if self.all_day:
            # all-day event
            if event_is_tomorrow:
                self.label_bottom.configure(
                    text=self.main_app.t("calendar.tomorrow", default="tomorrow")
                )
            else:
                self.label_bottom.configure(text=self.description)
        else:
            # timed event                    
            if self.event_start_date.date() == today:
                self.event_start_date_string = self.main_app.t(
                    "calendar.starts_at",
                    default="starts at {time}",
                    time=self.event_start_date.strftime("%H:%M"),
                )
            elif event_is_tomorrow:
                self.event_start_date_string = self.main_app.t(
                    "calendar.tomorrow_at",
                    default="tomorrow at {time}",
                    time=self.event_start_date.strftime("%H:%M"),
                )
            elif event_is_this_week:
                self.event_start_date_string = self.main_app.t(
                    "calendar.weekday_at",
                    default="{weekday} at {time}",
                    weekday=self.event_start_date.strftime("%A"),
                    time=self.event_start_date.strftime("%H:%M"),
                )
            else:
                self.event_start_date_string = self.main_app.t(
                    "calendar.date_at",
                    default="{weekday} {date} at {time}",
                    weekday=self.event_start_date.strftime("%A"),
                    date=self.event_start_date.strftime("%#d %b"),
                    time=self.event_start_date.strftime("%H:%M"),
                )
            
            self.event_end_date_string = self.main_app.t(
                "calendar.ends_at",
                default="ends at {time}",
                time=self.event_end_date.strftime("%H:%M"),
            )

            if current_time < self.event_start_date.timestamp():
                time_string = self.event_start_date_string
            else:
                time_string = self.event_end_date_string
            
            # Remove leading zeros from the day of the month or time
            time_string = time_string.replace(" 0", " ")
            
            if len(self.description)>0:
                if(self.label_bottom.cget("text")==self.description or len(self.description)==0):
                    self.label_bottom.configure(text=time_string)
                else:
                    self.label_bottom.configure(text=self.description)
            else:
                self.label_bottom.configure(text=time_string)

        # Update colors when festive
        searchstrings = ['jarig', 'verjaardag', 'vakantie', 'feest', 'jubileum', 'fuif']
        if self.search_for_substrings(self.title, searchstrings):
            global current_color
            self.current_color = (self.current_color + 1) % len(self.colors)
            self.label_title.configure(fg=self.colors[self.current_color])
        else:
            self.label_title.configure(fg=self.default_color)
        
        self.calendar_updater = self.window.after(1000, self.update_calendar)
        
    def show(self, data):
        if self.calendar_updater:
            self.window.after_cancel(self.calendar_updater)
        self.title = data["title"]
        if(self.title!=""):
            self.manual = data["manual"]
            self.start_time = data["start_time"]
            self.end_time = data["end_time"]
            self.description = data["description"]
            self.all_day = data["all_day"]

            if self.manual:
                self.event_start_date = datetime.datetime.strptime(self.start_time, "%Y-%m-%d %H:%M:%S")
                self.event_end_date = datetime.datetime.strptime(self.end_time, "%Y-%m-%d %H:%M:%S")
            else:
                self.event_start_date = datetime.datetime.fromisoformat(self.start_time)
                self.event_end_date = datetime.datetime.fromisoformat(self.end_time)

            self.is_showing = True
            
            self.window = tk.Toplevel(self.main_app.root, bg="black")
            
            if(not self.main_app.system_info["is_desktop"]):
                self.window.attributes('-fullscreen', True)  # Make it fullscreen
            else:
                self.window.geometry(f"{self.main_app.settings.screen_width}x{self.main_app.settings.screen_height}")

            words = self.title.split()            
            longest_word = max(words, key=len)
            longest_word_size = len(longest_word)
            total_string_length = len(self.title)
            if(total_string_length>20 or longest_word_size>7):
                title_font_size = 100 - (longest_word_size*4)
            else:
                title_font_size = 95

            background_color = 'black'
            foreground_color = 'white'
            timedate_font = tkFont.Font(family="Helvetica", size=60, weight="bold")
            title_font = tkFont.Font(family="Helvetica", size=title_font_size, weight="bold")
            self.label_time = tk.Label(self.window,text='00:00', font=timedate_font, bg=background_color, fg=foreground_color, padx=30, pady=30)
            self.label_date = tk.Label(self.window,text='ma 1 jan', font=timedate_font, bg=background_color, fg=foreground_color, padx=30, pady=30)
            
            self.label_time.place(relx=0, rely=0, anchor=tk.NW)
            self.label_date.place(relx=1, rely=0, anchor=tk.NE)

            self.label_title = tk.Label(self.window, text=self.title.upper(), font=title_font, bg=background_color, fg=foreground_color, wraplength=650)
            self.label_title.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

            self.label_bottom = tk.Label(self.window,text=self.description, font=("Helvetica", 40), bg=background_color, fg=foreground_color, padx=30, pady=30, wraplength=650)
            self.label_bottom.place(relx=0.5, rely=1, anchor=tk.S)     


            # Set the initial color of the text
            self.label_title.configure(fg=self.colors[0])
            # Set the current color index to 0
            self.current_color = 0

            # Bind the function to the left mouse button click event
            self.press_screen = self.window.bind("<Button-1>", self.destroy)            
            
            # first update immediatelly
            self.update_calendar()
        else:
            self.destroy(None)

        return True

    def search_for_substrings(self, s, substrings):
        for substring in substrings:
            if substring in s:
                return True
        return False

    # Define a function to exit the program when the screen is clicked
    def destroy(self, event=None):
        if not self.is_showing or not self.window:
            return
        if(self.is_showing):
            self.main_app.display_controller.check_idle()
            if self.calendar_updater:
                self.window.after_cancel(self.calendar_updater)
            self.is_showing = False
            self.window.destroy()
