from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import MainApp


class MusicMetricsService:
    """Observability-only counters and periodic logging for music flow."""

    def __init__(self, main_app: MainApp, interval_ms: int):
        self.main_app = main_app
        self.interval_ms = interval_ms
        self.metrics = {
            "received": 0,
            "coalesced": 0,
            "dropped": 0,
            "applied": 0,
            "art_requests": 0,
            "art_success": 0,
            "art_stale_dropped": 0,
            "art_placeholder": 0,
            "art_errors": 0,
        }

    def record(self, key: str, amount: int = 1) -> None:
        if key not in self.metrics:
            self.metrics[key] = 0
        self.metrics[key] += amount

    def start_logging(self) -> None:
        self.main_app.root.after(self.interval_ms, self._log_tick)

    def _log_tick(self) -> None:
        if self.main_app.music_debug_logging:
            self.main_app.log_music_debug("[music] metrics (observability-only)", self.metrics)
        self.main_app.root.after(self.interval_ms, self._log_tick)
