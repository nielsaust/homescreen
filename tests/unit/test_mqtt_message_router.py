from __future__ import annotations

import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.controllers.mqtt_message_router import MqttMessageRouter
from app.controllers.overlay_commands import OverlayCommand


class _DeviceStates:
    def __init__(self):
        self.printer_progress = 0
        self.sleep_mode = "off"

    def update_states(self, data, mapping=None):
        value = data.get("sleep_mode", self.sleep_mode)
        self.sleep_mode = str(value).strip().lower() in ("on", "true", "1", "yes")


class _MainApp:
    def __init__(self):
        self.boot_time = time.time() - 100
        self.music_calls = []
        self.overlay_calls = []
        self.events = []
        self.queue_checks = []
        self.bed_time_checks = 0
        self.settings = SimpleNamespace(
            mqtt_accept_nonessential_messages_after=0,
            show_cam_on_print_percentage=80,
        )
        self.mqtt_routes = [
            {"topic": "music", "action": "music_update", "phase": "essential"},
            {"topic": "screen_commands/incoming", "action": "device_states_update", "phase": "essential"},
            {"topic": "octoPrint/progress/printing", "action": "printer_progress_update", "phase": "nonessential"},
            {"topic": "calendar", "action": "overlay_command", "overlay_command": "show_calendar", "phase": "nonessential"},
        ]
        self.device_state_mapping = None
        self.device_states = _DeviceStates()
        self.startup_sync_service = SimpleNamespace(check_queue=self.check_mqtt_message_queue)
        self.music_update_service = SimpleNamespace(queue_update=self.queue_music_update)
        self.power_policy_service = SimpleNamespace(check_bed_time=self.check_bed_time)

    def publish_event(self, name, payload, source=None):
        self.events.append((name, payload, source))

    def check_mqtt_message_queue(self, topic):
        self.queue_checks.append(topic)

    def queue_music_update(self, data):
        self.music_calls.append(data)

    def check_bed_time(self):
        self.bed_time_checks += 1

    def request_overlay(self, command, payload=None, source=None):
        self.overlay_calls.append((command, payload, source))


class TestMqttMessageRouter(unittest.TestCase):
    def test_music_topic_queues_update(self):
        app = _MainApp()
        router = MqttMessageRouter(app)

        router.handle("music", {"state": "playing"})

        self.assertEqual(app.music_calls, [{"state": "playing"}])
        self.assertEqual(app.queue_checks, ["music"])

    def test_printer_progress_requests_update_overlay(self):
        app = _MainApp()
        router = MqttMessageRouter(app)

        router.handle("octoPrint/progress/printing", {"progress": 50})

        self.assertEqual(app.overlay_calls[-1][0], OverlayCommand.UPDATE_PRINT_PROGRESS)
        self.assertEqual(app.overlay_calls[-1][1]["progress"], 50)

    def test_printer_threshold_requests_cam_overlay(self):
        app = _MainApp()
        router = MqttMessageRouter(app)

        with patch(
            "app.controllers.mqtt_message_router.get_camera_specs",
            return_value={"printer": {"url": "http://printer-test"}},
        ):
            router.handle("octoPrint/progress/printing", {"progress": 95})

        self.assertEqual(app.overlay_calls[-1][0], OverlayCommand.SHOW_CAM)
        self.assertEqual(app.overlay_calls[-1][1]["url"], "http://printer-test")

    def test_device_topic_updates_state_and_emits_events(self):
        app = _MainApp()
        router = MqttMessageRouter(app)

        router.handle("screen_commands/incoming", {"sleep_mode": "on"})

        self.assertTrue(app.device_states.sleep_mode)
        self.assertEqual(app.bed_time_checks, 1)
        event_names = [entry[0] for entry in app.events]
        self.assertIn("device.state.updated", event_names)
        self.assertIn("menu.refresh.requested", event_names)

    def test_device_topic_accepts_sleep_mode_payload(self):
        app = _MainApp()
        router = MqttMessageRouter(app)

        router.handle("screen_commands/incoming", {"sleep_mode": "on"})

        self.assertTrue(app.device_states.sleep_mode)


if __name__ == "__main__":
    unittest.main()
