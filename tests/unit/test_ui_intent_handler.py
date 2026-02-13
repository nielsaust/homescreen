from __future__ import annotations

import unittest

from app.controllers.ui_intent_handler import UiIntentHandler


class _WeatherScreen:
    def __init__(self):
        self.cached_labels = []
        self.hide_calls = 0

    def show_cached_weather_label(self, text):
        self.cached_labels.append(text)

    def hide_cached_weather_label(self):
        self.hide_calls += 1


class _MusicScreen:
    def __init__(self):
        self.updates = []

    def apply_state_update(self, **kwargs):
        self.updates.append(kwargs)


class _DisplayController:
    def __init__(self):
        self.screen = "weather"
        self.screen_objects = {"weather": _WeatherScreen(), "music": _MusicScreen()}
        self.menu_refreshes = 0
        self.screen_switches = []

    def update_menu_states(self):
        self.menu_refreshes += 1

    def get_screen_state(self):
        return self.screen

    def show_screen(self, screen, force=False):
        self.screen = screen
        self.screen_switches.append((screen, force))

    def turn_off(self):
        self.screen = "off"

    def switch_menu_page(self, _offset):
        return None

    def menu_back(self):
        return None

    def exit_menu(self):
        return None

    def handle_overlay_command(self, _command, _intent):
        return True


class _MainApp:
    def __init__(self):
        self.display_controller = _DisplayController()
        self.network_ui_updates = []
        self.music_paused_scheduled = 0
        self.music_pause_cancelled = 0
        self.trace_events = []
        self.switch_to_music_calls = 0
        self.switch_to_idle_calls = 0

    def update_network_status_ui(self, online):
        self.network_ui_updates.append(online)

    def _schedule_music_pause_idle(self):
        self.music_paused_scheduled += 1

    def _cancel_music_pause_timeout(self):
        self.music_pause_cancelled += 1

    def switch_to_music(self):
        self.switch_to_music_calls += 1

    def switch_to_idle(self):
        self.switch_to_idle_calls += 1

    def trace_ui_event(self, name, **payload):
        self.trace_events.append((name, payload))


class TestUiIntentHandler(unittest.TestCase):
    def test_network_status_is_idempotent(self):
        app = _MainApp()
        handler = UiIntentHandler(app)

        handler.apply({"type": "network.status", "online": True})
        handler.apply({"type": "network.status", "online": True})

        self.assertEqual(app.network_ui_updates, [True])

    def test_weather_cache_label_show_and_hide(self):
        app = _MainApp()
        handler = UiIntentHandler(app)
        weather = app.display_controller.screen_objects["weather"]

        handler.apply({"type": "weather.cache.status", "source": "cache", "cached_at_text": "19:30"})
        handler.apply({"type": "weather.cache.status", "source": "live", "cached_at_text": None})

        self.assertEqual(weather.cached_labels, ["19:30"])
        self.assertEqual(weather.hide_calls, 1)

    def test_music_render_applies_once_for_same_signature(self):
        app = _MainApp()
        handler = UiIntentHandler(app)
        music = app.display_controller.screen_objects["music"]
        intent = {
            "type": "music.render",
            "state": "playing",
            "title": "Song",
            "artist": "Artist",
            "channel": None,
            "album": "Album",
            "album_art_api_url": None,
        }

        handler.apply(intent)
        handler.apply(intent)

        self.assertEqual(len(music.updates), 1)

    def test_playback_paused_schedules_idle_when_not_in_menu(self):
        app = _MainApp()
        handler = UiIntentHandler(app)

        handler.apply({"type": "ui.music.playback", "state": "paused"})

        self.assertEqual(app.music_paused_scheduled, 1)

    def test_screen_changed_turns_off_on_off_screen(self):
        app = _MainApp()
        handler = UiIntentHandler(app)

        handler.apply({"type": "ui.screen.changed", "screen": "off", "is_display_on": False})

        self.assertEqual(app.display_controller.get_screen_state(), "off")
        self.assertGreater(len(app.trace_events), 0)


if __name__ == "__main__":
    unittest.main()
