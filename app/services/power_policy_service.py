from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.observability.domain_logger import log_event

if TYPE_CHECKING:
    from main import MainApp

logger = logging.getLogger(__name__)


class PowerPolicyService:
    """Owns in-bed synchronization and idle wake/sleep timer policy."""

    def __init__(self, main_app: MainApp):
        self.main_app = main_app
        self._bed_time_timeout_future = None

    def check_bed_time(self, force: bool = False) -> None:
        in_bed_before = bool(getattr(self.main_app.device_states, "in_bed", False))
        display_before = self.main_app.display_controller.get_screen_state()
        showing_before = bool(getattr(self.main_app.display_controller, "is_showing", False))
        if self.main_app.device_states.in_bed_changed or force:
            if self.main_app.device_states.in_bed:
                self.main_app.display_controller.turn_off()
            else:
                self.main_app.display_controller.turn_on()
            self.main_app.device_states.in_bed_changed = False

        self.main_app.display_controller.check_idle()
        log_event(
            logger,
            logging.INFO,
            "display",
            "power.sync_with_in_bed",
            force=bool(force),
            in_bed=in_bed_before,
            screen_before=display_before,
            showing_before=showing_before,
            showing_after=bool(getattr(self.main_app.display_controller, "is_showing", False)),
            screen_after=self.main_app.display_controller.get_screen_state(),
        )

    def check_idle_timer(self, startnew: bool = True) -> None:
        if self._bed_time_timeout_future:
            self.main_app.root.after_cancel(self._bed_time_timeout_future)

        if startnew:
            self._bed_time_timeout_future = self.main_app.root.after(
                self.main_app.settings.in_bed_turn_off_timeout,
                lambda: self.check_bed_time(True),
            )
