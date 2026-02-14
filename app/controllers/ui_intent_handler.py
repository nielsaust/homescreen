from __future__ import annotations

import logging

from app.observability.domain_logger import log_event

logger = logging.getLogger(__name__)


class UiIntentHandler:
    """Applies queued UI intents and owns idempotency/signature guards."""

    def __init__(self, main_app):
        self.main_app = main_app
        self._last_network_ui_state = None
        self._last_cached_weather_label_text = None
        self._last_music_ui_signature = None
        self._last_music_playback_state = None
        self._last_screen_ui_signature = None

    def apply(self, intent):
        intent_type = intent.get("type")
        if intent_type == "network.status":
            self._apply_network_status(intent)
            return
        if intent_type == "weather.cache.status":
            self._apply_weather_cache_status(intent)
            return
        if intent_type == "music.render":
            self._apply_music_render(intent)
            return
        if intent_type == "ui.music.playback":
            self._apply_music_playback(intent)
            return
        if intent_type == "ui.screen.changed":
            self._apply_screen_changed(intent)
            return
        if intent_type == "menu.refresh":
            self.main_app.display_controller.update_menu_states()
            return
        if intent_type == "menu.navigate":
            self._apply_menu_navigation(intent)
            return
        if intent_type == "ui.overlay.requested":
            command = intent.get("command")
            handled = self.main_app.display_controller.handle_overlay_command(command, intent)
            if not handled:
                log_event(logger, logging.WARNING, "ui", "overlay.unknown_command", command=command)

    def _apply_network_status(self, intent):
        online = intent.get("online")
        if online is None or online == self._last_network_ui_state:
            return
        self._last_network_ui_state = online
        self.main_app.update_network_status_ui(online)

    def _apply_weather_cache_status(self, intent):
        weather_screen = self.main_app.display_controller.screen_objects.get("weather")
        if weather_screen is None:
            return

        source = intent.get("source")
        cached_at_text = intent.get("cached_at_text")
        if source == "cache" and cached_at_text:
            if cached_at_text == self._last_cached_weather_label_text:
                return
            self._last_cached_weather_label_text = cached_at_text
            weather_screen.show_cached_weather_label(cached_at_text)
            return

        if self._last_cached_weather_label_text is None:
            return
        self._last_cached_weather_label_text = None
        weather_screen.hide_cached_weather_label()

    def _apply_music_render(self, intent):
        signature = (
            intent.get("state"),
            intent.get("title"),
            intent.get("artist"),
            intent.get("channel"),
            intent.get("album"),
            intent.get("album_art_api_url"),
        )
        if signature == self._last_music_ui_signature:
            return
        self._last_music_ui_signature = signature

        music_screen = self.main_app.display_controller.screen_objects.get("music")
        if music_screen is None:
            return
        music_screen.apply_state_update(
            state=intent.get("state"),
            title=intent.get("title"),
            artist=intent.get("artist"),
            channel=intent.get("channel"),
            album=intent.get("album"),
            album_art_api_url=intent.get("album_art_api_url"),
        )

    def _apply_music_playback(self, intent):
        playback_state = intent.get("state")
        if playback_state == self._last_music_playback_state:
            return
        self._last_music_playback_state = playback_state
        menu_open = self.main_app.display_controller.get_screen_state() == "menu"
        if playback_state == "playing":
            self.main_app.music_playback_policy_service.cancel_pause_idle_timeout()
            self.main_app.switch_to_music()
            return
        if playback_state == "paused":
            if not menu_open:
                self.main_app.music_playback_policy_service.schedule_pause_idle()
            return
        self.main_app.music_playback_policy_service.cancel_pause_idle_timeout()
        if not menu_open:
            self.main_app.switch_to_idle()

    def _apply_screen_changed(self, intent):
        screen = intent.get("screen")
        is_display_on = bool(intent.get("is_display_on"))
        force = bool(intent.get("force", False))
        self.main_app.trace_ui_event(
            "ui.screen.intent",
            screen=screen,
            is_display_on=is_display_on,
            force=force,
        )
        signature = (screen, is_display_on)
        if not force and signature == self._last_screen_ui_signature:
            return
        self._last_screen_ui_signature = signature

        if not is_display_on or screen == "off":
            self.main_app.display_controller.turn_off()
            return
        if screen == "weather":
            self.main_app.display_controller.show_screen("weather", force=force)
            return
        if screen == "music":
            self.main_app.display_controller.show_screen("music", force=force)
            return
        if screen == "menu":
            self.main_app.display_controller.show_screen("menu", force=force)
            return
        log_event(logger, logging.WARNING, "ui", "screen.unknown_intent", screen=screen)

    def _apply_menu_navigation(self, intent):
        command = intent.get("command")
        if command == "page_prev":
            self.main_app.display_controller.switch_menu_page(-1)
            return
        if command == "page_next":
            self.main_app.display_controller.switch_menu_page(1)
            return
        if command == "back":
            self.main_app.display_controller.menu_back()
            return
        if command == "exit":
            self.main_app.display_controller.exit_menu()
            return
        log_event(logger, logging.WARNING, "ui", "menu.unknown_navigation_command", command=command)
