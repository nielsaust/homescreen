from __future__ import annotations

import signal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import MainApp


class AppLifecycleService:
    """Owns runtime startup ordering for the app loop."""

    def __init__(self, main_app: MainApp):
        self.main_app = main_app

    def start(self) -> None:
        self.main_app.touch_controller.bind_events(self.main_app.root)
        signal.signal(signal.SIGINT, self.main_app.signal_handler)
        self.main_app.screen_state_controller.switch_to_idle()
        self.main_app.queue_pump_service.start_mqtt_queue_pump()
        self.main_app.queue_pump_service.start_ui_intent_pump()
        self.main_app.network_bootstrap_service.start_network_status_poll()
        self.main_app.music_metrics_service.start_logging()
        self.main_app.network_bootstrap_service.maybe_init_mqtt_if_online()
