from __future__ import annotations

import logging
import time

from app.controllers.overlay_commands import OverlayCommand
from app.observability.domain_logger import log_event

logger = logging.getLogger(__name__)


class MqttMessageRouter:
    """Routes MQTT topics to app actions while preserving startup/degraded behavior."""

    def __init__(self, main_app):
        self.main_app = main_app

    def handle(self, topic, data):
        time_since_boot = time.time() - self.main_app.boot_time
        self.main_app.publish_event("mqtt.message.received", {"topic": topic})
        log_event(logger, logging.DEBUG, "mqtt", "router.message", topic=topic)
        self.main_app.check_mqtt_message_queue(topic)

        if topic == self.main_app.settings.mqtt_topic_music:
            self.main_app.queue_music_update(data)
            return

        if topic == self.main_app.settings.mqtt_topic_devices:
            self._handle_device_states(data)
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
            return

        self._handle_nonessential(topic, data)

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
            self.main_app.check_bed_time()
        except Exception as exc:
            log_event(logger, logging.ERROR, "mqtt", "router.device_state_update_failed", error=exc)

    def _handle_nonessential(self, topic, data):
        if topic == self.main_app.settings.mqtt_topic_doorbell:
            self.main_app.request_overlay(
                OverlayCommand.SHOW_CAM,
                {
                    "data": data,
                    "url": f"http://{self.main_app.settings.doorbell_url}{self.main_app.settings.doorbell_path}",
                    "username": self.main_app.settings.doorbell_username,
                    "password": self.main_app.settings.doorbell_password,
                },
                source="mqtt_router",
            )
            return

        if topic == self.main_app.settings.mqtt_topic_printer_progress:
            self._check_print_status(data)
            return

        if topic == self.main_app.settings.mqtt_topic_calendar:
            self.main_app.request_overlay(
                OverlayCommand.SHOW_CALENDAR,
                {"data": data},
                source="mqtt_router",
            )
            return

        if topic == self.main_app.settings.mqtt_topic_alert:
            log_event(logger, logging.DEBUG, "mqtt", "router.alert_received")
            self.main_app.request_overlay(
                OverlayCommand.SHOW_ALERT,
                {"data": data},
                source="mqtt_router",
            )
            return

        if topic == self.main_app.settings.mqtt_topic_print_start:
            self.main_app.request_overlay(
                OverlayCommand.SHOW_PRINT_STATUS,
                {"progress": self.main_app.device_states.printer_progress, "reset": True},
                source="mqtt_router",
            )
            return

        if topic in (
            self.main_app.settings.mqtt_topic_print_done,
            self.main_app.settings.mqtt_topic_print_change_filament,
        ):
            self.main_app.request_overlay(OverlayCommand.PRINT_SCREEN_ATTENTION, source="mqtt_router")
            return

        if topic == self.main_app.settings.mqtt_topic_print_cancelled:
            self.main_app.request_overlay(OverlayCommand.CLOSE_PRINT_SCREEN, source="mqtt_router")
            return

        if topic == self.main_app.settings.mqtt_topic_print_change_z:
            self.main_app.request_overlay(OverlayCommand.CANCEL_ATTENTION, source="mqtt_router")
            return

        log_event(logger, logging.WARNING, "mqtt", "router.unknown_topic", topic=topic)

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
            self.main_app.request_overlay(
                OverlayCommand.SHOW_CAM,
                {"data": data, "url": self.main_app.settings.printer_url},
                source="mqtt_router",
            )
            return

        self.main_app.request_overlay(
            OverlayCommand.UPDATE_PRINT_PROGRESS,
            {"progress": progress},
            source="mqtt_router",
        )
