from __future__ import annotations

import logging
from queue import Empty
from typing import TYPE_CHECKING

from app.observability.domain_logger import log_event

if TYPE_CHECKING:
    from main import MainApp

logger = logging.getLogger(__name__)


class QueuePumpService:
    """Owns periodic queue pump loops for UI intents and MQTT messages."""

    def __init__(self, main_app: MainApp):
        self.main_app = main_app

    def enqueue_ui_intent(self, intent: dict) -> None:
        self.main_app.ui_intent_queue.put(intent)

    def start_ui_intent_pump(self) -> None:
        self.main_app.root.after(self.main_app.ui_intent_poll_interval_ms, self._pump_ui_intents)

    def _pump_ui_intents(self) -> None:
        handled = 0
        while handled < 100:
            try:
                intent = self.main_app.ui_intent_queue.get_nowait()
            except Empty:
                break
            try:
                self.main_app.ui_intent_handler.apply(intent)
            except Exception as exc:
                log_event(logger, logging.ERROR, "ui", "intent.apply_failed", intent=intent, error=exc)
            handled += 1
        if handled > 0:
            self.main_app.trace_ui_event(
                "ui.intent.pump",
                handled=handled,
                pending=self.main_app.ui_intent_queue.qsize(),
            )
        self.main_app.root.after(self.main_app.ui_intent_poll_interval_ms, self._pump_ui_intents)

    def enqueue_mqtt_message(self, topic: str, data: dict) -> None:
        self.main_app.mqtt_message_queue.put((topic, data))

    def start_mqtt_queue_pump(self) -> None:
        self.main_app.root.after(self.main_app.mqtt_queue_poll_interval_ms, self._pump_mqtt_queue)

    def _pump_mqtt_queue(self) -> None:
        handled = 0
        while handled < 50:
            try:
                topic, data = self.main_app.mqtt_message_queue.get_nowait()
            except Empty:
                break

            try:
                self.main_app.mqtt_message_router.handle(topic, data)
            except Exception as exc:
                log_event(logger, logging.ERROR, "mqtt", "queue_message_handle_failed", topic=topic, error=exc)
            handled += 1

        self.main_app.root.after(self.main_app.mqtt_queue_poll_interval_ms, self._pump_mqtt_queue)
