from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from app.observability.domain_logger import log_event

if TYPE_CHECKING:
    from main import MainApp

logger = logging.getLogger(__name__)


class InteractionService:
    """Handles touch/gesture interaction behavior by current UI screen state."""

    def __init__(self, main_app: MainApp):
        self.main_app = main_app

    def handle(self, interaction_type: str) -> None:
        self.main_app.publish_event("interaction.received", {"interaction_type": interaction_type})
        log_event(logger, logging.DEBUG, "ui", "interaction.received", interaction_type=interaction_type)
        current_time = time.time()

        if self._should_ignore_click(interaction_type, current_time):
            return
        if self.main_app.display_controller.is_cam_showing():
            log_event(logger, logging.DEBUG, "ui", "interaction.ignored", reason="camera_overlay_active")
            return
        if self._is_rate_limited(current_time):
            return

        self.main_app.time_last_action = current_time
        screen_state = self.main_app.display_controller.get_screen_state()

        self.main_app.power_policy_service.check_idle_timer()
        if self._handle_display_wake(screen_state, interaction_type):
            return

        if screen_state is not None:
            self._route_by_screen(screen_state, interaction_type)
            self.main_app.print_memory_usage()
            return

        # Startup fallback: if screen state has not been applied yet, keep single-tap responsive.
        if interaction_type == "single_click":
            self.main_app.screen_state_controller.switch_to_menu()
            self.main_app.print_memory_usage()

    def _should_ignore_click(self, interaction_type: str, current_time: float) -> bool:
        touch = self.main_app.touch_controller
        if (
            interaction_type == "single_click"
            and touch.ignore_next_click
            and current_time <= getattr(touch, "ignore_click_until", 0.0)
        ):
            log_event(logger, logging.DEBUG, "ui", "interaction.ignored", reason="menu_click_already_handled")
            touch.ignore_next_click = False
            return True
        if current_time > getattr(touch, "ignore_click_until", 0.0):
            touch.ignore_next_click = False
        return False

    def _is_rate_limited(self, current_time: float) -> bool:
        time_between_actions = current_time - self.main_app.time_last_action
        if time_between_actions < self.main_app.settings.min_time_between_actions:
            log_event(
                logger,
                logging.WARNING,
                "ui",
                "interaction.rejected.rate_limit",
                time_between_actions=time_between_actions,
                min_interval=self.main_app.settings.min_time_between_actions,
            )
            return True
        return False

    def _handle_display_wake(self, screen_state: str | None, interaction_type: str) -> bool:
        if self.main_app.display_controller.is_showing:
            return False

        sleep_mode_active = bool(getattr(self.main_app.device_states, "sleep_mode", False))
        # Keep first tap responsive from idle/off/setup: go straight to menu flow.
        if not sleep_mode_active and interaction_type == "single_click" and screen_state in ("off", "setup", "weather"):
            return False

        if (
            self.main_app.settings.show_weather_on_idle
            and hasattr(self.main_app, "is_weather_enabled")
            and self.main_app.is_weather_enabled()
            and screen_state == "off"
        ):
            self.main_app.display_controller.check_idle(True)
            return True
        if sleep_mode_active:
            # In sleep mode, first tap only wakes the display.
            # A second tap is required to open the menu.
            self.main_app.display_controller.check_idle(True)
            return True

        # Keep interaction responsive when display state is temporarily out-of-sync.
        self.main_app.display_controller.turn_on()
        return False

    def _route_by_screen(self, screen_state: str, interaction_type: str) -> None:
        if screen_state in ("weather", "off", "setup", "status_check"):
            if interaction_type == "single_click":
                self.main_app.screen_state_controller.switch_to_menu()
            return

        if screen_state == "music":
            if interaction_type == "single_click":
                self.main_app.screen_state_controller.switch_to_menu()
            elif interaction_type == "hold":
                self.main_app.media_controller.media_play_pause()
            elif interaction_type == "left":
                self.main_app.media_controller.media_skip_song("previous")
            elif interaction_type == "right":
                self.main_app.media_controller.media_skip_song("next")
            elif interaction_type == "up":
                self.main_app.media_controller.media_volume("up")
            elif interaction_type == "down":
                self.main_app.media_controller.media_volume("down")
            return

        if screen_state == "menu":
            if interaction_type == "left":
                self.main_app.publish_event(
                    "menu.navigation.requested",
                    {"command": "page_prev"},
                    source="gesture",
                )
            elif interaction_type == "right":
                self.main_app.publish_event(
                    "menu.navigation.requested",
                    {"command": "page_next"},
                    source="gesture",
                )
            elif interaction_type == "down":
                self.main_app.publish_event(
                    "menu.navigation.requested",
                    {"command": "exit"},
                    source="gesture",
                )
