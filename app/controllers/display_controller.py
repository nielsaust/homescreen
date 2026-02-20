import logging
logger = logging.getLogger(__name__)

import time
import tkinter as tk
from app.hardware.hyperpixel_backlight import Backlight
from app.controllers.overlay_commands import OverlayCommand
from app.controllers.overlay_manager import OverlayManager
from app.ui.ui_render_service import UiRenderService
from app.observability.domain_logger import log_event

class DisplayController:
    def __init__(self, main_app):
        self.main_app = main_app
        self.previous_screen = None
        self.current_screen = None
        self._screen_state = None
        self.screens = {}
        self.screen_objects = {}

        # Create screens
        self.music_screen = None
        self.menu_screen = None
        # switching/state screens
        self._create_base_screens()

        self.overlay_manager = OverlayManager(self.main_app)
        self.ui_render = UiRenderService(self.main_app)

        self.time_in_screen = time.time() - 1000 # offset for start

        # display options for Pi Screen
        self.backlight = None
        self.is_showing = False
        self._sleep_mode_user_wake_active = False
        if(not self.main_app.system_info["is_desktop"]):
            self.backlight = Backlight()
            self._apply_kiosk_window_mode()
            # Some Pi desktop/session combinations briefly override window flags
            # during startup; retry a few times to keep kiosk fullscreen stable.
            for delay_ms in (150, 600, 2000):
                self.main_app.root.after(delay_ms, self._apply_kiosk_window_mode)

    def _apply_kiosk_window_mode(self):
        try:
            screen_w = int(self.main_app.root.winfo_screenwidth())
            screen_h = int(self.main_app.root.winfo_screenheight())
            self.main_app.root.geometry(f"{screen_w}x{screen_h}+0+0")
            self.main_app.root.attributes("-fullscreen", True)
            self.main_app.root.lift()
            self.main_app.root.focus_force()
            log_event(
                logger,
                logging.DEBUG,
                "display",
                "window.kiosk_applied",
                width=screen_w,
                height=screen_h,
            )
        except Exception as exc:
            log_event(logger, logging.WARNING, "display", "window.kiosk_apply_failed", error=exc)

    def force_kiosk_window_mode(self):
        self._apply_kiosk_window_mode()

    def _create_base_screens(self):
        for screen_name in ("off", "setup", "weather", "music", "menu", "network_check"):
            self.create_screen(screen_name)

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
        elif screen_name == "setup":
            from app.ui.screens.setup_required_screen import SetupRequiredScreen
            screen_object = SetupRequiredScreen(self.main_app, screen_frame)
        elif screen_name == "weather":         
            from app.ui.screens.weather_screen import WeatherScreen
            screen_object = WeatherScreen(self.main_app,screen_frame,self.main_app.settings.weather_api_key, self.main_app.settings.weather_city_id, self.main_app.settings.language)
        elif screen_name == "music":
            from app.ui.screens.music_screen import MusicScreen
            screen_object = MusicScreen(self.main_app,screen_frame)
        elif screen_name == "menu":
            from app.ui.screens.menu_screen import MenuScreen
            screen_object = MenuScreen(self.main_app,screen_frame)
        elif screen_name == "network_check":
            from app.ui.screens.network_check_screen import NetworkCheckScreen
            screen_object = NetworkCheckScreen(self.main_app, screen_frame)
        
        # Store the screen frame in the dictionary
        self.screens[screen_name] = screen_frame
        self.screen_objects[screen_name] = screen_object

    def exit_menu(self):
        menu_screen = self.screen_objects.get("menu")
        if(menu_screen):
            menu_screen.exit_menu()

    def close_open_windows(self):
        self.overlay_manager.close_open_windows()

    def show_fullscreen_image(self, image):
        menu_screen = self.screen_objects.get("menu")
        if(menu_screen):
            menu_screen.show_fullscreen_image(image)

    def show_fullscreen_qr(self, payload):
        menu_screen = self.screen_objects.get("menu")
        if menu_screen:
            menu_screen.show_fullscreen_qr(payload)

    def open_slideshow(self):
        self.overlay_manager.open_slideshow()

    def show_cam(self, data, url, username=None, password=None):
        self.overlay_manager.show_cam(data, url, username, password)
        self.check_idle(True)

    def show_calendar(self,data):
        self.overlay_manager.show_calendar(data)
        self.check_idle(True)

    def show_alert(self, data):
        """
        Wrapper around AlertScreen.show()
        Allows showing alerts directly with simple params.
        """
        log_event(logger, logging.DEBUG, "display", "overlay.alert.show", has_data=bool(data))

        self.overlay_manager.show_alert(data)
        self.check_idle(True)

    def close_alert_screen(self):
        self.overlay_manager.close_alert_screen()

    def show_print_status(self,progress,reset=False):
        self.overlay_manager.show_print_status(progress, reset)
        if progress is not None:
            self.check_idle(True)

    def close_print_screen(self):
        self.overlay_manager.close_print_screen()

    def update_print_progress(self,progress):
        self.overlay_manager.update_print_progress(progress)

    def print_screen_attention(self):
        self.overlay_manager.print_screen_attention()

    def cancel_attention(self):
        self.overlay_manager.cancel_attention()

    @property
    def cam_screen(self):
        return self.overlay_manager.cam_screen

    def is_cam_showing(self):
        return self.overlay_manager.is_cam_showing()

    def handle_overlay_command(self, command, payload):
        if command == OverlayCommand.OPEN_SLIDESHOW:
            self.open_slideshow()
            return True
        if command == OverlayCommand.SHOW_CAM:
            self.show_cam(
                payload.get("data") or {},
                payload.get("url"),
                payload.get("username"),
                payload.get("password"),
            )
            return True
        if command == OverlayCommand.SHOW_CALENDAR:
            self.show_calendar(payload.get("data") or {})
            return True
        if command == OverlayCommand.SHOW_ALERT:
            self.show_alert(payload.get("data") or {})
            return True
        if command == OverlayCommand.SHOW_PRINT_STATUS:
            self.show_print_status(
                payload.get("progress"),
                bool(payload.get("reset", False)),
            )
            return True
        if command == OverlayCommand.UPDATE_PRINT_PROGRESS:
            self.update_print_progress(payload.get("progress"))
            return True
        if command == OverlayCommand.PRINT_SCREEN_ATTENTION:
            self.print_screen_attention()
            return True
        if command == OverlayCommand.CLOSE_PRINT_SCREEN:
            self.close_print_screen()
            return True
        if command == OverlayCommand.CANCEL_ATTENTION:
            self.cancel_attention()
            return True
        return False

    def show_show_slider(self,entity,title,type="light"):
        self.stop_menu_timer()
        from app.ui.screens.slider_screen import SliderScreen
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
        previous_state = self._screen_state
        self._trace_ui(
            "screen.show.request",
            screen=screen_name,
            force=force,
            current=self.get_screen_state(),
            time_between_switches=round(time_between_switches, 4),
        )
        log_event(
            logger,
            logging.DEBUG,
            "display",
            "screen.show.request",
            screen=screen_name,
            time_between_switches=round(time_between_switches, 4),
            force=bool(force),
        )
        if self._should_block_screen_switch(time_between_switches, force, screen_name):
            return

        self._screen_state = screen_name
        self._hide_current_screen_for_switch(screen_name)

        # Show the selected screen
        self.previous_screen = self.current_screen
        self.current_screen = self.screens.get(screen_name)
        if self.current_screen is None:
            log_event(logger, logging.ERROR, "display", "screen.current_missing", screen=screen_name)
        elif not self._show_selected_screen(screen_name):
            log_event(logger, logging.WARNING, "display", "screen.show.restore_previous", failed_screen=screen_name)
            self.current_screen = self.previous_screen
            self._screen_state = previous_state
            if self.current_screen is not None:
                try:
                    self.current_screen.pack(fill=tk.BOTH, expand=True)
                except Exception as exc:
                    log_event(logger, logging.ERROR, "display", "screen.restore_previous_failed", error=exc)

        if screen_name != "off":
            self.check_idle()
        self.force_screen_update()
        self._trace_widget_state("screen.after_force_update", self.current_screen)

    def _should_block_screen_switch(self, time_between_switches, force, screen_name):
        if time_between_switches < self.main_app.settings.min_time_between_actions and not force:
            log_event(
                logger,
                logging.WARNING,
                "display",
                "screen.show.blocked_too_fast",
                time_between_switches=round(time_between_switches, 4),
                current_screen=str(self.current_screen),
            )
            self._trace_ui("screen.show.blocked_too_fast", screen=screen_name)
            return True
        return False

    def _hide_current_screen_for_switch(self, screen_name):
        allow_forget = (self.current_screen is not None) and (self.current_screen != self.screens.get(screen_name))
        if allow_forget:
            log_event(logger, logging.DEBUG, "display", "screen.forget", current_screen=str(self.current_screen))
            self._trace_widget_state("screen.before_forget", self.current_screen)
            self.current_screen.pack_forget()
            self._trace_widget_state("screen.after_forget", self.current_screen)
        else:
            log_event(logger, logging.DEBUG, "display", "screen.forget_skipped", reason="already_current")

    def _show_selected_screen(self, screen_name):
        log_event(logger, logging.DEBUG, "display", "screen.show.start", screen=screen_name)
        screen_object = self._get_screen_object(screen_name)
        if screen_object is None:
            log_event(logger, logging.ERROR, "display", "screen.object_missing", screen=screen_name)
            return False

        try:
            log_event(logger, logging.DEBUG, "display", "screen.object_show", screen=screen_name)
            show_ok = bool(screen_object.show())
            self._trace_ui("screen.object.show", screen=screen_name, show_ok=show_ok)
            if not show_ok:
                log_event(logger, logging.ERROR, "display", "screen.object_show_failed", screen=screen_name)
                return False

            log_event(logger, logging.INFO, "display", "screen.show.success", screen=screen_name)
            self.current_screen.pack(fill=tk.BOTH, expand=True)
            self.time_in_screen = time.time()
            self._trace_widget_state("screen.after_pack", self.current_screen)
            self._schedule_trace_widget_state("screen.after_delay", self.current_screen)
            log_event(
                logger,
                logging.DEBUG,
                "display",
                "screen.object_ready",
                screen=screen_name,
                class_name=screen_object.__class__.__name__,
                updated_at=self.time_in_screen,
            )
            return True
        except Exception as e:
            log_event(logger, logging.ERROR, "display", "screen.create_failed", screen=screen_name, error=e)
            return False

    def _get_screen_object(self, screen_name):
        try:
            log_event(logger, logging.DEBUG, "display", "screen.object_get", screen=screen_name)
            return self.screen_objects.get(screen_name)
        except Exception as e:
            log_event(logger, logging.ERROR, "display", "screen.object_get_failed", screen=screen_name, error=e)
            return None

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
        self.ui_render.force_screen_update()

    def _trace_ui(self, event_name, **fields):
        self.ui_render.trace_ui(event_name, **fields)

    def _trace_widget_state(self, event_name, widget):
        self.ui_render.trace_widget_state(event_name, widget)

    def _schedule_trace_widget_state(self, event_name, widget):
        self.ui_render.schedule_trace_widget_state(event_name, widget)

    def place_action_label(self, text=None, anchor="center", image=None, bg='black', fg='white', bordercolor='black', timeout_ms=None): 
        return self.ui_render.place_action_label(text, anchor, image, bg, fg, bordercolor, timeout_ms=timeout_ms)

    def hold_action_label(self, label):
        self.ui_render.hold_action_label(label)

    def release_action_label(self, label, timeout_ms=None):
        self.ui_render.release_action_label(label, timeout_ms=timeout_ms)

    def check_idle(self,turn_on=False):
        screen = self.get_screen_state()
        sleep_mode_active = bool(getattr(self.main_app.device_states, "sleep_mode", False))

        # Explicit wake (tap / user action) starts a temporary wake session while in-bed.
        if turn_on:
            if sleep_mode_active:
                self._sleep_mode_user_wake_active = True
            self.turn_on(user_override=True)
            return

        # While in-bed, allow interaction screens during user wake session only.
        if sleep_mode_active:
            if self._sleep_mode_user_wake_active and screen in ("menu", "music"):
                self.turn_on(user_override=True)
                return
            self._sleep_mode_user_wake_active = False
            self.turn_off()
            return

        # Outside in-bed mode, use normal behavior.
        if screen == "menu":
            self.turn_on()
        elif screen == "music":
            self.turn_on()
        elif screen == "off":
            self.turn_off()
        else:
            self.turn_on()

    def turn_on(self, user_override=False):
        sleep_mode_active = bool(getattr(self.main_app.device_states, "sleep_mode", False))
        if sleep_mode_active and not user_override:
            log_event(logger, logging.INFO, "display", "power.on_skipped", reason="sleep_mode_active")
            self.is_showing = False
            if not self.main_app.system_info["is_desktop"] and self.backlight is not None:
                self.backlight.set_power(False)
            return
        if sleep_mode_active and user_override:
            log_event(logger, logging.INFO, "display", "power.on_user_override", reason="sleep_mode_active")
        log_event(logger, logging.INFO, "display", "power.on")
        self.is_showing = True
        if(not self.main_app.system_info["is_desktop"]):
            self.backlight.set_power(True)

    def turn_off(self):
        log_event(logger, logging.INFO, "display", "power.off")
        self.is_showing = False
        self.close_open_windows()
        if not self.main_app.settings.show_weather_on_idle and self.get_screen_state() != "off":
            self.show_screen("off")
        if(not self.main_app.system_info["is_desktop"]):
            self.backlight.set_power(False)

    # Getter method for screen_state
    def get_screen_state(self):
        return self._screen_state
