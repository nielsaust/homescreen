#!/usr/bin/env python3
"""Interactive project configuration wizard for common integrations."""

from __future__ import annotations

import json
import platform
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SETTINGS_PATH = ROOT / "settings.json"
SETTINGS_EXAMPLE_PATH = ROOT / "settings.json.example"


def _load_settings() -> dict:
    if SETTINGS_PATH.exists():
        return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    return json.loads(SETTINGS_EXAMPLE_PATH.read_text(encoding="utf-8"))


def _save_settings(data: dict) -> None:
    SETTINGS_PATH.write_text(json.dumps(data, indent=4) + "\n", encoding="utf-8")


def _prompt(text: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{text}{suffix}: ").strip()
    return value if value else default


def _prompt_int(text: str, default: int) -> int:
    while True:
        raw = _prompt(text, str(default))
        try:
            return int(raw)
        except ValueError:
            print("Please enter a valid number.")


def _prompt_bool(text: str, default: bool) -> bool:
    default_text = "y" if default else "n"
    while True:
        raw = _prompt(f"{text} (y/n)", default_text).lower()
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("Please answer y or n.")


def configure_mqtt_base(settings: dict) -> None:
    print("\n[configuration] MQTT base settings")
    settings["mqtt_broker"] = _prompt("MQTT broker host/ip", str(settings.get("mqtt_broker", "127.0.0.1")))
    settings["mqtt_port"] = _prompt_int("MQTT port", int(settings.get("mqtt_port", 1883)))
    settings["mqtt_user"] = _prompt("MQTT username", str(settings.get("mqtt_user", "")))
    settings["mqtt_password"] = _prompt("MQTT password", str(settings.get("mqtt_password", "")))
    settings["mqtt_qos"] = _prompt_int("MQTT QoS", int(settings.get("mqtt_qos", 2)))
    print("[configuration] MQTT base updated.")


def configure_music(settings: dict) -> None:
    print("\n[configuration] Music integration")
    print("Expected payload shape is documented in docs/music-integration.md.")
    settings["mqtt_topic_music"] = _prompt("MQTT topic to receive music state", str(settings.get("mqtt_topic_music", "music")))
    settings["home_assistant_api_base_url"] = _prompt(
        "Home Assistant API base URL (for album art proxy)",
        str(settings.get("home_assistant_api_base_url", "https://homeassistant.local")),
    )
    settings["media_show_titles"] = _prompt_bool("Show title/artist overlays", bool(settings.get("media_show_titles", True)))
    settings["media_sanitize_titles"] = _prompt_bool(
        "Sanitize long/noisy titles",
        bool(settings.get("media_sanitize_titles", True)),
    )
    print("[configuration] Music integration updated.")


def configure_weather(settings: dict) -> None:
    print("\n[configuration] Weather integration")
    print("OpenWeather setup: https://openweathermap.org/")
    settings["weather_api_key"] = _prompt("OpenWeather API key", str(settings.get("weather_api_key", "")))
    settings["weather_city_id"] = _prompt("OpenWeather city id", str(settings.get("weather_city_id", "")))
    settings["weather_langage"] = _prompt("Weather language (e.g. nl/en)", str(settings.get("weather_langage", "nl")))
    print("[configuration] Weather integration updated.")


def configure_smart_home(settings: dict) -> None:
    print("\n[configuration] Smart-home MQTT integration")
    print("State topics are consumed by the app; action topics are published by the app.")
    settings["mqtt_topic_devices"] = _prompt(
        "State topic for device states",
        str(settings.get("mqtt_topic_devices", "screen_commands/incoming")),
    )
    settings["mqtt_topic_actions_outgoing"] = _prompt(
        "Action topic for outgoing commands",
        str(settings.get("mqtt_topic_actions_outgoing", "screen_commands/outgoing")),
    )
    settings["mqtt_topic_update_music"] = _prompt(
        "Action topic to request music state refresh",
        str(settings.get("mqtt_topic_update_music", "screen_commands/update_music")),
    )
    settings["mqtt_topic_doorbell_command"] = _prompt(
        "Action topic for doorbell command",
        str(settings.get("mqtt_topic_doorbell_command", "screen_commands/doorbell")),
    )
    print("[configuration] Smart-home integration updated.")


def configure_services() -> None:
    system_name = platform.system().lower()
    if system_name != "linux":
        print("\n[configuration] Service setup is only available on Linux/systemd. Skipping on this platform.")
        return

    run = _prompt_bool(
        "Run Linux service setup helper now (systemd autostart + optional deploy timer)?",
        False,
    )
    if not run:
        return
    subprocess.run(["python3", "tools/service_setup.py", "wizard"], cwd=ROOT, check=False)


def main() -> int:
    settings = _load_settings()
    dirty = False

    while True:
        print("\n=== Homescreen Configuration ===")
        print("1) MQTT base")
        print("2) Music integration")
        print("3) Weather integration")
        print("4) Smart-home integration")
        print("5) Auto-start/update setup (Linux/systemd)")
        print("6) Save and exit")
        print("7) Exit without saving")

        choice = _prompt("Choose option", "6")
        if choice == "1":
            configure_mqtt_base(settings)
            dirty = True
        elif choice == "2":
            configure_music(settings)
            dirty = True
        elif choice == "3":
            configure_weather(settings)
            dirty = True
        elif choice == "4":
            configure_smart_home(settings)
            dirty = True
        elif choice == "5":
            configure_services()
        elif choice == "6":
            _save_settings(settings)
            print("[configuration] Saved to settings.json")
            return 0
        elif choice == "7":
            if dirty and not _prompt_bool("Discard unsaved changes?", False):
                continue
            print("[configuration] Exiting without saving.")
            return 0
        else:
            print("Invalid option.")


if __name__ == "__main__":
    raise SystemExit(main())
