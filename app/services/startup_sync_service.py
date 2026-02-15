from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.observability.domain_logger import log_event

if TYPE_CHECKING:
    from main import MainApp

logger = logging.getLogger(__name__)


class StartupSyncService:
    """Coordinates startup MQTT sync sequence for required initial state topics."""

    def __init__(self, main_app: MainApp):
        self.main_app = main_app
        self._startup_mqtt_messages = {}
        if self.main_app.is_mqtt_enabled():
            topic_devices = str(getattr(self.main_app.settings, "mqtt_topic_devices", "")).strip()
            topic_music = str(getattr(self.main_app.settings, "mqtt_topic_music", "")).strip()
            if topic_devices:
                self._startup_mqtt_messages[topic_devices] = self.request_device_states
            if topic_music:
                self._startup_mqtt_messages[topic_music] = self.request_music_state
        self.main_app.publish_event("startup.queue.size", {"size": len(self._startup_mqtt_messages)})

    def on_mqtt_connected(self) -> None:
        self.check_queue()

    def check_queue(self, topic: str | None = None) -> None:
        if not self._startup_mqtt_messages:
            return

        if topic:
            processed_queue_item = self._startup_mqtt_messages.pop(topic, None)
            if processed_queue_item is not None:
                log_event(logger, logging.DEBUG, "mqtt", "startup_queue.removed", topic=topic)
            else:
                # Messages can arrive out-of-order or after a topic was already processed.
                # Do not abort queue progression in this case.
                log_event(logger, logging.DEBUG, "mqtt", "startup_queue.remove_missing", topic=topic)

        try:
            next_key, next_handler = next(iter(self._startup_mqtt_messages.items()))
            log_event(
                logger,
                logging.DEBUG,
                "mqtt",
                "startup_queue.next",
                key=next_key,
                handler=str(next_handler),
            )
            next_handler()
        except StopIteration:
            log_event(logger, logging.DEBUG, "mqtt", "startup_queue.empty")

        log_event(logger, logging.DEBUG, "mqtt", "startup_queue.checked", size=len(self._startup_mqtt_messages))
        self.main_app.publish_event("startup.queue.size", {"size": len(self._startup_mqtt_messages)})

    def request_device_states(self) -> None:
        if not self.main_app.is_mqtt_enabled():
            return
        log_event(logger, logging.DEBUG, "mqtt", "state_update.requested")
        self.main_app.mqtt_controller.publish_action("update_device_states")

    def request_music_state(self) -> None:
        if not self.main_app.is_mqtt_enabled():
            return
        log_event(logger, logging.DEBUG, "mqtt", "music_state.requested")
        self.main_app.mqtt_controller.publish_message(
            topic=getattr(self.main_app.settings, "mqtt_topic_update_music", "screen_commands/update_music")
        )
