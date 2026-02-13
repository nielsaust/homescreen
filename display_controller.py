import math
import os
import pathlib
import sys
import logging
logger = logging.getLogger(__name__)

import time
import tkinter as tk
from PIL import Image, ImageTk
from hyperpixel_backlight import Backlight

class DisplayController:
    def __init__(self, main_app):
        self.main_app = main_app
        self.previous_screen = None
        self.current_screen = None
        self._screen_state = None
        self.screens = {}
        self.screen_objects = {}
        self.action_labels = []

        # Create screens
        self.music_screen = None
        self.menu_screen = None
        # switching/state screens
        self.create_screen("off")
        self.create_screen("weather")
        self.create_screen("music")
        self.create_screen("menu")

        self.current_overlay_label = None
        # overlapping screens
        
        from app.ui.screens.cam_screen import CamScreen
        self.cam_screen = CamScreen(self.main_app)
        from app.ui.screens.calendar_screen import CalendarScreen
        self.calendar_screen = CalendarScreen(self.main_app)
        from app.ui.screens.print_screen import PrintScreen
        self.print_screen = PrintScreen(self.main_app)
        from app.ui.screens.slideshow import SlideShow
        self.slideshow = SlideShow(self.main_app)
        from app.ui.screens.alert_screen import AlertScreen
        self.alert_screen = AlertScreen(self.main_app)

        self.time_in_screen = time.time() - 1000 # offset for start

        # display options for Pi Screen
        self.backlight = None
        self.is_showing = False
        if(not self.main_app.system_info["is_desktop"]):
            self.backlight = Backlight()
            self.main_app.root.attributes("-fullscreen", True)

    def create_screen(self, screen_name):
        # Create a frame for the screen
        frame_background_color = self.main_app.settings.menu_background_color.get(screen_name)
        if frame_background_color is None:
            frame_background_color = "#000000"
        screen_frame = tk.Frame(self.main_app.root, bg=frame_background_color)
        # Add widgets and logic specific to each screen here
        if screen_name == "off":
            from app.ui.screens.turned_off_screen import TurnedOffScreen
            screen_object = TurnedOffScreen(self.main_app,screen_frame)
        elif screen_name == "weather":         
            from app.ui.screens.weather_screen import WeatherScreen
            screen_object = WeatherScreen(self.main_app,screen_frame,self.main_app.settings.weather_api_key, self.main_app.settings.weather_city_id, self.main_app.settings.weather_langage)
        elif screen_name == "music":
            from app.ui.screens.music_screen import MusicScreen
            screen_object = MusicScreen(self.main_app,screen_frame)
        elif screen_name == "menu":
            from app.ui.screens.menu_screen import MenuScreen
            screen_object = MenuScreen(self.main_app,screen_frame)
        
        # Store the screen frame in the dictionary
        self.screens[screen_name] = screen_frame
        self.screen_objects[screen_name] = screen_object

    def exit_menu(self):
        menu_screen = self.screen_objects.get("menu")
        if(menu_screen):
            menu_screen.exit_menu()

    def close_open_windows(self):
        self.print_screen.destroy()
        self.cam_screen.destroy()
        self.calendar_screen.destroy()
        self.alert_screen.destroy()
        self.slideshow.destroy()

    def show_fullscreen_image(self, image):
        menu_screen = self.screen_objects.get("menu")
        if(menu_screen):
            menu_screen.show_fullscreen_image(image)

    def open_slideshow(self):
        if self.slideshow:
            self.close_open_windows()
            self.slideshow.show()

    def show_cam(self, data, url, username=None, password=None):
        if self.cam_screen:
            self.close_open_windows()
            self.cam_screen.show(data, url, username, password)
            self.check_idle(True)

    def show_calendar(self,data):
        if self.calendar_screen:
            self.close_open_windows()
            self.calendar_screen.show(data)
            self.check_idle(True)

    def show_alert(self, data):
        """
        Wrapper around AlertScreen.show()
        Allows showing alerts directly with simple params.
        """
        logger.debug(f"show_alert(data: {data})")

        if self.alert_screen:
            self.close_open_windows()
            self.alert_screen.show(data)
            self.check_idle(True)

    def close_alert_screen(self):
        if self.alert_screen:
            self.alert_screen.destroy()

    def show_print_status(self,progress,reset=False):
        if self.print_screen and progress is not None:
            self.close_open_windows()
            self.print_screen.show(progress)
            self.check_idle(True)
            if reset:
                self.print_screen.cancel_blink()

    def close_print_screen(self):
        if self.print_screen:
            self.print_screen.destroy()

    def update_print_progress(self,progress):
        if self.print_screen and self.print_screen.is_showing:
            self.print_screen.update(progress)

    def print_screen_attention(self):
        if self.print_screen and self.main_app.settings.printer_screen_blink_on_complete:
            self.print_screen.blink_percentage()

    def cancel_attention(self):
        if self.print_screen and self.print_screen.is_blinking:
            self.print_screen.cancel_blink()

    def show_show_slider(self,entity,title,type="light"):
        self.stop_menu_timer()
        from slider_screen import SliderScreen
        SliderScreen(self.main_app,entity,title,type)
        
    def start_menu_timer(self):
        menu_screen = self.screen_objects.get("menu")
        if(menu_screen):
            menu_screen.close_timeout()

    def stop_menu_timer(self):
        menu_screen = self.screen_objects.get("menu")
        if(menu_screen):
            menu_screen.close_timeout(False)

    def show_screen(self, screen_name, init=False, force=False):
        time_between_switches = time.time() - self.time_in_screen
        logger.debug(f"show_screen({screen_name}) time_between_switches: {time_between_switches} - forced = {force}")
        if (time_between_switches<self.main_app.settings.min_time_between_actions and not force):
            logger.warning(f"Switched screens too fast ({time_between_switches}ms); could result in errors so abording. (self.current_screen = {self.current_screen})")
            return

        self._screen_state = screen_name
        # Hide the current screen if there is one and it's not the same as currently active
        allow_forget = (self.current_screen is not None) and (self.current_screen!=self.screens.get(screen_name))
        if allow_forget:
            logger.debug(f"forgetting {self.current_screen}")
            self.current_screen.pack_forget()
            self.force_screen_update()
        else:
            logger.debug(f"can't forget {self.current_screen} for it is the current screen already")

        # Show the selected screen
        self.previous_screen = self.current_screen
        self.current_screen = self.screens.get(screen_name)
        if self.current_screen:
            logger.debug(f"Showing {screen_name}")
            screen_object = None
            try:
                logger.debug(f"trying get screen object of {screen_name}")
                screen_object = self.screen_objects.get(screen_name)
            except Exception as e:
                logger.error(f"Error getting screen object {screen_name}: {e}")

            if screen_object:
                try:
                    logger.debug(f"trying to show {screen_name}")
                    if(screen_object.show()):
                        logger.info(f"Showing {screen_name} screen")
                        self.current_screen.pack(fill=tk.BOTH, expand=True)
                        self.time_in_screen = time.time()
                        logger.debug(f"screen_object {screen_object} at {screen_object.__class__.__name__} created and updated ({self.time_in_screen})")
                    else:
                        self.current_screen = self.previous_screen
                        logger.error(f"Error showing screen {screen_name}")
                except Exception as e:
                    logger.error(f"Error creating screen {screen_name}: {e}")
            else:
                logger.error(f"No screen object ({screen_name}) to show/found in self.screen_objects {self.screen_objects}")
        else:
            logger.error(f"No current screen; screen '{screen_name}' was not yet created")

        if screen_name != "off":
            self.check_idle()
        self.force_screen_update()

    def show_music_overlays(self):
        music_screen = self.screen_objects.get("music")
        if music_screen and self.get_screen_state() == "music":
            obj = getattr(self.main_app, "music_object", None)
            if obj is None:
                return
            music_screen.show_overlays(
                getattr(obj, "artist", None),
                getattr(obj, "title", None),
                getattr(obj, "album", None),
                getattr(obj, "channel", None),
            )

    def clear_album_art(self):
        music_screen = self.screen_objects.get("music")
        if(music_screen and self.get_screen_state()=="music"):
            music_screen.clear_album_art()

    def update_menu_states(self):
        menu_screen = self.screen_objects.get("menu")
        if(menu_screen):
            menu_screen.update_buttons()

    def menu_ready(self):
        ready = False
        menu_screen = self.screen_objects.get("menu")
        if(menu_screen):
            ready = menu_screen.created_and_updated

        return ready

    def switch_menu_page(self,page_direction=1):
        if(self.get_screen_state() == "menu"):
            menu_screen = self.screen_objects.get("menu")
            if(menu_screen):
                menu_screen.switch_page(page_direction)
                self.force_screen_update()
                max_page = menu_screen.max_page
                current_page = menu_screen.current_menu_page
                return {"current": current_page, "max": max_page}

    def menu_back(self):
        if(self.get_screen_state() == "menu"):
            menu_screen = self.screen_objects.get("menu")
            if(menu_screen):
                menu_screen.back()

    def force_screen_update(self):
        if(self.main_app.settings.force_update):
            logger.debug("Forcing screen update")
            self.main_app.root.update()
            self.main_app.root.update_idletasks()
        else:
            logger.debug("Not forcing screen update; force_update is false")

    def place_action_label(self, text=None, anchor="center", image=None, bg='black', fg='white', bordercolor='black'): 
        if self.main_app.settings.show_feedback_label_timeout==0:
            logger.info(f"Settings disallow for feedback label to be shown.")   
            return
        
        def remove(label):
            self.action_labels.remove(label)
            label.destroy()

        label_options = {
            "fg": fg,
            "bg": bg,
            "padx": self.main_app.settings.feedback_label_padx,
            "pady": self.main_app.settings.feedback_label_pady,
            "wraplength": self.main_app.settings.feedback_label_width-10,
            "highlightbackground": bordercolor,
            "highlightthickness": self.main_app.settings.feedback_label_border,
        }

        if text is not None:
            label_options["text"] = text
            label_options["compound"] = "top"
            label_options["font"] = "Helvetica 20"

        label = tk.Label(self.main_app.root, **label_options)
        self.current_overlay_label = label

        if image is not None:
            image_path= os.fspath(pathlib.Path(__file__).parent / f'images/buttons/{image}')
            image = Image.open(image_path)
            image = image.resize(self.main_app.settings.feedback_icon_size)
            label_image = ImageTk.PhotoImage(image)
            label.image = label_image
            label.configure(image=label_image,width=self.main_app.settings.feedback_label_width,height=self.main_app.settings.feedback_label_height)
        
        label_x = math.floor((self.main_app.settings.screen_width-self.main_app.settings.feedback_label_width)/2)-self.main_app.settings.feedback_label_border
        label_y = math.floor((self.main_app.settings.screen_height-self.main_app.settings.feedback_label_height)/2)-self.main_app.settings.feedback_label_border
        
        if anchor!="center":
            label.place(x=self.main_app.root.winfo_width() - label.winfo_reqwidth(), y=self.main_app.root.winfo_height() - label.winfo_reqheight())
        else:
            label.place(x=label_x, y=label_y)

        self.action_labels.append(label)

        # Destroy the label after 3 seconds
        self.current_overlay_label_timeout = self.main_app.root.after(self.main_app.settings.show_feedback_label_timeout, lambda: remove(label))

    def check_idle(self,turn_on=False):
        screen = self.get_screen_state()
        if turn_on:
            self.turn_on()
        elif screen=="menu":
            self.turn_on()
        elif screen=="music":
            if self.main_app.device_states.in_bed:
                self.turn_off()
            else:
                self.turn_on()
        elif screen=="off":
            self.turn_off()

    def turn_on(self):
        logger.info("turning screeen on")
        self.is_showing = True
        if(not self.main_app.system_info["is_desktop"]):
            self.backlight.set_power(True)

    def turn_off(self):
        logger.info("turning screeen off")
        self.is_showing = False
        self.close_open_windows()
        if not self.main_app.settings.show_weather_on_idle and self.get_screen_state() != "off":
            self.show_screen("off")
        if(not self.main_app.system_info["is_desktop"]):
            self.backlight.set_power(False)

    # Getter method for screen_state
    def get_screen_state(self):
        return self._screen_state
