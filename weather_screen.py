from __future__ import annotations
import os
import pathlib
from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from main import MainApp

import json
import sys
import logging

logger = logging.getLogger(__name__)

import logging
import time
import datetime
import locale
import tkinter as tk
from tkinter import font as tkFont
from PIL import Image, ImageTk
from io import BytesIO
import aiohttp
import asyncio
from urllib3.exceptions import InsecureRequestWarning
import warnings

"""
todo:
- either proper async or no async at all

current weather: https://openweathermap.org/current
5d forecast: https://openweathermap.org/forecast5
"""

class WeatherScreen:
    def __init__(self, main_app: MainApp, frame, api_key = "", city_id = "", language="en", units="metric"):
        self.main_app = main_app
        self.frame = frame
        self.weather_update_job = None
        self.api_failure_count = 0
        
        self.is_showing = False
        self.is_created = False
        if not api_key or not city_id:
            raise ValueError("API key and city ID are required")
        self.idle = False
        self.api_key = api_key
        self.lang = language # language
        self.city_id = city_id
        self.units = units # standard, metric or imperial
        # possibly check out buienradar: https://pypi.org/project/buienradar/
        self.img_base_url = 'https://openweathermap.org/img/wn/'
        self.icon_size_large = 300
        self.last_updated = 0
        background_color = self.main_app.settings.menu_background_color.get("weather")
        if background_color is None:
            background_color = 'black'
        foreground_color = 'white'
        self.previous_condition_image_url = ''

        self.degrees = u"\u00b0"
        self.arrow_up = u"\u25b2"
        self.arrow_down = u"\u25bc"

        width = self.main_app.settings.screen_width
        height = self.main_app.settings.screen_height

        timedate_font = tkFont.Font(family="Helvetica", size=60, weight="bold")
        temp_font = tkFont.Font(family="Helvetica", size=100, weight="bold")
        description_font = tkFont.Font(family="Helvetica", size=50)
        minmax_font = tkFont.Font(family="Helvetica", size=30)

        self.main_frame = tk.Frame(self.frame, background=background_color, width=width, height=height)
        self.time_frame = tk.Frame(self.main_frame, background=background_color, width=width, height=130)
        self.sub_frame = tk.Frame(self.main_frame, background=background_color, width=width, height=540)
        self.bottom_frame = tk.Frame(self.main_frame, background=background_color, width=width, height=50)
        self.temp_frame = tk.Frame(self.sub_frame, background=background_color, width=width, height=200)

        self.sub_frame.grid_propagate(False)
        self.time_frame.grid_propagate(False)
        self.bottom_frame.grid_propagate(False)
        self.temp_frame.grid_propagate(False)

        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.time_frame.grid(row=0, column=0, sticky="nsew")
        self.sub_frame.grid(row=1, column=0, sticky="nsew")
        self.bottom_frame.grid(row=2, column=0, sticky="nsew")
        
        self.label_time = tk.Label(self.time_frame,text='00:00', font=timedate_font, bg=background_color, fg=foreground_color, padx=30, pady=30)
        self.label_date = tk.Label(self.time_frame,text='ma 1 jan', font=timedate_font, bg=background_color, fg=foreground_color, padx=30, pady=30)

        self.label_time.place(relx=0, rely=0, anchor=tk.NW)
        self.label_date.place(relx=1, rely=0, anchor=tk.NE)

        self.label_temperature = tk.Label(self.temp_frame,text=f'--{self.degrees}C', font=temp_font, bg=background_color, fg=foreground_color, padx=20, pady=20)
        self.label_min = tk.Label(self.temp_frame,text=f'{self.arrow_down} --{self.degrees}C', font=minmax_font, bg=background_color, fg=foreground_color, padx=20, pady=10)
        self.label_max = tk.Label(self.temp_frame,text=f'{self.arrow_up} --{self.degrees}C', font=minmax_font, bg=background_color, fg=foreground_color, padx=20, pady=10)

        self.no_connection_image = Image.open(os.fspath(pathlib.Path(__file__).parent / f'images/buttons/no-wifi-white.png'))
        self.no_connection_image = self.no_connection_image.resize(self.main_app.settings.feedback_icon_size)
        self.no_connection_image = ImageTk.PhotoImage(self.no_connection_image)

        self.no_connection_label = tk.Label(self.main_frame, image=self.no_connection_image,bg=background_color)
        self.no_connection_label.image = self.no_connection_image  # Keep a reference
        self.no_connection_label.configure(image=self.no_connection_image,width=self.main_app.settings.feedback_icon_size[0],height=self.main_app.settings.feedback_icon_size[1])
        self.no_connection_label.place(relx=.95, rely=.95, anchor='se')

        relx = 0.6
        rely_correction = 0     
        if(not self.main_app.system_info["is_desktop"]):
            rely_correction = 0.05
        self.label_temperature.place(relx=relx,rely=0.5+rely_correction, anchor=tk.E)
        self.label_max.place(relx=relx,rely=0.5, anchor=tk.SW)
        self.label_min.place(relx=relx,rely=0.5, anchor=tk.NW)
        
        self.label_condition = tk.Label(self.sub_frame,text='IMAGE', bg=background_color, fg=foreground_color)
        self.label_description = tk.Label(self.sub_frame,text=f'mooi weer', font=description_font, bg=background_color, fg=foreground_color)

        self.label_condition.grid(row=0,column=0)
        self.temp_frame.grid(row=1,column=0)
        self.label_description.grid(row=2,column=0)
        
        self.time_frame.grid_columnconfigure(0, weight=1)
        self.sub_frame.grid_columnconfigure(0, weight=1)
        self.bottom_frame.grid_columnconfigure(0, weight=1)
        self.time_frame.grid_rowconfigure(0, weight=1)
        self.sub_frame.grid_rowconfigure(0, weight=1)
        self.bottom_frame.grid_rowconfigure(0, weight=1)
        
        self.is_created = True
        self.recurring_job = None
        self.blink_id = None
        self.network_available = True

        self.update_time_inteval = 10 * 1000

    def show(self):
        self.update_weather_loop()
        self.update_time_loop()
        return True

    def update_weather_loop(self):
        try:
            # Controleer of er al een geplande update is en annuleer deze
            if self.weather_update_job is not None:
                self.main_frame.after_cancel(self.weather_update_job)
                logger.debug("Existing weather update job canceled.")

            # Voer de update uit
            self.update_weather()

            # Plan de volgende update
            self.weather_update_job = self.main_frame.after(
                self.main_app.settings.weather_update_interval * 1000,
                self.update_weather_loop
            )
            logger.debug(f"Weather update job scheduled {self.main_app.settings.weather_update_interval} seconds from now.")
        except Exception as e:
            # Log fouten
            logger.error(f"Error in update_weather_loop: {e}")
            self.weather_update_job = None  # Reset de job zodat er geen ghost jobs zijn

    def update_time_loop(self):
        self.update_time()
        # Set the time update timer (e.g., every 10 seconds)
        self.time_update_job = self.main_frame.after(self.update_time_inteval, self.update_time_loop)

    def make_request(self, url):
        for attempt in range(self.main_app.settings.weather_api_call_direct_retries):
            try:
                # Suppress InsecureRequestWarning if verify is False
                if not self.main_app.settings.verify_ssl_on_trusted_sources:
                    logger.debug("Surpressing HTTTPS InsecureRequestWarning")
                    warnings.filterwarnings("ignore", category=InsecureRequestWarning)

                # Add a timeout to the request
                response = requests.get(url, timeout=10, verify=self.main_app.settings.verify_ssl_on_trusted_sources)

                if response.status_code == 200:
                    self.update_network_availability(True)
                    logger.debug("Success getting weather info.")
                    return response.content  # Return the response content
                else:
                    logger.error(f"HTTP error {response.status_code} for URL: {url}")
            except requests.Timeout:
                logger.error(f"Timeout when calling {url}. Attempt {attempt + 1} of {self.main_app.settings.weather_api_call_direct_retries}.")
            except requests.RequestException as e:
                logger.error(f"Request exception for {url}: {e}. Attempt {attempt + 1} of {self.main_app.settings.weather_api_call_direct_retries}.")

            # If there's an error, update network status and retry
            self.update_network_availability(False)

        # Increment failure counter after all retries fail
        self.api_failure_count += 1
        logger.error(f"API request failed after {self.main_app.settings.weather_api_call_direct_retries} retries. Failure count: {self.api_failure_count}")

        # Trigger reboot if failure count reaches the limit
        if self.main_app.settings.weather_api_call_reboot_after_retries>0 and self.api_failure_count >= self.main_app.settings.weather_api_call_reboot_after_retries:
            logger.critical("API failure count exceeded limit. Triggering system reboot.")
            if self.main_app.settings.restart_program_style == 'application':
                self.main_app.touch_controller.reboot(ask=True)
            else:
                self.main_app.touch_controller.quit_app(ask=False)
            
        return None

    def update_network_availability(self, network_available):
        if network_available:
            self.no_connection_label.place_forget()       
        else:
            logger.warning(f"Network unavailable.")
            self.no_connection_label.place(relx=.95, rely=.95, anchor='se')

    def update_weather(self):
        try:
            url = f'https://api.openweathermap.org/data/2.5/weather?id={self.city_id}&appid={self.api_key}&units={self.units}&lang={self.lang}'
            data = self.make_request(url)
            if data is None:
                logger.error(f"No response from weather; just try the next cycle in {self.main_app.settings.weather_update_interval} seconds.")
                return
            
            logger.debug(f"Got weather data at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}")

            try:
                json_data = json.loads(data.decode('utf-8'))
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON: {e}")
                return None

            self.today_data = json_data
            self.last_updated = time.time()

            # Update GUI
            try:
                self.update_weather_gui()
            except Exception as e:
                logger.error(f"Could not update weather GUI elements: {e}")
        except Exception as e:
            logger.error(f"Error in update_weather: {e}")

    def update_weather_gui(self):
        temperature = self.today_data['main']['temp']
        temp_min = self.today_data['main']['temp_min']
        temp_max = self.today_data['main']['temp_max']
        description = self.today_data['weather'][0]['description'].capitalize()
        icon = self.today_data['weather'][0]['icon']

        condition_image_url = f'{self.img_base_url}{icon}@4x.png'

        if self.previous_condition_image_url != condition_image_url:
            try:
                condition_image_response = self.make_request(condition_image_url)
                condition_image_bytes = BytesIO(condition_image_response)
                condition_image = Image.open(condition_image_bytes)
                condition_image = condition_image.resize(
                    (self.icon_size_large, self.icon_size_large),
                    ImageTk.Image.LANCZOS
                )
                self.weather_now_image = ImageTk.PhotoImage(condition_image)
            except Exception as e:
                logger.error(f"Could not open weather image: {e}")
                return

        self.previous_condition_image_url = condition_image_url

        self.label_condition.configure(image=self.weather_now_image)
        self.label_temperature.configure(text=f'{round(temperature)}{self.degrees}C')
        self.label_max.configure(text=f'{self.arrow_up}{round(temp_max)}{self.degrees}C')
        self.label_min.configure(text=f'{self.arrow_down}{round(temp_min)}{self.degrees}C')
        self.label_description.configure(text=description)

    def update_time(self):
        """
        sudo sed -i "s/# nl_NL.UTF-8/nl_NL.UTF-8/g" /etc/locale.gen
        sudo locale-gen
        """
        if(not self.main_app.system_info["is_desktop"]):
            locale.setlocale(locale.LC_TIME, "nl_NL.UTF8") # dutch
            
        current_time = datetime.datetime.now()
        time_string = current_time.strftime("%H:%M")
        if self.main_app.system_info["system_platform"]=="Windows":
            date_string = current_time.strftime("%a %#d %b")
        else:
            date_string = current_time.strftime("%a %-d %b")
        
        #logger.debug(f"Setting time to {time_string} every {self.update_time_inteval}ms ({self.update_time_inteval/1000} seconds)")
        # Load labels with new values
        try:
            self.label_time.configure(text=time_string)
            self.label_date.configure(text=date_string)
        except Exception as e:
            logger.error(f"Could not update datetime GUI elements: {e}")
        
    def set_idle(self, idle=True):
        if(idle):
            self.frame.backlight.set_power(False)
        else:
            self.frame.backlight.set_power(True)
        
        self.idle = idle

