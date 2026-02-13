from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import MainApp
    from touch_controller import TouchController

logger = logging.getLogger(__name__)


class ActionDispatcher:
    """Routes menu actions to handlers, separate from touch/gesture input code."""

    def __init__(self, main_app: MainApp, touch_controller: TouchController):
        self.main_app = main_app
        self.touch_controller = touch_controller
        self._handlers: dict[str, Callable[[], None]] = {
            "back": lambda: self.main_app.request_menu_navigation("back", source="action_dispatcher"),
            "close": lambda: self.main_app.request_menu_navigation("exit", source="action_dispatcher"),
            "turn_screen_off": self._turn_screen_off,
            "cover_kitchen": lambda: self.main_app.mqtt_controller.publish_action("cover_kitchen_toggle"),
            "cinema": lambda: self.main_app.mqtt_controller.publish_action("cinema_toggle"),
            "bed_heating": lambda: self.main_app.mqtt_controller.publish_action("bed_heating_toggle"),
            "beamer_on": lambda: self.main_app.mqtt_controller.publish_action("beamer_on"),
            "beamer_off": lambda: self.main_app.mqtt_controller.publish_action("beamer_off"),
            "soundbar_toggle": lambda: self.main_app.mqtt_controller.publish_action("soundbar_toggle"),
            "soundbar_mute": lambda: self.main_app.mqtt_controller.publish_action("soundbar_mute"),
            "soundbar_hdmi": lambda: self.main_app.mqtt_controller.publish_action("soundbar_hdmi"),
            "soundbar_volume_down": lambda: self.main_app.mqtt_controller.publish_action("soundbar_volume_down"),
            "soundbar_volume_up": lambda: self.main_app.mqtt_controller.publish_action("soundbar_volume_up"),
            "ps_toggle": lambda: self.main_app.mqtt_controller.publish_action("ps_toggle"),
            "scene_dinner": lambda: self.main_app.mqtt_controller.publish_action("scene_dinner"),
            "scene_bright": lambda: self.main_app.mqtt_controller.publish_action("scene_bright"),
            "scene_movie": lambda: self.main_app.mqtt_controller.publish_action("scene_movie"),
            "scene_romantic": lambda: self.main_app.mqtt_controller.publish_action("scene_romantic"),
            "scene_off": lambda: self.main_app.mqtt_controller.publish_action("scene_off"),
            "blinds_down": lambda: self.main_app.mqtt_controller.publish_action("blinds_down"),
            "blinds_up": lambda: self.main_app.mqtt_controller.publish_action("blinds_up"),
            "blinds_stop": lambda: self.main_app.mqtt_controller.publish_action("blinds_stop"),
            "light_woonkamer": lambda: self.main_app.mqtt_controller.publish_action("light_woonkamer_toggle"),
            "light_keuken": lambda: self.main_app.mqtt_controller.publish_action("light_keuken_toggle"),
            "light_kleur": lambda: self.main_app.mqtt_controller.publish_action("light_kleur_toggle"),
            "light_tafel": lambda: self.main_app.mqtt_controller.publish_action("light_tafel_toggle"),
            "in_bed_toggle": lambda: self.main_app.mqtt_controller.publish_action("in_bed_toggle"),
            "doorbell": lambda: self.main_app.mqtt_controller.publish_message(topic="screen_commands/doorbell"),
            "calendar": lambda: self.main_app.mqtt_controller.publish_action("calendar"),
            "calendar_add": lambda: self.main_app.display_controller.show_fullscreen_image("qr-agenda.png"),
            "wifi_qr": lambda: self.main_app.display_controller.show_fullscreen_image("qr-wifi.png"),
            "trash_warning_toggle": lambda: self.main_app.mqtt_controller.publish_action("trash_warning_toggle"),
            "music_play_pause": lambda: self.main_app.media_play_pause(),
            "music_volume_up": lambda: self.main_app.media_volume("up"),
            "music_volume_down": lambda: self.main_app.media_volume("down"),
            "music_next": lambda: self.main_app.media_skip_song("next"),
            "music_previous": lambda: self.main_app.media_skip_song("previous"),
            "music_show_title": self._music_show_title,
            "heart": lambda: self.main_app.display_controller.open_slideshow(),
            "christmas": lambda: self.main_app.mqtt_controller.publish_action("activate_christmas"),
            "3d_printer_status": lambda: self.main_app.display_controller.show_print_status(self.main_app.device_states.printer_progress),
            "3d_printer_cam": lambda: self.main_app.display_controller.show_cam({}, self.main_app.settings.printer_url),
            "show_weather_on_idle": lambda: self._toggle_setting("show_weather_on_idle"),
            "verify_ssl_on_trusted_sources": lambda: self._toggle_setting("verify_ssl_on_trusted_sources"),
            "media_show_titles": lambda: self._toggle_setting("media_show_titles"),
            "media_sanitize_titles": lambda: self._toggle_setting("media_sanitize_titles"),
            "shell_reboot": lambda: self.touch_controller.reboot(),
            "shell_shutdown": lambda: self.touch_controller.shell_command("shutdown", use_sudo=True),
            "shell_disable_networking": lambda: self.touch_controller.disable_networking(),
            "shell_enable_networking": lambda: self.touch_controller.enable_networking(),
            "shell_recover_network": lambda: self.touch_controller.recover_network(),
            "exit": lambda: self.touch_controller.quit_app(),
        }

    def dispatch(self, action: str) -> None:
        self.main_app.publish_event("action.triggered", {"action": action}, source="action_dispatcher")
        handler = self._handlers.get(action)
        if handler is None:
            logger.warning("No action handler found for '%s'", action)
            return
        handler()

    def _toggle_setting(self, attr: str) -> None:
        current = bool(getattr(self.main_app.settings, attr))
        setattr(self.main_app.settings, attr, not current)
        self.main_app.settings.save_settings()
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
        self.main_app.check_idle_timer(False)

    def _music_show_title(self) -> None:
        self.main_app.request_menu_navigation("exit", source="action_dispatcher")
        if not self.main_app.settings.media_show_titles:
            self.main_app.root.after(120, self.main_app.show_music_overlays)
