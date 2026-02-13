from __future__ import annotations

import time
import unittest
from types import SimpleNamespace

from app.controllers.mqtt_message_router import MqttMessageRouter
from app.controllers.overlay_commands import OverlayCommand


class _DeviceStates:
    def __init__(self):
        self.printer_progress = 0
        self.in_bed = "off"

    def update_states(self, data):
        self.in_bed = data.get("in_bed", self.in_bed)


class _MainApp:
    def __init__(self):
        self.boot_time = time.time() - 100
        self.music_calls = []
        self.overlay_calls = []
        self.events = []
        self.queue_checks = []
        self.settings = SimpleNamespace(
            mqtt_topic_music="music",
            mqtt_topic_devices="screen_commands/incoming",
            mqtt_topic_doorbell="doorbell",
            mqtt_topic_printer_progress="octoPrint/progress/printing",
            mqtt_topic_calendar="calendar",
            mqtt_topic_alert="screen_commands/alert",
            mqtt_topic_print_start="screen_commands/print_start",
            mqtt_topic_print_done="screen_commands/print_done",
            mqtt_topic_print_change_filament="screen_commands/print_change_filament",
            mqtt_topic_print_cancelled="screen_commands/print_cancelled",
            mqtt_topic_print_change_z="screen_commands/print_change_z",
            mqtt_accept_nonessential_messages_after=0,
            show_cam_on_print_percentage=80,
            printer_url="http://printer",
            doorbell_url="doorbell.local",
            doorbell_path="/stream",
            doorbell_username="u",
            doorbell_password="p",
        )
        self.device_states = _DeviceStates()

    def publish_event(self, name, payload, source=None):
        self.events.append((name, payload, source))

    def check_mqtt_message_queue(self, topic):
        self.queue_checks.append(topic)

    def queue_music_update(self, data):
        self.music_calls.append(data)

    def check_bed_time(self):
        return None

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

        router.handle(app.settings.mqtt_topic_printer_progress, {"progress": 50})

        self.assertEqual(app.overlay_calls[-1][0], OverlayCommand.UPDATE_PRINT_PROGRESS)
        self.assertEqual(app.overlay_calls[-1][1]["progress"], 50)

    def test_printer_threshold_requests_cam_overlay(self):
        app = _MainApp()
        router = MqttMessageRouter(app)

        router.handle(app.settings.mqtt_topic_printer_progress, {"progress": 95})

        self.assertEqual(app.overlay_calls[-1][0], OverlayCommand.SHOW_CAM)
        self.assertEqual(app.overlay_calls[-1][1]["url"], app.settings.printer_url)

    def test_device_topic_updates_state_and_emits_events(self):
        app = _MainApp()
        router = MqttMessageRouter(app)

        router.handle(app.settings.mqtt_topic_devices, {"in_bed": "on"})

        self.assertEqual(app.device_states.in_bed, "on")
        event_names = [entry[0] for entry in app.events]
        self.assertIn("device.state.updated", event_names)
        self.assertIn("menu.refresh.requested", event_names)


if __name__ == "__main__":
    unittest.main()
