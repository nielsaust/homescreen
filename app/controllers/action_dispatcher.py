from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from app.controllers.overlay_commands import OverlayCommand
from app.controllers.action_registry import ACTION_SPECS
from app.config.camera_config_loader import get_camera_specs

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
            "music_show_title": self._music_show_title,
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
            self._publish_mqtt_action(spec)
            return
        if kind in ("mqtt_message", "mqtt_publish"):
            if not self._ensure_mqtt_enabled():
                return
            self._publish_mqtt_message(spec)
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
        if kind == "show_camera":
            self._show_camera(
                spec.get("camera_id", ""),
                command_topic=spec.get("command_topic"),
                command_topic_key=spec.get("command_topic_key"),
                command_payload=spec.get("command_payload"),
            )
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
                camera_id = str(spec.get("camera_id", "printer"))
                camera = self._load_camera_item(camera_id)
                if camera is None:
                    self.main_app.notify_setup_required("Camera")
                    return
                payload = {
                    "data": camera.get("overlay_data") if isinstance(camera.get("overlay_data"), dict) else {},
                    "url": camera.get("url"),
                    "username": camera.get("username"),
                    "password": camera.get("password"),
                }
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

    def _resolve_topic_for_spec(self, spec: dict, default_topic_key: str = "") -> str:
        topic = str(spec.get("topic", "")).strip()
        if topic:
            return topic
        topic_key = str(spec.get("topic_key", "")).strip() or default_topic_key
        if topic_key and hasattr(self.main_app, "get_topic"):
            fallback = "screen_commands/outgoing" if topic_key == "actions_outgoing" else ""
            return self.main_app.get_topic(topic_key, fallback)
        if topic_key == "actions_outgoing":
            return "screen_commands/outgoing"
        return ""

    def _normalize_payload(self, payload):
        if isinstance(payload, (dict, list)):
            return json.dumps(payload)
        if payload is None:
            return None
        return str(payload)

    def _publish_mqtt_action(self, spec: dict) -> None:
        topic = self._resolve_topic_for_spec(spec, default_topic_key="actions_outgoing")
        if not topic:
            logger.warning("MQTT action missing publish topic")
            self.main_app.notify_setup_required("MQTT")
            return

        payload = {"action": spec.get("action")}
        if "value" in spec:
            payload["value"] = spec.get("value")
        extra = spec.get("extra")
        if isinstance(extra, dict):
            payload.update(extra)
        self.main_app.mqtt_controller.publish_message(
            payload=self._normalize_payload(payload),
            topic=topic,
        )

    def _publish_mqtt_message(self, spec: dict) -> None:
        topic = self._resolve_topic_for_spec(spec, default_topic_key="")
        if not topic:
            logger.warning("MQTT publish missing topic")
            self.main_app.notify_setup_required("MQTT")
            return
        payload = self._normalize_payload(spec.get("payload"))
        self.main_app.mqtt_controller.publish_message(payload=payload, topic=topic)

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

    def _ensure_mqtt_enabled(self) -> bool:
        if self.main_app.is_mqtt_enabled():
            return True
        self.main_app.notify_setup_required("MQTT")
        return False

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

    def _show_camera(
        self,
        camera_id: str,
        command_topic: str | None = None,
        command_topic_key: str | None = None,
        command_payload=None,
    ) -> None:
        camera_id = str(camera_id or "").strip()
        if not camera_id:
            logger.warning("Camera action missing camera_id")
            return

        camera = self._load_camera_item(camera_id)
        if camera is None:
            self.main_app.notify_setup_required("Camera")
            return

        url = str(camera.get("url", "")).strip()
        if not url:
            logger.warning("Camera '%s' missing URL", camera_id)
            self.main_app.notify_setup_required("Camera")
            return

        username = camera.get("username")
        password = camera.get("password")
        overlay_data = camera.get("overlay_data")
        if not isinstance(overlay_data, dict):
            overlay_data = {"active": True}

        self.main_app.request_overlay(
            OverlayCommand.SHOW_CAM,
            {
                "data": overlay_data,
                "url": url,
                "username": username,
                "password": password,
            },
            source="action_dispatcher",
        )

        topic_key = str(command_topic_key or camera.get("command_topic_key") or "").strip()
        topic = str(command_topic or camera.get("command_topic") or "").strip()
        if not topic and topic_key and hasattr(self.main_app, "get_topic"):
            topic = self.main_app.get_topic(topic_key)
        if not topic:
            return

        if not self._ensure_mqtt_enabled():
            return

        payload = command_payload if command_payload is not None else camera.get("command_payload")
        if payload is None:
            payload = overlay_data
        if isinstance(payload, (dict, list)):
            payload = json.dumps(payload)
        elif payload is not None:
            payload = str(payload)
        self.main_app.mqtt_controller.publish_message(payload=payload, topic=topic)

    def _load_camera_item(self, camera_id: str) -> dict | None:
        specs = get_camera_specs()
        payload = specs.get(camera_id)
        if isinstance(payload, dict):
            return payload
        logger.warning("Camera '%s' not found in local_config/cameras.json", camera_id)
        return None
