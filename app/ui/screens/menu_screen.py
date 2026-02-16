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
from PIL import ImageTk

from app.ui.menu_registry import build_menu_buttons
from app.ui.menu_state_resolver import MenuStateResolver
from app.observability.domain_logger import log_event

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
        
        self.buttons = build_menu_buttons(self.main_app.settings)
        self.state_resolver = MenuStateResolver(self.main_app)
        self.button_index = {}

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
        self._build_button_index()
            

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
                log_event(logger, logging.ERROR, "menu", "button.image_missing", error=file_not_found_error)
            except OSError as os_error:
                # Handle OSError (e.g., permission or file system error)
                log_event(logger, logging.ERROR, "menu", "button.image_os_error", error=os_error)
            except Exception as e:
                # Handle other exceptions that may occur
                log_event(logger, logging.ERROR, "menu", "button.image_load_failed", error=e)

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

    def _build_button_index(self):
        self.button_index = {}
        self._index_buttons_recursive(self.buttons)

    def _index_buttons_recursive(self, entries):
        for entry in entries:
            button = entry.get("button")
            if button is not None:
                self.button_index.setdefault(button.id, []).append(button)
            sub_entries = entry.get("screen") or []
            if sub_entries:
                self._index_buttons_recursive(sub_entries)

    def show(self):
        self.in_subpage = False
        self.remove_current_menu()
        self.make_menu_buttons()
        self.update_buttons()
        return True

    def back(self):
        self.in_subpage = False
        self.remove_current_menu()
        self.make_menu_buttons(self.main_page_nr)
        self.update_buttons()
        
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
                log_event(logger, logging.CRITICAL, "menu", "button.label_missing", button_id=button.id)
            
            #label.configure(bg = "white")
            row = i // 2  # Calculate the row (0 or 1)
            col = i % 2   # Calculate the column (0 or 1)
            label.grid(row=row, column=col, padx=self.main_app.settings.menu_button_padding, pady=self.main_app.settings.menu_button_padding, sticky="nsew")

            button_entry = self.active_buttons[i]
            button.bind_down_event = lambda event, button=button: self.handle_button_click(event, button)
            button.bind_up_event = lambda event, button=button, entry=button_entry: self.handle_button_release(event, button, entry)

            # Register a click event for each button
            label.bind("<Button-1>", button.bind_down_event)
            label.bind("<ButtonRelease-1>", button.bind_up_event)

        if(self.main_app.display_controller):
            self.main_app.display_controller.place_action_label(f"{page_nr}/{self.max_page}",anchor="se")
            log_event(logger, logging.DEBUG, "menu", "page.indicator", page=page_nr, max_page=self.max_page)

        self._trace_menu_render("menu.render.complete")

    def enter_submenu(self):
        self.remove_current_menu()
        self.in_subpage = True
        self.main_page_nr = self.current_menu_page
        self.make_menu_buttons(buttons=self.sub_buttons)
        self.update_buttons()

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
        self.update_buttons()
    
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

    def show_fullscreen_qr(self, payload: dict):
        qr_text = self._qr_payload_to_text(payload)
        if not qr_text:
            return

        self.fullscreen_image_window = tk.Toplevel(self.frame)
        if not self.main_app.system_info["is_desktop"]:
            self.fullscreen_image_window.attributes("-fullscreen", True)

        try:
            import qrcode
            qr_image = qrcode.make(qr_text)
            # Scale to fit current screen while preserving sharp edges.
            target = min(max(self.main_app.settings.screen_width, 480), 720)
            qr_image = qr_image.resize((target, target), resample=0)
            qr_photo = ImageTk.PhotoImage(qr_image)
            qr_label = tk.Label(self.fullscreen_image_window, image=qr_photo, bg="black")
            qr_label.image = qr_photo
            qr_label.pack(fill=tk.BOTH, expand=True)
        except Exception:
            log_event(logger, logging.ERROR, "menu", "qr.render_unavailable", reason="missing_qrcode_dependency")
            fallback = tk.Label(
                self.fullscreen_image_window,
                text="QR rendering unavailable.\nInstall package: qrcode\n\n" + qr_text,
                bg="black",
                fg="white",
                justify="center",
                wraplength=int(self.main_app.settings.screen_width * 0.9),
            )
            fallback.pack(fill=tk.BOTH, expand=True)

        self.fullscreen_image_window.bind("<ButtonRelease-1>", self.destroy_fullscreen_image)
        self.fullscreen_image_window.after(self.main_app.settings.destroy_image_timeout, self.destroy_fullscreen_image)

    def _qr_payload_to_text(self, payload: dict) -> str | None:
        qr_type = str(payload.get("type", "")).strip().lower()
        if qr_type == "url":
            url = str(payload.get("url", "")).strip()
            if not url:
                log_event(logger, logging.WARNING, "menu", "qr.url_missing")
                return None
            return url
        if qr_type == "wifi":
            ssid = str(payload.get("ssid", "")).strip()
            password = str(payload.get("password", "")).strip()
            auth = str(payload.get("auth", "WPA")).strip() or "WPA"
            hidden = bool(payload.get("hidden", False))
            if not ssid:
                log_event(logger, logging.WARNING, "menu", "qr.wifi_missing_ssid")
                return None
            return f"WIFI:T:{auth};S:{ssid};P:{password};H:{str(hidden).lower()};;"
        log_event(logger, logging.WARNING, "menu", "qr.unsupported_type", qr_type=qr_type)
        return None

    def destroy_fullscreen_image(self, event=None):
        if self.fullscreen_image_window is not None:
            self.fullscreen_image_window.destroy()
            self.fullscreen_image_window = None

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
    def handle_button_click(self, event, button):
        self.click_x = event.x_root
        self.click_y = event.y_root
        # Record the time of the initial click
        self.button_click_time = time.time()
        button.label.configure(highlightthickness=self.main_app.settings.menu_border_thickness)
        self.close_timeout()
        return "break"

    # Define a method to handle button clicks
    def handle_button_release(self, event, button, button_entry):
        try:
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
                log_event(logger, logging.DEBUG, "menu", "gesture.swipe_detected", min_movement=min_movement, movement=max_movement)
                # Consume menu widget event and route swipe explicitly so root handlers
                # do not need to receive this event.
                x_abs = abs(x_dir)
                y_abs = abs(y_dir)
                if x_abs > y_abs and x_dir > min_movement:
                    self.main_app.interaction_service.handle("left")
                elif x_abs > y_abs and x_dir < -min_movement:
                    self.main_app.interaction_service.handle("right")
                elif x_abs < y_abs and y_dir > min_movement:
                    self.main_app.interaction_service.handle("down")
                elif x_abs < y_abs and y_dir < -min_movement:
                    self.main_app.interaction_service.handle("up")
                return "break"

            sub_button_amount = 0

            if(not self.in_subpage):
                self.sub_buttons = button_entry.get("screen") or []
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
        finally:
            # Never carry touch capture state across button interactions.
            self.button_click_time = None
            self.click_x = None
            self.click_y = None

    def handle_button_hold(self, button, time_held):
        log_event(
            logger,
            logging.DEBUG,
            "menu",
            "button.hold",
            hold_threshold=self.main_app.settings.hold_time,
            held_seconds=time_held,
            action=button.action,
        )
        self.main_app.touch_controller.handle_alt_menu_button(button.action)

    def update_buttons(self):
        for config in self.state_resolver.resolve():
            button_id = config["button_id"]
            state_condition = config["active"]
            action_text = config.get("action_text", "")
            on_text = config.get("on_text", "")
            off_text = config.get("off_text", "")
            available = config.get("available", True)
            for button in self.button_index.get(button_id, []):
                self.change_button(button,state_condition,action_text,on_text,off_text,available,ignore_screen_update=True)

        self.created_and_updated = True

    def change_button(self,button,state_condition,action_text,on_text,off_text,available,ignore_screen_update=False):
        active_color = self.button_color.get("active")
        inactive_color = self.button_color.get("inactive")
        disabled_color = self.button_color.get("disabled")
        button.is_active = state_condition
        if on_text!='' and off_text!='':
            new_text = button.text.replace(action_text, on_text if button.is_active else off_text)
            button.label.configure(text=new_text)
        button.label.configure(bg=disabled_color if not available else active_color if button.is_active else inactive_color)
        log_event(
            logger,
            logging.DEBUG,
            "menu",
            "button.state",
            button_text=button.text,
            active=button.is_active,
            available=available,
        )
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
        self.main_app.screen_state_controller.exit_menu()
