from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import MainApp

logger = logging.getLogger(__name__)


class ScreenStateController:
    """Coordinates high-level screen transition decisions."""

    def __init__(self, main_app: MainApp):
        self.main_app = main_app

    def switch_to_idle(self, force=False):
        show_weather = bool(self.main_app.settings.show_weather_on_idle)
        self.main_app.publish_event(
            "ui.screen.changed",
            {
                "screen": "weather" if show_weather else "off",
                "is_display_on": show_weather,
                "force": bool(force),
            },
            source="screen_state_controller",
        )

    def switch_to_music(self, force=False):
        if self.main_app.display_controller.get_screen_state() == "menu" and not force:
            return
        self.main_app.publish_event(
            "ui.screen.changed",
            {"screen": "music", "is_display_on": True, "force": bool(force)},
            source="screen_state_controller",
        )
        logger.debug(
            "Switch_to_music, current screen: %s",
            self.main_app.display_controller.get_screen_state(),
        )

    def switch_to_menu(self):
        if self.main_app.display_controller.menu_ready():
            self.main_app.publish_event(
                "ui.screen.changed",
                {"screen": "menu", "is_display_on": True, "force": False},
                source="screen_state_controller",
            )
            logger.debug("Menu ready; show menu")
            return
        logger.warning("Menu NOT ready; show idle instead")
        self.switch_to_idle()

    def exit_menu(self):
        music_object = self.main_app.music_object
        if music_object is not None and music_object.state == "playing":
            self.switch_to_music(True)
            return
        self.switch_to_idle()
