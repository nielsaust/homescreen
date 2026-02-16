from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.config.startup_actions import get_startup_actions
from app.observability.domain_logger import log_event

if TYPE_CHECKING:
    from main import MainApp

logger = logging.getLogger(__name__)

MQTT_ACTION_KINDS = {"mqtt_action", "mqtt_message", "mqtt_publish"}


class StartupActionService:
    """Runs selected action specs after app startup with optional MQTT readiness retry."""

    def __init__(self, main_app: MainApp):
        self.main_app = main_app

    def start(self) -> None:
        actions = self._collect_startup_actions()
        if not actions:
            return
        for item in actions:
            delay_ms = max(0, int(item["delay_ms"]))
            self.main_app.root.after(delay_ms, lambda i=item: self._execute_with_readiness(i))

    def _collect_startup_actions(self) -> list[dict]:
        out: list[dict] = []
        for spec in get_startup_actions():
            if not isinstance(spec, dict):
                continue
            if not bool(spec.get("enabled", True)):
                continue
            action_id = str(spec.get("id", "")).strip() or "startup_action"
            delay_ms = int(spec.get("delay_ms", 0) or 0)
            require_mqtt = spec.get("require_mqtt")
            if require_mqtt is None:
                require_mqtt = str(spec.get("kind", "")).strip() in MQTT_ACTION_KINDS
            out.append(
                {
                    "action_id": action_id,
                    "spec": spec,
                    "delay_ms": delay_ms,
                    "require_mqtt": bool(require_mqtt),
                    "attempts": 0,
                }
            )
        out.sort(key=lambda item: (item["delay_ms"], item["action_id"]))
        log_event(logger, logging.INFO, "app", "startup_actions.collected", count=len(out))
        return out

    def _execute_with_readiness(self, item: dict) -> None:
        action_id = str(item["action_id"])
        require_mqtt = bool(item["require_mqtt"])
        attempts = int(item.get("attempts", 0))

        if require_mqtt and not bool(getattr(self.main_app, "mqtt_initialized", False)):
            if attempts >= 20:
                log_event(
                    logger,
                    logging.WARNING,
                    "app",
                    "startup_action.skipped",
                    action=action_id,
                    reason="mqtt_not_ready",
                )
                return
            item["attempts"] = attempts + 1
            self.main_app.root.after(500, lambda i=item: self._execute_with_readiness(i))
            return

        log_event(
            logger,
            logging.INFO,
            "app",
            "startup_action.executing",
            action=action_id,
            attempts=attempts,
            require_mqtt=require_mqtt,
        )
        self.main_app.action_dispatcher.dispatch_spec(action_id, item.get("spec", {}))
