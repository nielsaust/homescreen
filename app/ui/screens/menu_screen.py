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
from app.ui.menu_config_loader import load_menu_config, save_local_menu_config
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

        self.edit_mode = False
        self.edit_mode_hold_seconds = 1.2
        self.edit_indicator_press_at = None
        self.edit_indicator_hold_after_id = None
        self.edit_selected_button_id = None
        self.edit_dirty_paths = set()
        self.edit_topbar = None
        self.edit_up_btn = None
        self.edit_down_btn = None
        self.page_indicator_label = None
        self.current_button_path = []
        self.current_buttons_ref = self.buttons

        self._create_buttons_recursive(self.buttons)
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

    def _create_buttons_recursive(self, entries):
        self.create_buttons(entries)
        for entry in entries:
            children = entry.get("screen") or []
            if children:
                self._create_buttons_recursive(children)

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
        self.current_button_path = []
        self.current_buttons_ref = self.buttons
        self.remove_current_menu()
        self.make_menu_buttons()
        self.update_buttons()
        return True

    def back(self):
        self.in_subpage = False
        self.current_button_path = []
        self.current_buttons_ref = self.buttons
        self.remove_current_menu()
        self.make_menu_buttons(self.main_page_nr)
        self.update_buttons()
        
    def make_menu_buttons(self,page_nr=1,buttons=None):
        self.close_timeout()
        self.current_menu_page = page_nr
        if buttons is None:
            buttons = self.current_buttons_ref
        else:
            self.current_buttons_ref = buttons

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
            label.configure(highlightthickness=0)
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

        if self.page_indicator_label is not None:
            try:
                self.page_indicator_label.destroy()
            except Exception:
                pass
            self.page_indicator_label = None

        if(self.main_app.display_controller):
            indicator_timeout_ms = 0 if self.edit_mode else None
            indicator_label = self.main_app.display_controller.place_action_label(
                f"{page_nr}/{self.max_page}",
                anchor="se",
                timeout_ms=indicator_timeout_ms,
            )
            if indicator_label is not None:
                self.page_indicator_label = indicator_label
                indicator_label.bind("<Button-1>", self._handle_indicator_down)
                indicator_label.bind("<ButtonRelease-1>", self._handle_indicator_up)
            log_event(logger, logging.DEBUG, "menu", "page.indicator", page=page_nr, max_page=self.max_page)

        self._render_edit_topbar()
        self._trace_menu_render("menu.render.complete")

    def enter_submenu(self, button_entry=None):
        self.remove_current_menu()
        self.in_subpage = True
        self.main_page_nr = self.current_menu_page
        if button_entry is not None:
            button = button_entry.get("button")
            button_id = getattr(button, "id", None)
            if button_id:
                self.current_button_path = self.current_button_path + [button_id]
            self.current_buttons_ref = button_entry.get("screen") or []
        self.make_menu_buttons(buttons=self.current_buttons_ref)
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
            buttons = self.current_buttons_ref

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
            # Toplevel overlays (e.g. QR window) are not managed by grid/pack.
            if isinstance(child, tk.Toplevel):
                child.destroy()
                continue
            manager = child.winfo_manager()
            if manager == "grid":
                child.grid_forget()
            elif manager == "pack":
                child.pack_forget()
            elif manager == "place":
                child.place_forget()

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
        if self.edit_mode:
            return "break"
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
            if self.edit_mode:
                self._select_button_for_edit(button)
                return "break"

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
                sub_buttons = button_entry.get("screen") or []
                sub_button_amount = len(sub_buttons)

            if self.button_click_time is not None:
                release_time = time.time()
                time_elapsed = release_time - self.button_click_time

                if time_elapsed >= self.main_app.settings.hold_time:
                    self.handle_button_hold(button,time_elapsed)
                elif(sub_button_amount>0):
                    self.enter_submenu(button_entry=button_entry)
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
        if self.edit_mode:
            self._apply_edit_selection_highlight()
            return
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

    def _can_use_edit_mode(self):
        env = str(getattr(self.main_app.settings, "app_environment", "production") or "production").strip().lower()
        return env not in {"production", "prod"}

    def _menu_edit_hold_ms(self):
        raw = getattr(self.main_app.settings, "menu_edit_hold_ms", 1200)
        try:
            return max(200, int(raw))
        except (TypeError, ValueError):
            return 1200

    def _handle_indicator_down(self, _event):
        self.edit_indicator_press_at = time.time()
        if self.main_app.display_controller and self.page_indicator_label is not None:
            self.main_app.display_controller.hold_action_label(self.page_indicator_label)
        if self.edit_indicator_hold_after_id is not None:
            try:
                self.frame.after_cancel(self.edit_indicator_hold_after_id)
            except Exception:
                pass
            self.edit_indicator_hold_after_id = None

        hold_ms = self._menu_edit_hold_ms()
        self.edit_indicator_hold_after_id = self.frame.after(hold_ms, self._activate_edit_mode_from_hold)
        return "break"

    def _handle_indicator_up(self, _event):
        try:
            if not self._can_use_edit_mode():
                return "break"
            if self.edit_mode:
                return "break"
        finally:
            if self.edit_indicator_hold_after_id is not None:
                try:
                    self.frame.after_cancel(self.edit_indicator_hold_after_id)
                except Exception:
                    pass
                self.edit_indicator_hold_after_id = None
            if (not self.edit_mode) and self.main_app.display_controller and self.page_indicator_label is not None:
                self.main_app.display_controller.release_action_label(self.page_indicator_label)
            self.edit_indicator_press_at = None
        return "break"

    def _activate_edit_mode_from_hold(self):
        self.edit_indicator_hold_after_id = None
        if not self._can_use_edit_mode():
            return
        if self.edit_indicator_press_at is None:
            return
        if self.edit_mode:
            return
        self._enter_edit_mode()

    def _enter_edit_mode(self):
        self.edit_mode = True
        self.edit_selected_button_id = None
        self.edit_dirty_paths = set()
        self.close_timeout(False)
        self.make_menu_buttons(self.current_menu_page, self.current_buttons_ref)
        self.update_buttons()
        log_event(logger, logging.INFO, "menu", "edit_mode.enter")

    def _exit_edit_mode(self, save=False):
        if save:
            self._persist_menu_order_changes()
        else:
            self._reload_buttons_from_config()
        self.edit_mode = False
        self.edit_selected_button_id = None
        self.edit_dirty_paths = set()
        self._clear_all_button_selection_highlights()
        if self.main_app.display_controller and self.page_indicator_label is not None:
            self.main_app.display_controller.release_action_label(self.page_indicator_label)
        self.remove_current_menu()
        self.make_menu_buttons(self.current_menu_page, self.current_buttons_ref)
        self.update_buttons()
        self.close_timeout()
        log_event(logger, logging.INFO, "menu", "edit_mode.exit", saved=bool(save))

    def _reload_buttons_from_config(self):
        self.buttons = build_menu_buttons(self.main_app.settings)
        self._create_buttons_recursive(self.buttons)
        self._build_button_index()
        restored = self._get_entries_by_path(self.current_button_path)
        if restored is None:
            self.current_button_path = []
            self.current_buttons_ref = self.buttons
            self.in_subpage = False
        else:
            self.current_buttons_ref = restored
            self.in_subpage = bool(self.current_button_path)

    def _select_button_for_edit(self, button):
        if button.action == "back":
            self.edit_selected_button_id = None
            self._render_edit_topbar()
            self._apply_edit_selection_highlight()
            return
        self.edit_selected_button_id = button.id
        self._render_edit_topbar()
        self._apply_edit_selection_highlight()

    def _apply_edit_selection_highlight(self):
        self.update_buttons_nonselected_inactive()
        if not self.edit_selected_button_id:
            return
        for entry in self.current_buttons_ref:
            candidate = entry.get("button")
            if candidate and candidate.id == self.edit_selected_button_id and candidate.label:
                candidate.label.configure(
                    bg=self.button_color.get("inactive"),
                    highlightbackground=self.button_color.get("down"),
                    highlightthickness=max(4, int(self.main_app.settings.menu_border_thickness)),
                )
                break

    def update_buttons_nonselected_inactive(self):
        for entry in self.active_buttons:
            button = entry.get("button")
            if button and button.label:
                button.label.configure(
                    bg=self.button_color.get("inactive"),
                    highlightthickness=0,
                )

    def _clear_all_button_selection_highlights(self):
        for buttons in self.button_index.values():
            for button in buttons:
                if button and button.label:
                    button.label.configure(highlightthickness=0)

    def _selected_entry_in_current_level(self):
        if not self.edit_selected_button_id:
            return None, -1
        for idx, entry in enumerate(self.current_buttons_ref):
            button = entry.get("button")
            if button and button.id == self.edit_selected_button_id:
                return entry, idx
        return None, -1

    def _move_selected(self, delta):
        entry, idx = self._selected_entry_in_current_level()
        if entry is None:
            return
        button = entry.get("button")
        if button and button.action == "back":
            return
        target_idx = idx + delta
        if target_idx < 0 or target_idx >= len(self.current_buttons_ref):
            return
        if target_idx != 0:
            target_entry = self.current_buttons_ref[target_idx]
            target_button = target_entry.get("button")
            if target_button and target_button.action == "back":
                return
        # Back button stays pinned at the first slot for submenu levels.
        if idx == 0 and button and button.action == "back":
            return

        moving_entry = self.current_buttons_ref.pop(idx)
        self.current_buttons_ref.insert(target_idx, moving_entry)
        self.edit_dirty_paths.add(tuple(self.current_button_path))

        selected_index = target_idx
        self.current_menu_page = max(1, math.floor(selected_index / self.num_active_buttons) + 1)
        self.remove_current_menu()
        self.make_menu_buttons(self.current_menu_page, self.current_buttons_ref)
        self._render_edit_topbar()
        self._apply_edit_selection_highlight()

    def _render_edit_topbar(self):
        if self.edit_topbar is not None:
            self.edit_topbar.destroy()
            self.edit_topbar = None
            self.edit_up_btn = None
            self.edit_down_btn = None

        if not self.edit_mode:
            return

        bar = tk.Frame(self.frame, bg=self.frame.cget("bg"))
        bar.place(relx=0.5, rely=0.02, anchor=tk.N)
        self.edit_topbar = bar

        has_selection = self._selected_entry_in_current_level()[0] is not None

        self.edit_up_btn = self._make_edit_topbar_button(
            bar,
            text="◀",
            command=lambda: self._move_selected(-1),
            enabled=has_selection,
        )
        self.edit_up_btn.pack(side=tk.LEFT, padx=0)

        cancel_btn = self._make_edit_topbar_button(
            bar,
            text="Cancel",
            command=lambda: self._exit_edit_mode(save=False),
            enabled=True,
        )
        cancel_btn.pack(side=tk.LEFT, padx=0)

        save_btn = self._make_edit_topbar_button(
            bar,
            text="Save",
            command=lambda: self._exit_edit_mode(save=True),
            enabled=True,
        )
        save_btn.pack(side=tk.LEFT, padx=0)

        self.edit_down_btn = self._make_edit_topbar_button(
            bar,
            text="▶",
            command=lambda: self._move_selected(1),
            enabled=has_selection,
        )
        self.edit_down_btn.pack(side=tk.LEFT, padx=0)

    def _make_edit_topbar_button(self, parent, text, command, enabled=True):
        label = tk.Label(
            parent,
            text=text,
            bg="black",
            fg="white" if enabled else "#888888",
            font=("Helvetica", 18, "bold"),
            padx=16,
            pady=16,
            width=5,
            bd=0,
            highlightthickness=0,
        )
        if enabled:
            label.bind("<ButtonRelease-1>", lambda _evt: command())
        return label

    def _get_entries_by_path(self, path_ids):
        entries = self.buttons
        for node_id in path_ids:
            next_entry = None
            for entry in entries:
                button = entry.get("button")
                if button and button.id == node_id:
                    next_entry = entry
                    break
            if next_entry is None:
                return None
            entries = next_entry.get("screen") or []
        return entries

    def _get_schema_container(self, menu_schema, path_ids):
        container = menu_schema
        for node_id in path_ids:
            next_entry = None
            for entry in container:
                if str(entry.get("id", "")) == str(node_id):
                    next_entry = entry
                    break
            if next_entry is None:
                return None
            container = next_entry.get("screen") or []
        return container

    def _persist_menu_order_changes(self):
        if not self.edit_dirty_paths:
            return
        config = load_menu_config()
        menu_schema = config.get("menu_schema", [])
        if not isinstance(menu_schema, list):
            return
        for path in self.edit_dirty_paths:
            runtime_container = self._get_entries_by_path(list(path))
            local_container = self._get_schema_container(menu_schema, list(path))
            if runtime_container is None or local_container is None:
                continue
            runtime_ids = [entry.get("button").id for entry in runtime_container if entry.get("button") is not None]
            by_id = {str(item.get("id", "")): item for item in local_container}
            for idx, item_id in enumerate(runtime_ids):
                match = by_id.get(str(item_id))
                if match is None:
                    continue
                match["order"] = (idx + 1) * 10
        config["menu_schema"] = menu_schema
        save_local_menu_config(config)

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

        if new_timeout and not self.edit_mode:
            self.exit_timeout_future = self.frame.after(self.exit_timeout_ms, self.exit_menu)

    def exit_menu(self):
        if self.edit_mode:
            self.edit_mode = False
            self.edit_selected_button_id = None
            self.edit_dirty_paths = set()
        self.in_subpage = False
        self.current_button_path = []
        self.current_buttons_ref = self.buttons
        self.remove_current_menu()
        if self.page_indicator_label is not None:
            try:
                self.page_indicator_label.destroy()
            except Exception:
                pass
            self.page_indicator_label = None
        self.close_timeout(False)
        self.main_app.screen_state_controller.exit_menu()
