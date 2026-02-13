from __future__ import annotations

import threading
from collections.abc import Callable

from core.events import AppEvent
from core.reducer import reduce_state
from core.state import AppState


StateListener = Callable[[AppState, AppEvent], None]


class AppStore:
    """Thread-safe state store for the reducer-based app model."""

    def __init__(self, initial_state: AppState):
        self._state = initial_state
        self._lock = threading.RLock()
        self._listeners: list[StateListener] = []

    def subscribe(self, listener: StateListener) -> None:
        with self._lock:
            self._listeners.append(listener)

    def dispatch(self, event: AppEvent) -> AppState:
        with self._lock:
            self._state = reduce_state(self._state, event)
            listeners = list(self._listeners)
            snapshot = self._state

        for listener in listeners:
            listener(snapshot, event)
        return snapshot

    def get_state(self) -> AppState:
        with self._lock:
            return self._state
