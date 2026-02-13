import logging

from settings import Settings
logger = logging.getLogger(__name__)

import time
from tkinter import font as tkFont
import tkinter as tk
import paho.mqtt.client as mqtt
import os
import json
import datetime
import locale

class HomeCalendar:
    def __init__(self):
        self.is_showing = False
        self.is_created = False

        # load settings
        self.settings = Settings("settings.json")
        self.image_width = self.settings.screen_width
        self.image_height = self.settings.screen_height      
                
        self.colors = ['#ffbe0b', '#fb5607', '#ff006e', '#8338ec', '#3a86ff']
        self.default_color = ['#3a86ff']
        self.init_mqtt()

    def init_mqtt(self):
        # Create an MQTT client
        client = mqtt.Client()
        # Set the update frequency to 1 second (1000 milliseconds)
        client.loop(timeout=60)

        # Set the on_connect and on_message callback functions
        client.on_connect = self.on_connect
        client.on_message = self.on_message
        
        # Set up the MQTT client and connect to the broker
        client.username_pw_set(self.settings.mqtt_user, self.settings.mqtt_password)
        client.connect(self.settings.mqtt_broker)  

        # Start the MQTT client loop
        client.loop_forever()  
         

    def on_connect(self, client, userdata, flags, rc):
        # Subscribe to the doorbell topic
        client.subscribe("calendar")

    def on_message(self, client, userdata, msg):
        # Get the message payload
        data = json.loads(msg.payload)
        self.show_calendar(data['manual'],data['title'],data['start_time'],data['end_time'],data['description'],data['all_day'])
   
    def update_time(self):
        """
        sudo sed -i "s/# nl_NL.UTF-8/nl_NL.UTF-8/g" /etc/locale.gen
        sudo locale-gen
        """
        locale.setlocale(locale.LC_TIME, "nl_NL.UTF8") # dutch
        current_time = datetime.datetime.now()
        time_string = current_time.strftime("%H:%M")

        if os.name!='nt':
            date_string = current_time.strftime("%a %-d %b")
        else:
            date_string = current_time.strftime("%a %#d %b")

        # Load labels with new values
        try:
            self.label_time.configure(text=time_string)
            self.label_date.configure(text=date_string)
        except Exception as e:
            logger.error(f"Could not update datetime GUI elements: {e}")
            
        self.root.update()

    # Define a function to change the text color
    def update_calendar(self):   
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
                self.label_bottom.configure(text="morgen")
            else:
                self.label_bottom.configure(text=self.description)
        else:
            # timed event                    
            if self.event_start_date.date() == today:
                self.event_start_date_string = self.event_start_date.strftime("start om %H:%M uur")
            elif event_is_tomorrow:
                self.event_start_date_string = self.event_start_date.strftime("morgen om %H:%M uur")
            elif event_is_this_week:
                self.event_start_date_string = self.event_start_date.strftime("%A om %H:%M uur")
            else:
                self.event_start_date_string = self.event_start_date.strftime("%A %#d %b om %H:%M uur")
            
            self.event_end_date_string = self.event_end_date.strftime("eindigt om %H:%M uur")

            if current_time < self.event_start_date.timestamp():
                time_string = self.event_start_date_string
            else:
                time_string = self.event_end_date_string
            
            if len(self.description)>0:
                if(self.label_bottom.cget("text")==self.description or len(self.description)==0):
                    self.label_bottom.configure(text=time_string)
                else:
                    self.label_bottom.configure(text=self.description)
            else:
                self.label_bottom.configure(text=time_string)

        # Update colors when festive
        searchstrings = ['jarig', 'verjaardag', 'vakantie', 'feest', 'jubileum']
        if self.search_for_substrings(self.title, searchstrings):
            global current_color
            self.current_color = (self.current_color + 1) % len(self.colors)
            self.label_title.configure(fg=self.colors[self.current_color])
        else:
            self.label_title.configure(fg=self.default_color)
        
        self.root.after(1000, self.update_calendar)
        
    def show_calendar(self, manual=False, title="", start_time="", end_time="", description="", all_day=False):
        if(title!=""):
            self.manual = manual
            self.title = title
            self.start_time = start_time
            self.end_time = end_time
            self.description = description
            self.all_day = all_day

            if self.manual:
                self.event_start_date = datetime.datetime.strptime(self.start_time, "%Y-%m-%d %H:%M:%S")
                self.event_end_date = datetime.datetime.strptime(self.end_time, "%Y-%m-%d %H:%M:%S")
            else:
                self.event_start_date = datetime.datetime.fromisoformat(self.start_time)
                self.event_end_date = datetime.datetime.fromisoformat(self.end_time)

            self.is_showing = True
            self.root = tk.Tk()
            self.root.geometry(f"{self.image_width}x{self.image_height}")
            self.root.configure(bg='black')
            
            if os.name!='nt':
                self.root.attributes("-fullscreen", True)

            words = title.split()            
            longest_word = max(words, key=len)
            longest_word_size = len(longest_word)
            total_string_length = len(title)
            if(total_string_length>20 or longest_word_size>7):
                title_font_size = 100 - (longest_word_size*4)
            else:
                title_font_size = 95

            background_color = 'black'
            foreground_color = 'white'
            timedate_font = tkFont.Font(family="Helvetica", size=60, weight="bold")
            title_font = tkFont.Font(family="Helvetica", size=title_font_size, weight="bold")
            self.label_time = tk.Label(self.root,text='00:00', font=timedate_font, bg=background_color, fg=foreground_color, padx=30, pady=30)
            self.label_date = tk.Label(self.root,text='ma 1 jan', font=timedate_font, bg=background_color, fg=foreground_color, padx=30, pady=30)
            
            self.label_time.place(relx=0, rely=0, anchor=tk.NW)
            self.label_date.place(relx=1, rely=0, anchor=tk.NE)

            self.label_title = tk.Label(self.root, text=self.title.upper(), font=title_font, bg=background_color, fg=foreground_color, wraplength=650)
            self.label_title.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

            self.label_bottom = tk.Label(self.root,text=self.description, font=("Helvetica", 40), bg=background_color, fg=foreground_color, padx=30, pady=30, wraplength=650)
            self.label_bottom.place(relx=0.5, rely=1, anchor=tk.S)     


            # Set the initial color of the text
            self.label_title.configure(fg=self.colors[0])
            # Set the current color index to 0
            self.current_color = 0            
            self.is_created = True

            # Bind the function to the left mouse button click event
            self.press_screen = self.root.bind("<Button-1>", self.destroy)            
            
            # first update immediatelly
            self.update_calendar()
            self.root.mainloop()
        else:
            self.destroy(None)

    def search_for_substrings(self, s, substrings):
        for substring in substrings:
            if substring in s:
                return True
        return False

    # Define a function to exit the program when the screen is clicked
    def destroy(self, event):
        # Bind the function to the left mouse button click event
        self.root.unbind("<Button-1>", self.press_screen)
        self.is_showing = False
        self.root.destroy()


class Main:    
    def __init__(self):
        self.calendar = HomeCalendar()

if __name__ == "__main__":
    main = Main()