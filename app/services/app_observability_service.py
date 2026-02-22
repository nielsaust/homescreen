from __future__ import annotations

import datetime
import json
import logging
import sys
import time

from app.observability.domain_logger import log_event

logger = logging.getLogger(__name__)


class AppObservabilityService:
    """Centralizes app-level debug/trace/error logging helpers."""

    def __init__(self, main_app):
        self.main_app = main_app

    def startup_timestamp(self) -> str:
        current_datetime = datetime.datetime.now()
        return current_datetime.strftime("%d %b %Y - %H:%M")

    def install_global_exception_hook(self) -> None:
        sys.excepthook = self._handle_unhandled_exception

    def _handle_unhandled_exception(self, exc_type, exc_value, exc_traceback) -> None:
        log_event(logger, logging.ERROR, "app", "unhandled_exception", error=exc_value)
        log_event(logger, logging.ERROR, "app", "unhandled_exception.trace")
        logger.error("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))

    def log_music_debug(self, message, payload=None) -> None:
        if not self.main_app.music_debug_logging:
            return
        if payload is None:
            log_event(logger, logging.DEBUG, "music", "debug", message=message)
            return
        try:
            log_event(
                logger,
                logging.DEBUG,
                "music",
                "debug",
                message=message,
                payload=json.dumps(payload, default=str, ensure_ascii=False),
            )
        except Exception:
            log_event(logger, logging.DEBUG, "music", "debug", message=message, payload=payload)

    def trace_ui_event(self, event_name, **fields) -> None:
        if not self.main_app.ui_trace_logging:
            return
        payload = {
            "event": event_name,
            "ts_ms": int(time.time() * 1000),
            **fields,
        }
        try:
            log_event(logger, logging.DEBUG, "ui", "trace", payload=json.dumps(payload, default=str, ensure_ascii=False))
        except Exception:
            log_event(logger, logging.DEBUG, "ui", "trace", payload=payload)
