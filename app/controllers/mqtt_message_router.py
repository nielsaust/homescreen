from __future__ import annotations

import logging
import time

from app.controllers.overlay_commands import OverlayCommand
from app.config.camera_config_loader import get_camera_specs
from app.observability.domain_logger import log_event

logger = logging.getLogger(__name__)


LEGACY_HANDLER_TO_ACTION = {
    "music_update": "music_update",
    "device_states_update": "device_states_update",
    "overlay_camera": "overlay_command",
    "overlay_calendar": "overlay_command",
    "overlay_alert": "overlay_command",
    "printer_progress": "printer_progress_update",
    "print_status_show": "overlay_command",
    "print_attention": "overlay_command",
    "print_close": "overlay_command",
    "print_cancel_attention": "overlay_command",
}

LEGACY_HANDLER_TO_OVERLAY_COMMAND = {
    "overlay_camera": OverlayCommand.SHOW_CAM,
    "overlay_calendar": OverlayCommand.SHOW_CALENDAR,
    "overlay_alert": OverlayCommand.SHOW_ALERT,
    "print_status_show": OverlayCommand.SHOW_PRINT_STATUS,
    "print_attention": OverlayCommand.PRINT_SCREEN_ATTENTION,
    "print_close": OverlayCommand.CLOSE_PRINT_SCREEN,
    "print_cancel_attention": OverlayCommand.CANCEL_ATTENTION,
}


