from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import MainApp

import logging
import pathlib

logger = logging.getLogger(__name__)
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
IMAGES_DIR = PROJECT_ROOT / "images"

import math
import time
import tkinter as tk
import os

from tkinter import font as tkFont

from menu_button import MenuButton

class MenuScreen:
    def __init__(self, main_app: MainApp, frame):
        self.main_app = main_app
        self.frame = frame

        self.created_and_updated = False
        self.active_buttons = []
        self.num_active_buttons = 4
        self.current_menu_page = 1
        self.main_page_nr = 1
        self.in_subpage = False

        self.exit_timeout_future = None
        self.exit_timeout_ms = self.main_app.settings.close_menu_timeout
        self.button_click_time = None
        
        self.buttons = [
            # page 1
            {"button": MenuButton("cinema","Zet bioscoop [cinema_action]","cinema.png","cinema"), "screen": []},
            {"button": MenuButton("debug_cinema","Bios probleem repareren","tools.png","open_page"), "screen": [
                {"button": MenuButton("debug_cinema_back","Terug","back.png","back")},
                {"button": MenuButton("soundbar_toggle","Zet soundbar aan/uit","speaker.png","soundbar_toggle")},
                {"button": MenuButton("beamer_on","Zet projector aan","video.png","beamer_on")},
                {"button": MenuButton("beamer_off","Zet projector uit","video-off.png","beamer_off")},
                {"button": MenuButton("blinds_up","Scherm omhoog","blinds-up.png","blinds_up")},
                {"button": MenuButton("blinds_down","Scherm omlaag","blinds-down.png","blinds_down")},
                {"button": MenuButton("blinds_stop","Stop scherm","blinds.png","blinds_stop")},
                {"button": MenuButton("soundbar_hdmi","HDMI 1","output.png","soundbar_hdmi")},
                {"button": MenuButton("ps_toggle","Playstation [ps_action]","ps.png","ps_toggle")},
                {"button": MenuButton("soundbar_volume_down","Zachter","volume-down.png","soundbar_volume_down")},
                {"button": MenuButton("soundbar_volume_up","Harder","volume-up.png","soundbar_volume_up")},
                {"button": MenuButton("soundbar_mute","Mute soundbar","mute.png","soundbar_mute")}
            ]},
            {"button": MenuButton("music","Muziek","music.png","music_menu"), "screen": [
                {"button": MenuButton("music_back","Terug","back.png","back")},
                {"button": MenuButton("music_volume_up","Harder","volume-up.png","music_volume_up")},
                {"button": MenuButton("music_play_pause","[music_action] muziek","play.png","music_play_pause")},
                {"button": MenuButton("music_volume_down","Zachter","volume-down.png","music_volume_down")},
                {"button": MenuButton("music_previous","Vorig nummer","backward.png","music_previous")},
                {"button": MenuButton("music_next","Volgend nummer","forward.png","music_next")},
                {"button": MenuButton("music_show_title","Toon muziek details","detail.png","music_show_title",cancel_close=True)}
            ]},
            {"button": MenuButton("light_scenes","Lichten","lights.png","light_scenes"), "screen": [
                {"button": MenuButton("light_scenes_back","Terug","back.png","back")},
                {"button": MenuButton("lights_movie","Movie scene","movie.png","scene_movie")},
                {"button": MenuButton("lights_romance","Romance scene","romance.png","scene_romantic")},
                {"button": MenuButton("lights_dinner","Normal / dinner scene","cutlery.png","scene_dinner")},
                {"button": MenuButton("light_woonkamer","Woonkamer licht [woonkamer_licht_action]","sofa.png","light_woonkamer")},
                {"button": MenuButton("light_keuken","Keuken licht [keuken_licht_action]","kitchen.png","light_keuken")},
                {"button": MenuButton("light_tafel","Tafel licht [tafel_licht_action]","table.png","light_tafel")},
                {"button": MenuButton("light_kleur","Kleur licht [kleur_licht_action]","color-lights.png","light_kleur")},
                {"button": MenuButton("lights_bright","Fel scene","bright.png","scene_bright")},
                {"button": MenuButton("lights_off","Licht uit","light-off.png","scene_off")}
            ]},
            # page 2
            {"button": MenuButton("cover_kitchen","Doe keuken gordijn [cover_action]","curtain.png","cover_kitchen"), "screen": []},
            {"button": MenuButton("blinds_control","Rolgordijn schijfpui","blinds.png","open_page"), "screen": [
                {"button": MenuButton("blinds_control_back","Terug","back.png","back")},
                {"button": MenuButton("blinds_up","Scherm omhoog","blinds-up.png","blinds_up")},
                {"button": MenuButton("blinds_down","Scherm omlaag","blinds-down.png","blinds_down")},
                {"button": MenuButton("blinds_stop","Stop scherm","blinds.png","blinds_stop")}
            ]},
            {"button": MenuButton("doorbell","Voordeur","door.png","doorbell"), "screen": []},
            {"button": MenuButton("calendar","Volgend kalender item","calendar.png","calendar"), "screen": []},
            # page 3
            {"button": MenuButton("calendar_add","Voeg kalender item toe","calendar-plus.png","calendar_add"), "screen": []},
            {"button": MenuButton("trash_warning_toggle","Zet afval melding [trash_action]","trash-x.png","trash_warning_toggle"), "screen": []},
            {"button": MenuButton("screen_off","Zet scherm uit","screen-off.png","turn_screen_off"), "screen": []},
            {"button": MenuButton("in_bed_toggle","Zet 'in-bed' modus [in_bed_action]","in-bed.png","in_bed_toggle"), "screen": []},
            # page 4
            {"button": MenuButton("wifi_qr","Wifi QR code","wifi.png","wifi_qr"), "screen": []},
            #{"button": MenuButton("heart","Activate love","heart.png","heart"), "screen": []},
            #{"button": MenuButton("christmas","Activate christmas","christmas.png","christmas"), "screen": []},
            {"button": MenuButton("3d_printer_progress","Check 3D print status","3d-object.png","3d_printer_status"), "screen": []},
            {"button": MenuButton("3d_printer_cam","3D printer cam","camera.png","3d_printer_cam"), "screen": []},
            {"button": MenuButton("system_options","Systeem","system.png","system_options"), "screen": [
                {"button": MenuButton("options_back","Terug","back.png","back")},
                {"button": MenuButton("show_weather_on_idle","Toon weer als idle","weather.png","show_weather_on_idle")},
                {"button": MenuButton("verify_ssl_on_trusted_sources","SSL","shield.png","verify_ssl_on_trusted_sources")},
                {"button": MenuButton("media_show_titles","Toon media titels","text.png","media_show_titles")},
                {"button": MenuButton("media_sanitize_titles","Kort titels in","text.png","media_sanitize_titles")},
                {"button": MenuButton("quit","Sluit deze app","exit.png","exit")},
                {"button": MenuButton("shell_reboot","Reboot machine","shell.png","shell_reboot")},
                {"button": MenuButton("shell_shutdown","Shutdown machine","shell.png","shell_shutdown")},
                {"button": MenuButton("shell_disable_networking","Disable networking","shell.png","shell_disable_networking")},
                {"button": MenuButton("shell_enable_networking","Enable networking","shell.png","shell_enable_networking")},
                {"button": MenuButton("shell_recover_network","Recover network","shell.png","shell_recover_network")}
            ]},
        ]

        self.button_color = self.main_app.settings.button_color
        self.button_after_ids = {}
        self.max_page = math.ceil(len(self.buttons) / self.num_active_buttons)

        self.click_x = None
        self.click_y = None

        self.fullscreen_image_window = None

        self.create_buttons(self.buttons)
        for i, button in enumerate(self.buttons):
            sub_buttons = self.buttons[i].get("screen")
            if(len(sub_buttons)>0):
                self.create_buttons(sub_buttons)
            

    def create_buttons(self, buttons):
        font = tkFont.Font(family="Helvetica", size=self.main_app.settings.menu_item_font_size, weight="bold")
        for button in buttons:
            button = button.get("button")
            button_name = button.text
            image_path = os.fspath(IMAGES_DIR / "buttons" / button.image)
            
            try:
                button_image = tk.PhotoImage(file=image_path)
            except FileNotFoundError as file_not_found_error:
                # Handle FileNotFoundError (file not found)
                logger.error(f"Button image file not found error: {file_not_found_error}")
            except OSError as os_error:
                # Handle OSError (e.g., permission or file system error)
                logger.error(f"OS error: {os_error}")
            except Exception as e:
                # Handle other exceptions that may occur
                logger.error(f"An unexpected error occurred getting button image: {e}")

            label = tk.Label(self.frame, 
                            image=button_image, 
                            bg=self.button_color.get("inactive"), 
                            fg="black", 
                            text=button_name, 
                            compound="top",                              
                            font=font, 
                            padx=20, 
                            pady=20, 
                            wraplength=200,
                            highlightbackground=self.main_app.settings.button_color.get("down"),
                            highlightthickness=0)
            label.image = button_image
            button.label = label

    def show(self):
        self.in_subpage = False
        self.remove_current_menu()
        self.make_menu_buttons()
        return True

    def back(self):
        self.in_subpage = False
        self.remove_current_menu()
        self.make_menu_buttons(self.main_page_nr)
        
    def make_menu_buttons(self,page_nr=1,buttons=None):
        self.close_timeout()
        self.current_menu_page = page_nr
        if(not buttons):
            buttons = self.buttons

        self.max_page = math.ceil(len(buttons) / self.num_active_buttons)
        self.active_buttons = buttons[(self.current_menu_page-1)*self.num_active_buttons:self.current_menu_page*self.num_active_buttons]

        # Calculate a fixed size for the buttons
        button_width = self.main_app.settings.menu_button_width
        button_height = self.main_app.settings.menu_button_height

        for i in range(self.num_active_buttons):
            self.frame.grid_rowconfigure(i // 3, weight=1, minsize=button_height)
            self.frame.grid_columnconfigure(i % 3, weight=1, minsize=button_width)

        for i, button in enumerate(self.active_buttons):
            button = button.get("button")
            # prevent making extra Label when button already has one (sort of pooling)
            if(button.label is not None):
                label = button.label
            else:
                logger.critical(f"Critical error: No label found for button (make real error)")
            
            #label.configure(bg = "white")
            row = i // 2  # Calculate the row (0 or 1)
            col = i % 2   # Calculate the column (0 or 1)
            label.grid(row=row, column=col, padx=self.main_app.settings.menu_button_padding, pady=self.main_app.settings.menu_button_padding, sticky="nsew")

            button_nr=((self.current_menu_page-1)*self.num_active_buttons+(i+1))
            button.bind_down_event = lambda event, button=button, button_nr=button_nr: self.handle_button_click(event, button, button_nr)
            button.bind_up_event = lambda event, button=button, button_nr=button_nr: self.handle_button_release(event, button, button_nr)

            # Register a click event for each button
            label.bind("<Button-1>", button.bind_down_event)
            label.bind("<ButtonRelease-1>", button.bind_up_event)

        if(self.main_app.display_controller):
            self.main_app.display_controller.place_action_label(f"{page_nr}/{self.max_page}",anchor="se")
            logger.debug(f"Placing action label: {page_nr}/{self.max_page}")
            self.main_app.display_controller.force_screen_update()

        self._trace_menu_render("menu.render.complete")

    def enter_submenu(self):
        self.remove_current_menu()
        self.in_subpage = True
        self.main_page_nr = self.current_menu_page
        self.make_menu_buttons(buttons=self.sub_buttons)

    def switch_page(self,page_direction=1):
        self.remove_current_menu()
        new_page_nr = self.current_menu_page+page_direction
        if(new_page_nr<1):
            new_page_nr = self.max_page
        elif(new_page_nr>self.max_page):
            new_page_nr = 1

        buttons = None
        if self.in_subpage:
            buttons = self.sub_buttons

        self.make_menu_buttons(new_page_nr,buttons)
    
    def show_fullscreen_image(self, image):
        image_path = os.fspath(IMAGES_DIR / image)
        # Create a top-level window for the QR code overlay
        self.fullscreen_image_window = tk.Toplevel(self.frame)
        fullscreen_image = tk.PhotoImage(file=image_path)
        if(not self.main_app.system_info["is_desktop"]):
            self.fullscreen_image_window.attributes('-fullscreen', True)  # Make it fullscreen

        # Create a label to display the image
        fullscreen_image_label = tk.Label(self.fullscreen_image_window, image=fullscreen_image, bg="black")
        fullscreen_image_label.image = fullscreen_image
        fullscreen_image_label.pack(fill=tk.BOTH, expand=True)

        # Schedule a function to destroy the QR code overlay
        fullscreen_image_bind = self.fullscreen_image_window.bind("<ButtonRelease-1>", self.destroy_fullscreen_image)
        self.fullscreen_image_window.after(self.main_app.settings.destroy_image_timeout, self.destroy_fullscreen_image)

    def destroy_fullscreen_image(self, event=None):
        self.fullscreen_image_window.destroy()

    def remove_current_menu(self):
        if(self.frame is not None):
            self.remove_children(self.frame)

    def remove_children(self, widget):
        for child in widget.winfo_children():
            child.grid_forget()

    def change_button_background(self, button, new_color, duration_ms):
        widget = button.label
        # Change the background color temporarily
        original_color = widget.cget("background")
        widget.configure(background=new_color)

        # Cancel any previously scheduled background change actions for this button
        if button in self.button_after_ids:
            widget.after_cancel(self.button_after_ids[button])
            del self.button_after_ids[button]

        # Schedule a function to change it back after the specified duration
        self.button_after_ids[button] = widget.after(duration_ms, lambda button=button: self.change_button_background_back(button))

    def change_button_background_back(self, button):
        widget = button.label
        background_color = self.button_color.get("active") if button.is_active else self.button_color.get("inactive")
        widget.configure(background=background_color)

    # Define a method to handle button clicks
    def handle_button_click(self, event, button, button_nr):
        self.click_x = event.x_root
        self.click_y = event.y_root
        # Record the time of the initial click
        self.button_click_time = time.time()
        button.label.configure(highlightthickness=self.main_app.settings.menu_border_thickness)
        self.close_timeout()
        return "break"

    # Define a method to handle button clicks
    def handle_button_release(self, event, button, button_nr):
        if(button.cancel_close):
            self.close_timeout(False)
        else:
            self.close_timeout()

        button.label.configure(highlightthickness=0)
        if self.click_x is None or self.click_y is None:
            self.click_x = event.x_root
            self.click_y = event.y_root
        x_dir = event.x_root - self.click_x
        y_dir = event.y_root - self.click_y
        max_movement = max(abs(x_dir),abs(y_dir))
        min_movement = self.main_app.settings.gesture_min_movement
        
        if(max_movement>min_movement):
            logger.debug(f"Will not be seen as button click; moved more than {min_movement} ({max_movement})")
            # Consume menu widget event and route swipe explicitly so root handlers
            # do not need to receive this event.
            x_abs = abs(x_dir)
            y_abs = abs(y_dir)
            if x_abs > y_abs and x_dir > min_movement:
                self.main_app.perform_action("left")
            elif x_abs > y_abs and x_dir < -min_movement:
                self.main_app.perform_action("right")
            elif x_abs < y_abs and y_dir > min_movement:
                self.main_app.perform_action("down")
            elif x_abs < y_abs and y_dir < -min_movement:
                self.main_app.perform_action("up")
            return "break"

        sub_button_amount = 0

        if(not self.in_subpage):
            self.sub_buttons = self.buttons[button_nr-1].get("screen")
            sub_button_amount = len(self.sub_buttons)

        if self.button_click_time is not None:
            release_time = time.time()
            time_elapsed = release_time - self.button_click_time

            if time_elapsed >= self.main_app.settings.hold_time:
                self.handle_button_hold(button,time_elapsed)
            elif(sub_button_amount>0):
                self.enter_submenu()
            else:
                self.change_button_background(button=button, new_color=self.button_color.get("down"), duration_ms=self.main_app.settings.button_down_color_change_time)
                self.main_app.touch_controller.handle_menu_button(button.action)
        return "break"

    def handle_button_hold(self, button, time_held):
        logger.debug(f"Button held for more than {self.main_app.settings.hold_time} ({time_held}) seconds")
        self.main_app.touch_controller.handle_alt_menu_button(button.action)

    def update_buttons(self):
        if not self.main_app.device_states.devices_inited:
            return
        
        harmony_state = self.main_app.device_states.harmony_state
        cover_kitchen = self.main_app.device_states.cover_kitchen
        in_bed = self.main_app.device_states.in_bed
        trash_warning = self.main_app.device_states.trash_warning
        playstation_power = self.main_app.device_states.playstation_power
        playstation_available = self.main_app.device_states.playstation_available

        light_tafel = self.main_app.device_states.light_tafel
        light_keuken = self.main_app.device_states.light_keuken
        light_kleur = self.main_app.device_states.light_kleur
        light_woonkamer = self.main_app.device_states.light_woonkamer

        #settings
        show_weather_on_idle = self.main_app.settings.show_weather_on_idle
        verify_ssl_on_trusted_sources = self.main_app.settings.verify_ssl_on_trusted_sources
        media_show_titles = self.main_app.settings.media_show_titles
        media_sanitize_titles = self.main_app.settings.media_sanitize_titles
        
        playing = self.main_app.music_object is not None and self.main_app.music_object.state == "playing"
        if cover_kitchen is None:
            cover_kitchen = 0
        if harmony_state is None:
            harmony_state = "Off"
        if in_bed is None:
            in_bed = False
        if trash_warning is None:
            trash_warning = False
        if playing is None:
            playing = False

        button_configs = [
            {
                "button_id": "cinema", 
                "state_condition": harmony_state != 'Off', 
                "action_text": "[cinema_action]",
                "on_text": "uit", "off_text": "aan",
                "available": True 
            },
            {
                "button_id": 
                "cover_kitchen", 
                "state_condition": cover_kitchen < 50, 
                "action_text": "[cover_action]",
                "on_text": "open", "off_text": "dicht"
            },
            {
                "button_id": "in_bed_toggle", 
                "state_condition": in_bed, 
                "action_text": "[in_bed_action]",
                "on_text": "uit", "off_text": "aan"
            },
            {
                "button_id": "trash_warning_toggle", 
                "state_condition": trash_warning, 
                "action_text": "[trash_action]",
                "on_text": "uit", "off_text": "aan"
            },
            {
                "button_id": "music_play_pause", 
                "state_condition": playing, 
                "action_text": "[music_action]",
                "on_text": "Pauzeer", "off_text": "Speel"
            },
            {
                "button_id": "ps_toggle", 
                "state_condition": playstation_power, 
                "action_text": "[ps_action]",
                "on_text": "uit", "off_text": "aan",
                "available": playstation_available 
            },
            {
                "button_id": "light_woonkamer", 
                "state_condition": light_woonkamer["state"]=="on", 
                "action_text": "[woonkamer_licht_action]",
                "on_text": f"({self.recalculate_brightness_percentage(light_woonkamer['brightness'])}%) uit", "off_text": "aan"
            },
            {
                "button_id": "light_keuken", 
                "state_condition": light_keuken["state"]=="on", 
                "action_text": "[keuken_licht_action]",
                "on_text": f"({self.recalculate_brightness_percentage(light_keuken['brightness'])}%) uit", "off_text": "aan"
            },
            {
                "button_id": "light_tafel", 
                "state_condition": light_tafel["state"]=="on", 
                "action_text": "[tafel_licht_action]",
                "on_text": f"({self.recalculate_brightness_percentage(light_tafel['brightness'])}%) uit", "off_text": "aan"
            },
            {
                "button_id": "light_kleur", 
                "state_condition": light_kleur["state"]=="on", 
                "action_text": "[kleur_licht_action]",
                "on_text": f"({self.recalculate_brightness_percentage(light_kleur['brightness'])}%) uit", "off_text": "aan"
            },
            {
                "button_id": "show_weather_on_idle", 
                "state_condition": show_weather_on_idle, 
            },
            {
                "button_id": "verify_ssl_on_trusted_sources", 
                "state_condition": verify_ssl_on_trusted_sources, 
            },
            {
                "button_id": "media_show_titles", 
                "state_condition": media_show_titles, 
            },
            {
                "button_id": "media_sanitize_titles", 
                "state_condition": media_sanitize_titles, 
            }
        ]
        
        for config in button_configs:
            button_id = config["button_id"]
            state_condition = config["state_condition"]
            action_text = config.get("action_text", "")
            on_text = config.get("on_text", "")
            off_text = config.get("off_text", "")
            available = config.get("available", True)

            for btn in self.buttons:
                button = btn["button"]
                screen = btn["screen"]

                if(button.id==button_id):
                    self.change_button(button,state_condition,action_text,on_text,off_text,available,ignore_screen_update=True)

                for screen_btn in screen:
                    button = screen_btn["button"]
                    if(button.id==button_id):
                        self.change_button(button,state_condition,action_text,on_text,off_text,available,ignore_screen_update=True)

        self.created_and_updated = True
    
    def recalculate_brightness_percentage(self,brightness):
        if brightness > 0:
            return round((brightness/256)*100)
        else:
            return 0

    def change_button(self,button,state_condition,action_text,on_text,off_text,available,ignore_screen_update=False):
        active_color = self.button_color.get("active")
        inactive_color = self.button_color.get("inactive")
        disabled_color = self.button_color.get("disabled")
        button.is_active = state_condition
        if on_text!='' and off_text!='':
            new_text = button.text.replace(action_text, on_text if button.is_active else off_text)
            button.label.configure(text=new_text)
        button.label.configure(bg=disabled_color if not available else active_color if button.is_active else inactive_color)
        logger.debug(f"Button {button.text} is {'active' if button.is_active else 'inactive'}")
        if(ignore_screen_update==False):
            self.main_app.display_controller.force_screen_update()

    def _trace_menu_render(self, event_name):
        if not getattr(self.main_app, "ui_trace_logging", False):
            return
        try:
            button_ids = [btn.get("button").id for btn in self.active_buttons]
        except Exception:
            button_ids = []
        visible_children = 0
        try:
            for child in self.frame.winfo_children():
                if child.winfo_manager() == "grid" and child.winfo_ismapped():
                    visible_children += 1
        except Exception:
            visible_children = -1
        if hasattr(self.main_app, "trace_ui_event"):
            self.main_app.trace_ui_event(
                event_name,
                page=self.current_menu_page,
                max_page=self.max_page,
                active_buttons=button_ids,
                visible_children=visible_children,
            )

    def close_timeout(self,new_timeout=True):
        # Cancel the previously scheduled job, if any
        if self.exit_timeout_future:
            self.frame.after_cancel(self.exit_timeout_future)

        if new_timeout:
            self.exit_timeout_future = self.frame.after(self.exit_timeout_ms, self.exit_menu)

    def exit_menu(self):
        self.in_subpage = False
        self.remove_current_menu()
        self.close_timeout(False)
        self.main_app.exit_menu()
