from __future__ import annotations

import unittest
from types import SimpleNamespace

from app.controllers.screen_state_controller import ScreenStateController


class _DisplayController:
    def __init__(self):
        self.screen = "weather"

    def get_screen_state(self):
        return self.screen

    def menu_ready(self):
        return True


class _MainApp:
    def __init__(self):
        self.display_controller = _DisplayController()
        self.music_object = SimpleNamespace(state="idle")
        self.settings = SimpleNamespace(show_weather_on_idle=True)
        self.events = []

    def publish_event(self, name, payload, source=None):
        self.events.append((name, payload, source))


class TestScreenStateController(unittest.TestCase):
    def test_switch_to_idle_weather(self):
        app = _MainApp()
        controller = ScreenStateController(app)

        controller.switch_to_idle()

        self.assertEqual(app.events[-1][0], "ui.screen.changed")
        self.assertEqual(app.events[-1][1]["screen"], "weather")

    def test_switch_to_idle_off_when_disabled(self):
        app = _MainApp()
        app.settings.show_weather_on_idle = False
        controller = ScreenStateController(app)

        controller.switch_to_idle()

        self.assertEqual(app.events[-1][1]["screen"], "off")
        self.assertFalse(app.events[-1][1]["is_display_on"])

    def test_switch_to_music_ignored_when_menu_active_without_force(self):
        app = _MainApp()
        app.display_controller.screen = "menu"
        controller = ScreenStateController(app)

        controller.switch_to_music(force=False)

        self.assertEqual(app.events, [])

    def test_switch_to_menu_falls_back_to_idle_if_not_ready(self):
        app = _MainApp()
        app.display_controller.menu_ready = lambda: False
        controller = ScreenStateController(app)

        controller.switch_to_menu()

        self.assertEqual(app.events[-1][0], "ui.screen.changed")

    def test_exit_menu_prefers_music_when_playing(self):
        app = _MainApp()
        app.music_object.state = "playing"
        controller = ScreenStateController(app)

        controller.exit_menu()

        self.assertEqual(app.events[-1][1]["screen"], "music")


if __name__ == "__main__":
    unittest.main()
