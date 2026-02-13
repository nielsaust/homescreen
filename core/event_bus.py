from __future__ import annotations

import logging
import threading
from collections.abc import Callable

from core.events import AppEvent

logger = logging.getLogger(__name__)

EventListener = Callable[[AppEvent], None]


class EventBus:
    """In-process event bus to decouple producers from consumers."""

    def __init__(self) -> None:
        self._listeners: list[EventListener] = []
        self._lock = threading.RLock()

    def subscribe(self, listener: EventListener) -> None:
        with self._lock:
            self._listeners.append(listener)

    def publish(self, event: AppEvent) -> None:
        with self._lock:
            listeners = list(self._listeners)

        for listener in listeners:
            try:
                listener(event)
            except Exception as exc:  # pragma: no cover
                logger.error("Event listener error for %s: %s", event.event_type, exc)
