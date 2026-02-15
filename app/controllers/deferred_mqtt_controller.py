from __future__ import annotations

import logging

from app.observability.domain_logger import log_event

logger = logging.getLogger(__name__)


class DeferredMqttController:
    """No-op MQTT controller used until network is available."""

    def publish_action(self, action, value=None):
        log_event(logger, logging.WARNING, "mqtt", "publish_action.skipped", reason="not_initialized", action=action)

    def publish_message(self, payload=None, topic=None):
        if topic is None:
            topic = "screen_commands/outgoing"
        log_event(logger, logging.WARNING, "mqtt", "publish_message.skipped", reason="not_initialized", topic=topic)

    def start(self):
        return None

    def stop(self):
        return None
