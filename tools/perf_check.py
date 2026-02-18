#!/usr/bin/env python3
"""Lightweight performance checks for core controllers.

This script avoids UI/network side effects and focuses on pure Python event flow costs.
It is intended as a fast guardrail for regressions, not as a benchmark suite.
"""

from __future__ import annotations

import argparse
import importlib
import statistics
import sys
import time
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _measure(label, iterations, fn):
    durations_ms = []
    for _ in range(iterations):
        start = time.perf_counter()
        fn()
        durations_ms.append((time.perf_counter() - start) * 1000.0)

    mean = statistics.fmean(durations_ms)
    p95 = sorted(durations_ms)[max(0, int(len(durations_ms) * 0.95) - 1)]
    worst = max(durations_ms)
    print(
        f"[perf] {label}: mean={mean:.3f}ms p95={p95:.3f}ms max={worst:.3f}ms "
        f"(n={iterations})"
    )
    return mean, p95, worst


def _check_import_cost(iterations):
    targets = [
        "app.controllers.mqtt_message_router",
        "app.controllers.ui_intent_handler",
        "app.controllers.screen_state_controller",
        "app.controllers.overlay_manager",
        "app.services.music_service",
        "app.services.weather_service",
    ]

    def _run_once():
        for mod in targets:
            importlib.invalidate_caches()
            importlib.import_module(mod)

    return _measure("import.core_modules", iterations, _run_once)


class _FakeDisplayController:
    def __init__(self):
        self.screen = "weather"
        self.screen_objects = {"weather": _FakeWeatherScreen(), "music": _FakeMusicScreen()}

    def get_screen_state(self):
        return self.screen

    def show_screen(self, screen, force=False):
        self.screen = screen

    def turn_off(self):
        self.screen = "off"

    def update_menu_states(self):
        return None

    def switch_menu_page(self, _offset):
        return None

    def menu_back(self):
        return None

    def exit_menu(self):
        return None

    def handle_overlay_command(self, _command, _payload):
        return True

    def menu_ready(self):
        return True


class _FakeWeatherScreen:
    def show_cached_weather_label(self, _text):
        return None

    def hide_cached_weather_label(self):
        return None


class _FakeMusicScreen:
    def apply_state_update(self, **_kwargs):
        return None


class _FakeDeviceStates:
    def __init__(self):
        self.sleep_mode = "off"
        self.printer_progress = 0

    def update_states(self, data, mapping=None):
        if "sleep_mode" in data:
            self.sleep_mode = data["sleep_mode"]


class _FakeMainApp:
    def __init__(self):
        self.boot_time = time.time() - 999
        self.events = 0
        self.overlay_requests = 0
        self.settings = SimpleNamespace(
            mqtt_accept_nonessential_messages_after=0,
            show_cam_on_print_percentage=90,
            show_weather_on_idle=True,
            enable_mqtt=True,
            enable_music=True,
            enable_weather=True,
        )
        self.mqtt_routes = [
            {"topic": "music", "action": "music_update", "phase": "essential"},
            {"topic": "screen_commands/incoming", "action": "device_states_update", "phase": "essential"},
            {"topic": "octoPrint/progress/printing", "action": "printer_progress_update", "phase": "nonessential"},
            {"topic": "calendar", "action": "overlay_command", "overlay_command": "show_calendar", "phase": "nonessential"},
        ]
        self.device_state_mapping = None
        self.device_states = _FakeDeviceStates()
        self.display_controller = _FakeDisplayController()
        self.music_object = SimpleNamespace(state="idle")
        self.startup_sync_service = SimpleNamespace(check_queue=self.check_mqtt_message_queue)
        self.music_update_service = SimpleNamespace(queue_update=self.queue_music_update)
        self.power_policy_service = SimpleNamespace(check_bed_time=self.check_bed_time)
        self.music_playback_policy_service = SimpleNamespace(
            cancel_pause_idle_timeout=self._cancel_music_pause_timeout,
            schedule_pause_idle=self._schedule_music_pause_idle,
        )
        self.screen_state_controller = SimpleNamespace(
            switch_to_music=self.switch_to_music,
            switch_to_idle=self.switch_to_idle,
        )

    def publish_event(self, *_args, **_kwargs):
        self.events += 1

    def check_mqtt_message_queue(self, *_args, **_kwargs):
        return None

    def queue_music_update(self, *_args, **_kwargs):
        return None

    def check_bed_time(self, *_args, **_kwargs):
        return None

    def request_overlay(self, *_args, **_kwargs):
        self.overlay_requests += 1

    def trace_ui_event(self, *_args, **_kwargs):
        return None

    def update_network_status_ui(self, *_args, **_kwargs):
        return None

    def _cancel_music_pause_timeout(self):
        return None

    def _schedule_music_pause_idle(self):
        return None

    def switch_to_music(self, force=False):
        self.display_controller.show_screen("music", force=force)

    def switch_to_idle(self):
        self.display_controller.show_screen("weather")

    def is_mqtt_enabled(self):
        return bool(getattr(self.settings, "enable_mqtt", False))

    def is_music_enabled(self):
        return bool(getattr(self.settings, "enable_music", False))

    def is_weather_enabled(self):
        return bool(getattr(self.settings, "enable_weather", False))


