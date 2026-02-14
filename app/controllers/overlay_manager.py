import logging

logger = logging.getLogger(__name__)


class OverlayManager:
    def __init__(self, main_app):
        self.main_app = main_app
        self._create_overlay_screens()

    def _create_overlay_screens(self):
        from app.ui.screens.cam_screen import CamScreen
        from app.ui.screens.calendar_screen import CalendarScreen
        from app.ui.screens.print_screen import PrintScreen
        from app.ui.screens.slideshow import SlideShow
        from app.ui.screens.alert_screen import AlertScreen

        self.cam_screen = CamScreen(self.main_app)
        self.calendar_screen = CalendarScreen(self.main_app)
        self.print_screen = PrintScreen(self.main_app)
        self.slideshow = SlideShow(self.main_app)
        self.alert_screen = AlertScreen(self.main_app)

    def close_open_windows(self):
        self.print_screen.destroy()
        self.cam_screen.destroy()
        self.calendar_screen.destroy()
        self.alert_screen.destroy()
        self.slideshow.destroy()
        self._reset_touch_input_state()

    def _reset_touch_input_state(self):
        touch = getattr(self.main_app, "touch_controller", None)
        if touch is None:
            return
        touch.click_time = None
        touch.start_x = 0
        touch.start_y = 0
        touch.ignore_next_click = False
        touch.ignore_click_until = 0.0

    def open_slideshow(self):
        if self.slideshow:
            self.close_open_windows()
            self.slideshow.show()

    def show_cam(self, data, url, username=None, password=None):
        if self.cam_screen:
            self.close_open_windows()
            self.cam_screen.show(data, url, username, password)

    def show_calendar(self, data):
        if self.calendar_screen:
            self.close_open_windows()
            self.calendar_screen.show(data)

    def show_alert(self, data):
        logger.debug(f"show_alert(data: {data})")
        if self.alert_screen:
            self.close_open_windows()
            self.alert_screen.show(data)

    def close_alert_screen(self):
        if self.alert_screen:
            self.alert_screen.destroy()

    def show_print_status(self, progress, reset=False):
        if self.print_screen and progress is not None:
            self.close_open_windows()
            self.print_screen.show(progress)
            if reset:
                self.print_screen.cancel_blink()

    def close_print_screen(self):
        if self.print_screen:
            self.print_screen.destroy()

    def update_print_progress(self, progress):
        if self.print_screen and self.print_screen.is_showing:
            self.print_screen.update(progress)

    def print_screen_attention(self):
        if self.print_screen and self.main_app.settings.printer_screen_blink_on_complete:
            self.print_screen.blink_percentage()

    def cancel_attention(self):
        if self.print_screen and self.print_screen.is_blinking:
            self.print_screen.cancel_blink()

    def is_cam_showing(self):
        return bool(self.cam_screen and self.cam_screen.is_showing)
