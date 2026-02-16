from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from app.controllers.overlay_commands import OverlayCommand
from app.controllers.action_registry import ACTION_SPECS

if TYPE_CHECKING:
    from main import MainApp
    from app.controllers.touch_controller import TouchController

logger = logging.getLogger(__name__)
QR_ITEMS_PATH = Path(__file__).resolve().parent.parent.parent / "local_config" / "qr_items.json"


class ActionDispatcher:
    """Routes menu actions to handlers, separate from touch/gesture input code."""

    def __init__(self, main_app: MainApp, touch_controller: TouchController):
        self.main_app = main_app
        self.touch_controller = touch_controller
        self._custom_handlers = {
            "turn_screen_off": self._turn_screen_off,
            "doorbell": self._doorbell_action,
            "music_show_title": self._music_show_title,
            "test_mij_todo": self._test_mij_todo,
        }

    def dispatch(self, action: str) -> None:
        self.main_app.publish_event("action.triggered", {"action": action}, source="action_dispatcher")
        spec = ACTION_SPECS.get(action)
        if spec is None:
            logger.warning("No action handler found for '%s'", action)
            return
        self._execute(action, spec)

    def _execute(self, action: str, spec: dict) -> None:
        kind = spec.get("kind")
        if kind == "menu_nav":
            self.main_app.request_menu_navigation(spec["command"], source="action_dispatcher")
            return
        if kind == "mqtt_action":
            if not self._ensure_mqtt_enabled():
                return
            self.main_app.mqtt_controller.publish_action(spec["action"])
            return
        if kind == "mqtt_message":
            if not self._ensure_mqtt_enabled():
                return
            self.main_app.mqtt_controller.publish_message(topic=spec["topic"])
            return
        if kind == "show_image":
            self.main_app.display_controller.show_fullscreen_image(spec["image"])
            return
        if kind == "show_qr":
            payload = self._load_qr_item(spec.get("item_id", ""))
            if payload is None:
                return
            self.main_app.display_controller.show_fullscreen_qr(payload)
            return
        if kind == "setting_toggle":
            self._toggle_setting(spec["attr"])
            return
        if kind == "media":
            op = spec.get("op")
            if op == "play_pause":
                self.main_app.media_controller.media_play_pause()
            elif op == "volume":
                self.main_app.media_controller.media_volume(spec.get("arg"))
            elif op == "skip":
                self.main_app.media_controller.media_skip_song(spec.get("arg"))
            return
        if kind == "overlay":
            payload = {}
            command = spec["command"]
            if command == OverlayCommand.SHOW_PRINT_STATUS:
                payload = {"progress": self.main_app.device_states.printer_progress}
            elif command == OverlayCommand.SHOW_CAM:
                payload = {"data": {}, "url": self.main_app.settings.printer_url}
            self.main_app.request_overlay(command, payload, source="action_dispatcher")
            return
        if kind == "shell":
            op = spec.get("op")
            if op == "reboot":
                self.touch_controller.reboot()
            elif op == "shutdown":
                self.touch_controller.shell_command("shutdown", use_sudo=True)
            elif op == "disable_networking":
                self.touch_controller.disable_networking()
            elif op == "enable_networking":
                self.touch_controller.enable_networking()
            elif op == "recover_network":
                self.touch_controller.recover_network()
            return
        if kind == "app_exit":
            self.touch_controller.quit_app()
            return
        if kind == "custom":
            custom = self._custom_handlers.get(spec.get("name"))
            if custom:
                custom()
            else:
                logger.warning("No custom action handler found for '%s'", action)
            return
        logger.warning("Unsupported action kind '%s' for action '%s'", kind, action)

    def _toggle_setting(self, attr: str) -> None:
        default = True if attr == "store_settings" else False
        current = bool(getattr(self.main_app.settings, attr, default))
        setattr(self.main_app.settings, attr, not current)

        should_persist = bool(getattr(self.main_app.settings, "store_settings", True))
        # Always persist the store_settings toggle itself so the persistence mode is explicit.
        if attr == "store_settings" or should_persist:
            self.main_app.settings.save_settings()
        else:
            logger.info("Setting '%s' changed runtime-only (store_settings=false)", attr)

        self.main_app.publish_event(
            "menu.refresh.requested",
            {"reason": f"setting.toggled:{attr}"},
            source="action_dispatcher",
        )

    def _turn_screen_off(self) -> None:
        self.main_app.request_menu_navigation("exit", source="action_dispatcher")
        self.main_app.publish_event(
            "ui.screen.changed",
            {"screen": "off", "is_display_on": False, "force": True},
            source="action_dispatcher",
        )
        self.main_app.power_policy_service.check_idle_timer(False)

    def _music_show_title(self) -> None:
        if not self.main_app.is_music_enabled():
            self.main_app.notify_setup_required("Music")
            return
        self.main_app.request_menu_navigation("exit", source="action_dispatcher")
        if not self.main_app.settings.media_show_titles:
            self.main_app.root.after(120, self.main_app.media_controller.show_music_overlays)

    def _doorbell_action(self) -> None:
        if not self._ensure_mqtt_enabled():
            return
        doorbell_command_topic = str(
            getattr(self.main_app.settings, "mqtt_topic_doorbell_command", "")
        ).strip()
        if not doorbell_command_topic:
            self.main_app.notify_setup_required("Doorbell")
            return
        # Always open the camera immediately on local press, even if HA state is already active.
        self.main_app.request_overlay(
            OverlayCommand.SHOW_CAM,
            {
                "data": {"active": True},
                "url": f"http://{self.main_app.settings.doorbell_url}{self.main_app.settings.doorbell_path}",
                "username": self.main_app.settings.doorbell_username,
                "password": self.main_app.settings.doorbell_password,
            },
            source="action_dispatcher",
        )
        # Also notify HA flow so timeout/automation behavior remains in sync.
        self.main_app.mqtt_controller.publish_message(
            topic=doorbell_command_topic
        )

    def _ensure_mqtt_enabled(self) -> bool:
        if self.main_app.is_mqtt_enabled():
            return True
        self.main_app.notify_setup_required("MQTT")
        return False
    def _test_mij_todo(self) -> None:
        logger.info("Custom action stub triggered: test_mij_todo")

    def _load_qr_item(self, item_id: str) -> dict | None:
        if not item_id:
            logger.warning("QR action missing item_id")
            return None
        if not QR_ITEMS_PATH.exists():
            logger.warning("QR config missing at %s", QR_ITEMS_PATH)
            self.main_app.notify_setup_required("QR config")
            return None
        try:
            data = json.loads(QR_ITEMS_PATH.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.error("QR config parse failed: %s", exc)
            return None
        payload = data.get(item_id)
        if not isinstance(payload, dict):
            logger.warning("QR item '%s' not found in %s", item_id, QR_ITEMS_PATH)
            return None
        return payload
