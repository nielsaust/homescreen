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

    def _is_music_enabled(self):
        if hasattr(self.main_app, "is_music_enabled"):
            return bool(self.main_app.is_music_enabled())
        return bool(getattr(self.main_app.settings, "enable_music", True))

    def _is_weather_enabled(self):
        if hasattr(self.main_app, "is_weather_enabled"):
            return bool(self.main_app.is_weather_enabled())
        return bool(getattr(self.main_app.settings, "enable_weather", True))

    def switch_to_idle(self, force=False):
        if hasattr(self.main_app, "is_any_feature_enabled") and not self.main_app.is_any_feature_enabled():
            self.main_app.publish_event(
                "ui.screen.changed",
                {
                    "screen": "setup",
                    "is_display_on": True,
                    "force": bool(force),
                },
                source="screen_state_controller",
            )
            return

        show_weather = bool(self.main_app.settings.show_weather_on_idle) and self._is_weather_enabled()
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
        if not self._is_music_enabled():
            logger.debug("switch_to_music ignored; enable_music=false")
            return
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
        if not self.main_app.display_controller.menu_ready():
            logger.warning("Menu NOT ready yet; showing menu with current/default state")
        self.main_app.publish_event(
            "ui.screen.changed",
            {"screen": "menu", "is_display_on": True, "force": False},
            source="screen_state_controller",
        )

    def exit_menu(self):
        music_object = self.main_app.music_object
        if music_object is not None and music_object.state == "playing":
            self.switch_to_music(True)
            return
        self.switch_to_idle()