def _check_router_cost(iterations):
    from app.controllers.mqtt_message_router import MqttMessageRouter

    app = _FakeMainApp()
    router = MqttMessageRouter(app)
    payload = {"progress": 73, "sleep_mode": "off"}

    def _run_once():
        router.handle("screen_commands/incoming", payload)
        router.handle("octoPrint/progress/printing", payload)
        router.handle("calendar", {"event": "x"})

    result = _measure("router.handle.mixed", iterations, _run_once)
    print(f"[perf] router.events={app.events} overlay_requests={app.overlay_requests}")
    return result


def _check_ui_intent_cost(iterations):
    from app.controllers.ui_intent_handler import UiIntentHandler

    app = _FakeMainApp()
    handler = UiIntentHandler(app)

    intents = [
        {"type": "network.status", "online": True},
        {"type": "weather.cache.status", "source": "cache", "cached_at_text": "13:37"},
        {
            "type": "music.render",
            "state": "playing",
            "title": "Track",
            "artist": "Artist",
            "channel": None,
            "album": "Album",
            "album_art_api_url": None,
        },
        {"type": "ui.music.playback", "state": "playing"},
        {"type": "ui.screen.changed", "screen": "menu", "is_display_on": True, "force": False},
        {"type": "menu.refresh"},
        {"type": "menu.navigate", "command": "page_next"},
    ]

    def _run_once():
        for intent in intents:
            handler.apply(intent)

    return _measure("ui_intent.apply.mixed", iterations, _run_once)


def main() -> int:
    parser = argparse.ArgumentParser(description="Homescreen performance guard checks")
    parser.add_argument("--iterations", type=int, default=300, help="Iterations per check (default: 300)")
    parser.add_argument(
        "--max-p95-ms",
        type=float,
        default=20.0,
        help="Fail when any p95 exceeds this many milliseconds (default: 20)",
    )
    args = parser.parse_args()

    print(f"[perf] project root: {ROOT}")
    print(f"[perf] python: {sys.version.split()[0]}")
    print(f"[perf] iterations: {args.iterations}")

    checks = [
        _check_import_cost(args.iterations),
        _check_router_cost(args.iterations),
        _check_ui_intent_cost(args.iterations),
    ]

    worst_p95 = max(p95 for _, p95, _ in checks)
    if worst_p95 > args.max_p95_ms:
        print(f"[perf] FAILED: p95 {worst_p95:.3f}ms exceeds threshold {args.max_p95_ms:.3f}ms")
        return 1

    print(f"[perf] OK: worst p95 {worst_p95:.3f}ms <= {args.max_p95_ms:.3f}ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