class MqttMessageRouter:
    """Routes MQTT topics to app actions while preserving startup/degraded behavior."""

    def __init__(self, main_app):
        self.main_app = main_app
        self._routes_by_topic = self._build_routes_by_topic()

    def _is_music_enabled(self):
        if hasattr(self.main_app, "is_music_enabled"):
            return bool(self.main_app.is_music_enabled())
        return bool(getattr(self.main_app.settings, "enable_music", True))

    def handle(self, topic, data):
        time_since_boot = time.time() - self.main_app.boot_time
        self.main_app.publish_event("mqtt.message.received", {"topic": topic})
        log_event(logger, logging.DEBUG, "mqtt", "router.message", topic=topic)
        self.main_app.startup_sync_service.check_queue(topic)
        routes = self._routes_by_topic.get(str(topic), [])
        if not routes:
            log_event(logger, logging.WARNING, "mqtt", "router.unknown_topic", topic=topic)
            return

        log_event(
            logger,
            logging.DEBUG,
            "mqtt",
            "router.time_since_boot",
            seconds=round(time_since_boot),
            hours=round(time_since_boot / 60 / 60, 1),
        )
        if time_since_boot < self.main_app.settings.mqtt_accept_nonessential_messages_after:
            log_event(
                logger,
                logging.WARNING,
                "mqtt",
                "router.nonessential_deferred",
                accept_after_seconds=self.main_app.settings.mqtt_accept_nonessential_messages_after,
            )
        for route in routes:
            phase = str(route.get("phase", "nonessential"))
            if phase != "essential" and time_since_boot < self.main_app.settings.mqtt_accept_nonessential_messages_after:
                continue
            self._dispatch_route(route, data)

    def _handle_device_states(self, data):
        try:
            self.main_app.device_states.update_states(data)
            self.main_app.publish_event(
                "device.state.updated",
                {
                    "in_bed": self.main_app.device_states.in_bed,
                    "printer_progress": self.main_app.device_states.printer_progress,
                },
                source="mqtt_router",
            )
            self.main_app.publish_event(
                "menu.refresh.requested",
                {"reason": "device.state.updated"},
                source="mqtt_router",
            )
            self.main_app.power_policy_service.check_bed_time()
        except Exception as exc:
            log_event(logger, logging.ERROR, "mqtt", "router.device_state_update_failed", error=exc)

    def _dispatch_route(self, route, data):
        action = self._route_action(route)
        if action == "music_update":
            self._dispatch_music_update(data)
            return
        if action == "device_states_update":
            self._handle_device_states(data)
            return
        if action == "printer_progress_update":
            self._check_print_status(data)
            return
        if action == "overlay_command":
            self._dispatch_overlay_command(route, data)
            return

        log_event(
            logger,
            logging.WARNING,
            "mqtt",
            "router.unknown_action",
            action=action,
            handler=str(route.get("handler", "")).strip(),
        )

    def _route_action(self, route: dict) -> str:
        action = str(route.get("action", "")).strip()
        if action:
            return action
        handler = str(route.get("handler", "")).strip()
        return LEGACY_HANDLER_TO_ACTION.get(handler, "")

    def _resolve_overlay_command(self, route: dict) -> str:
        explicit = str(route.get("overlay_command", "")).strip()
        if explicit:
            return explicit
        handler = str(route.get("handler", "")).strip()
        return LEGACY_HANDLER_TO_OVERLAY_COMMAND.get(handler, "")

    def _dispatch_music_update(self, data):
        if not self._is_music_enabled():
            log_event(logger, logging.DEBUG, "mqtt", "router.music_ignored", reason="enable_music_false")
            return
        self.main_app.music_update_service.queue_update(data)

    def _dispatch_overlay_command(self, route, data):
        command = self._resolve_overlay_command(route)
        if not command:
            log_event(
                logger,
                logging.WARNING,
                "mqtt",
                "router.overlay_command_missing",
                route=route,
            )
            return

        payload = {}
        if command == OverlayCommand.SHOW_CAM:
            camera = self._get_camera(str(route.get("camera_id", "")).strip())
            if camera is None:
                return
            payload = {
                "data": data,
                "url": camera.get("url"),
                "username": camera.get("username"),
                "password": camera.get("password"),
            }
        elif command == OverlayCommand.SHOW_CALENDAR:
            payload = {"data": data}
        elif command == OverlayCommand.SHOW_ALERT:
            log_event(logger, logging.DEBUG, "mqtt", "router.alert_received")
            payload = {"data": data}
        elif command == OverlayCommand.SHOW_PRINT_STATUS:
            payload = {
                "progress": self.main_app.device_states.printer_progress,
                "reset": bool(route.get("reset", False)),
            }

        self.main_app.request_overlay(command, payload, source="mqtt_router")

    def _check_print_status(self, data):
        progress = data.get("progress")
        if self.main_app.device_states:
            self.main_app.device_states.printer_progress = progress
        log_event(logger, logging.INFO, "mqtt", "router.print_progress", progress=progress)

        if (
            self.main_app.settings.show_cam_on_print_percentage > 0
            and progress
            and progress >= self.main_app.settings.show_cam_on_print_percentage
        ):
            camera = self._get_camera("printer")
            if camera is None:
                return
            self.main_app.request_overlay(
                OverlayCommand.SHOW_CAM,
                {
                    "data": data,
                    "url": camera.get("url"),
                    "username": camera.get("username"),
                    "password": camera.get("password"),
                },
                source="mqtt_router",
            )
            return

        self.main_app.request_overlay(
            OverlayCommand.UPDATE_PRINT_PROGRESS,
            {"progress": progress},
            source="mqtt_router",
        )

    def _get_camera(self, camera_id: str) -> dict | None:
        camera = get_camera_specs().get(camera_id)
        if isinstance(camera, dict):
            return camera
        log_event(
            logger,
            logging.WARNING,
            "mqtt",
            "router.camera_missing",
            camera_id=camera_id,
            config="local_config/cameras.json",
        )
        return None

    def _build_routes_by_topic(self) -> dict[str, list[dict]]:
        out: dict[str, list[dict]] = {}
        for route in getattr(self.main_app, "mqtt_routes", []):
            topic = str(route.get("topic", "")).strip()
            if not topic:
                continue
            out.setdefault(topic, []).append(route)
        return out
