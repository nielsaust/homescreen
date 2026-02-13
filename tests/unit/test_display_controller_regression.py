from __future__ import annotations

import unittest
from types import SimpleNamespace

from app.controllers.display_controller import DisplayController


class _FakeFrame:
    def __init__(self):
        self.packed = 0

    def pack(self, **_kwargs):
        self.packed += 1


class TestDisplayControllerRegression(unittest.TestCase):
    def test_show_screen_restores_previous_when_show_fails(self):
        controller = DisplayController.__new__(DisplayController)
        previous_frame = _FakeFrame()
        music_frame = _FakeFrame()

        controller.main_app = SimpleNamespace(settings=SimpleNamespace(min_time_between_actions=0.0))
        controller._screen_state = "weather"
        controller.current_screen = previous_frame
        controller.previous_screen = None
        controller.screens = {"music": music_frame}
        controller.time_in_screen = 0

        controller._trace_ui = lambda *_args, **_kwargs: None
        controller._trace_widget_state = lambda *_args, **_kwargs: None
        controller._schedule_trace_widget_state = lambda *_args, **_kwargs: None
        controller._should_block_screen_switch = lambda *_args, **_kwargs: False
        controller._hide_current_screen_for_switch = lambda *_args, **_kwargs: None
        controller._show_selected_screen = lambda *_args, **_kwargs: False
        controller.check_idle = lambda *_args, **_kwargs: None
        controller.force_screen_update = lambda *_args, **_kwargs: None
        controller.get_screen_state = lambda: controller._screen_state

        controller.show_screen("music")

        self.assertEqual(controller.current_screen, previous_frame)
        self.assertEqual(controller._screen_state, "weather")
        self.assertEqual(previous_frame.packed, 1)


if __name__ == "__main__":
    unittest.main()
