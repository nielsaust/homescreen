from __future__ import annotations

import logging

from core.events import AppEvent
from app.observability.domain_logger import log_event

logger = logging.getLogger(__name__)


class EventDispatchService:
    """Encapsulates event publishing to the app event bus."""

    def __init__(self, main_app):
        self.main_app = main_app

    def publish_event(self, event_type, payload=None, source="main") -> None:
        try:
            event = AppEvent(
                event_type=event_type,
                payload=payload or {},
                source=source,
            )
            self.main_app.event_bus.publish(event)
        except Exception as exc:
            log_event(logger, logging.DEBUG, "app", "event.publish_failed", event_type=event_type, error=exc)
