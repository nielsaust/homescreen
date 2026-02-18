#!/usr/bin/env python3
"""Interactive project configuration wizard for common integrations."""

from __future__ import annotations

import json
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SETTINGS_PATH = ROOT / "local_config" / "settings.json"
SETTINGS_EXAMPLE_PATH = ROOT / "settings.json.example"
MENU_PATH = ROOT / "local_config" / "menu.json"
MENU_EXAMPLE_PATH = ROOT / "local_config" / "menu.json.example"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config.mqtt_topics import load_mqtt_topics, save_local_mqtt_topics

MUSIC_BUTTON_REQUIREMENTS: dict[str, list[str]] = {
    "music": ["enable_mqtt", "enable_music"],
    "music_play_pause": ["enable_mqtt", "enable_music"],
    "media_show_titles": ["enable_mqtt", "enable_music"],
    "media_show_album": ["enable_mqtt", "enable_music"],
    "media_sanitize_titles": ["enable_mqtt", "enable_music"],
}

WEATHER_BUTTON_REQUIREMENTS: dict[str, list[str]] = {
    "weather_options": ["enable_weather"],
    "show_weather_on_idle": ["enable_weather"],
}

MUSIC_ACTION_SPECS: dict[str, dict] = {
    "music_play_pause": {"kind": "media", "op": "play_pause"},
    "music_volume_up": {"kind": "media", "op": "volume", "arg": "up"},
    "music_volume_down": {"kind": "media", "op": "volume", "arg": "down"},
    "music_next": {"kind": "media", "op": "skip", "arg": "next"},
    "music_previous": {"kind": "media", "op": "skip", "arg": "previous"},
    "music_show_title": {"kind": "custom", "name": "music_show_title"},
    "media_show_titles": {"kind": "setting_toggle", "attr": "media_show_titles"},
    "media_show_album": {"kind": "setting_toggle", "attr": "media_show_album"},
    "media_sanitize_titles": {"kind": "setting_toggle", "attr": "media_sanitize_titles"},
}

WEATHER_ACTION_SPECS: dict[str, dict] = {
    "show_weather_on_idle": {"kind": "setting_toggle", "attr": "show_weather_on_idle"},
}

MUSIC_STATE_SPECS: list[dict] = [
    {
        "button_id": "music_play_pause",
        "type": "music_state",
        "state": "playing",
        "action_text": "[music_action]",
        "on_text": "Pauzeer",
        "off_text": "Speel",
    },
    {"button_id": "media_show_titles", "type": "setting_bool", "source": "media_show_titles", "default": True},
    {"button_id": "media_show_album", "type": "setting_bool", "source": "media_show_album", "default": True},
    {
        "button_id": "media_sanitize_titles",
        "type": "setting_bool",
        "source": "media_sanitize_titles",
        "default": True,
    },
]

WEATHER_STATE_SPECS: list[dict] = [
    {"button_id": "show_weather_on_idle", "type": "setting_bool", "source": "show_weather_on_idle", "default": False},
]


def _load_settings() -> dict:
    if SETTINGS_PATH.exists():
        return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    return json.loads(SETTINGS_EXAMPLE_PATH.read_text(encoding="utf-8"))


def _save_settings(data: dict) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(data, indent=4) + "\n", encoding="utf-8")


def _load_topics(settings: dict) -> dict:
    _ = settings
    return load_mqtt_topics()


def _save_topics(topics: dict) -> None:
    save_local_mqtt_topics(topics)


def _load_menu_config() -> dict:
    if MENU_PATH.exists():
        return json.loads(MENU_PATH.read_text(encoding="utf-8"))
    if MENU_EXAMPLE_PATH.exists():
        return json.loads(MENU_EXAMPLE_PATH.read_text(encoding="utf-8"))
    return {
        "menu_schema": [],
        "button_setting_requirements": {},
        "action_specs": {},
        "state_specs": [],
    }


def _save_menu_config(data: dict) -> None:
    MENU_PATH.parent.mkdir(parents=True, exist_ok=True)
    MENU_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _find_top_level_item(menu_schema: list[dict], item_id: str) -> dict | None:
    for item in menu_schema:
        if item.get("id") == item_id:
            return item
    return None


def _remove_top_level_item(menu_schema: list[dict], item_id: str) -> None:
    menu_schema[:] = [item for item in menu_schema if item.get("id") != item_id]


def _upsert_state_spec(state_specs: list[dict], spec: dict) -> None:
    button_id = str(spec.get("button_id", "")).strip()
    if not button_id:
        return
    for idx, current in enumerate(state_specs):
        if str(current.get("button_id", "")).strip() == button_id:
            state_specs[idx] = spec
            return
    state_specs.append(spec)


def _remove_state_spec(state_specs: list[dict], button_id: str) -> None:
    state_specs[:] = [spec for spec in state_specs if str(spec.get("button_id", "")).strip() != button_id]


def _ensure_music_menu_contracts(config: dict) -> None:
    button_reqs = config.setdefault("button_setting_requirements", {})
    action_specs = config.setdefault("action_specs", {})
    state_specs = config.setdefault("state_specs", [])
    for button_id in MUSIC_BUTTON_REQUIREMENTS:
        button_reqs.pop(button_id, None)
    for action_id in MUSIC_ACTION_SPECS:
        action_specs.pop(action_id, None)
    for spec in MUSIC_STATE_SPECS:
        _remove_state_spec(state_specs, str(spec.get("button_id", "")))


def _ensure_weather_menu_contracts(config: dict) -> None:
    button_reqs = config.setdefault("button_setting_requirements", {})
    action_specs = config.setdefault("action_specs", {})
    state_specs = config.setdefault("state_specs", [])
    for button_id in WEATHER_BUTTON_REQUIREMENTS:
        button_reqs.pop(button_id, None)
    for action_id in WEATHER_ACTION_SPECS:
        action_specs.pop(action_id, None)
    for spec in WEATHER_STATE_SPECS:
        _remove_state_spec(state_specs, str(spec.get("button_id", "")))


def _remove_music_menu_contracts(config: dict) -> None:
    button_reqs = config.setdefault("button_setting_requirements", {})
    for button_id in MUSIC_BUTTON_REQUIREMENTS:
        button_reqs.pop(button_id, None)
    state_specs = config.setdefault("state_specs", [])
    for spec in MUSIC_STATE_SPECS:
        _remove_state_spec(state_specs, str(spec.get("button_id", "")))


def _remove_weather_menu_contracts(config: dict) -> None:
    button_reqs = config.setdefault("button_setting_requirements", {})
    for button_id in WEATHER_BUTTON_REQUIREMENTS:
        button_reqs.pop(button_id, None)
    state_specs = config.setdefault("state_specs", [])
    for spec in WEATHER_STATE_SPECS:
        _remove_state_spec(state_specs, str(spec.get("button_id", "")))


def _music_menu_item() -> dict:
    return {
        "id": "music",
        "text": "Muziek",
        "image": "music.png",
        "action": "music_menu",
        "order": 400,
        "setting_requirements": ["enable_mqtt", "enable_music"],
        "screen": [
            {"id": "music_back", "text": "Terug", "image": "back.png", "action": "back", "order": 10},
            {"id": "music_volume_up", "text": "Harder", "image": "volume-up.png", "action": "music_volume_up", "action_spec": {"kind": "media", "op": "volume", "arg": "up"}, "order": 20},
            {"id": "music_play_pause", "text": "[music_action] muziek", "image": "play.png", "action": "music_play_pause", "action_spec": {"kind": "media", "op": "play_pause"}, "state_spec": {"type": "music_state", "state": "playing", "action_text": "[music_action]", "on_text": "Pauzeer", "off_text": "Speel"}, "order": 30},
            {"id": "music_volume_down", "text": "Zachter", "image": "volume-down.png", "action": "music_volume_down", "action_spec": {"kind": "media", "op": "volume", "arg": "down"}, "order": 40},
            {"id": "music_previous", "text": "Vorig nummer", "image": "backward.png", "action": "music_previous", "action_spec": {"kind": "media", "op": "skip", "arg": "previous"}, "order": 50},
            {"id": "music_next", "text": "Volgend nummer", "image": "forward.png", "action": "music_next", "action_spec": {"kind": "media", "op": "skip", "arg": "next"}, "order": 60},
            {"id": "music_show_title", "text": "Toon muziek details", "image": "detail.png", "action": "music_show_title", "action_spec": {"kind": "custom", "name": "music_show_title"}, "cancel_close": True, "order": 70},
            {"id": "media_show_titles", "text": "Toon media titels", "image": "text.png", "action": "media_show_titles", "action_spec": {"kind": "setting_toggle", "attr": "media_show_titles"}, "state_spec": {"type": "setting_bool", "source": "media_show_titles", "default": True}, "setting_requirements": ["enable_mqtt", "enable_music"], "order": 80},
            {"id": "media_show_album", "text": "Toon album titel", "image": "text.png", "action": "media_show_album", "action_spec": {"kind": "setting_toggle", "attr": "media_show_album"}, "state_spec": {"type": "setting_bool", "source": "media_show_album", "default": True}, "setting_requirements": ["enable_mqtt", "enable_music"], "order": 90},
            {"id": "media_sanitize_titles", "text": "Schoon titels op", "image": "text.png", "action": "media_sanitize_titles", "action_spec": {"kind": "setting_toggle", "attr": "media_sanitize_titles"}, "state_spec": {"type": "setting_bool", "source": "media_sanitize_titles", "default": True}, "setting_requirements": ["enable_mqtt", "enable_music"], "order": 100},
        ],
    }


def _weather_menu_item() -> dict:
    return {
        "id": "weather_options",
        "text": "Weer",
        "image": "weather.png",
        "action": "open_page",
        "order": 500,
        "setting_requirements": ["enable_weather"],
        "screen": [
            {"id": "weather_back", "text": "Terug", "image": "back.png", "action": "back", "order": 10},
            {"id": "show_weather_on_idle", "text": "Toon weer als idle", "image": "weather.png", "action": "show_weather_on_idle", "action_spec": {"kind": "setting_toggle", "attr": "show_weather_on_idle"}, "state_spec": {"type": "setting_bool", "source": "show_weather_on_idle", "default": False}, "setting_requirements": ["enable_weather"], "order": 20},
        ],
    }


def _upsert_menu_item(menu_schema: list[dict], item: dict, ask_overwrite: bool) -> bool:
    existing = _find_top_level_item(menu_schema, item.get("id", ""))
    if existing is None:
        menu_schema.append(item)
        return True
    if existing == item:
        return False
    if ask_overwrite and not _prompt_bool(
        f"Menu item '{item.get('id')}' already exists. Overwrite with default item?",
        False,
    ):
        return False
    existing.clear()
    existing.update(item)
    return True


def _apply_feature_menu_defaults(settings: dict, ask_overwrite: bool) -> None:
    config = _load_menu_config()
    before_config = json.dumps(config, sort_keys=True, ensure_ascii=False)
    menu_schema = config.setdefault("menu_schema", [])
    changed = False
    if bool(settings.get("enable_music", False)):
        _ensure_music_menu_contracts(config)
        changed = _upsert_menu_item(menu_schema, _music_menu_item(), ask_overwrite) or changed
    else:
        before = len(menu_schema)
        _remove_top_level_item(menu_schema, "music")
        _remove_music_menu_contracts(config)
        changed = len(menu_schema) != before or changed

    if bool(settings.get("enable_weather", False)):
        _ensure_weather_menu_contracts(config)
        changed = _upsert_menu_item(menu_schema, _weather_menu_item(), ask_overwrite) or changed
    else:
        before = len(menu_schema)
        _remove_top_level_item(menu_schema, "weather_options")
        _remove_weather_menu_contracts(config)
        changed = len(menu_schema) != before or changed

    after_config = json.dumps(config, sort_keys=True, ensure_ascii=False)
    if changed or before_config != after_config:
        _save_menu_config(config)
        print("[configuration] Menu defaults updated for selected features.")


def _prompt(text: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        value = input(f"{text}{suffix}: ").strip()
    except KeyboardInterrupt as exc:
        raise KeyboardInterrupt from exc
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


def _prompt_choice(text: str, options: list[str], default: str) -> str:
    option_set = {opt.lower() for opt in options}
    while True:
        raw = _prompt(f"{text} ({'/'.join(options)})", default).strip().lower()
        if raw in option_set:
            return raw
        print(f"Please choose one of: {', '.join(options)}.")


def configure_mqtt_base(settings: dict) -> None:
    print("\n[configuration] MQTT base settings")
    settings["enable_mqtt"] = _prompt_bool("Enable MQTT integration", bool(settings.get("enable_mqtt", False)))
    if not settings["enable_mqtt"]:
        print("[configuration] MQTT disabled. Music and smart-home integrations will stay inactive.")
        return
    settings["mqtt_broker"] = _prompt("MQTT broker host/ip", str(settings.get("mqtt_broker", "127.0.0.1")))
    settings["mqtt_port"] = _prompt_int("MQTT port", int(settings.get("mqtt_port", 1883)))
    settings["mqtt_user"] = _prompt("MQTT username", str(settings.get("mqtt_user", "")))
    settings["mqtt_password"] = _prompt("MQTT password", str(settings.get("mqtt_password", "")))
    settings["mqtt_qos"] = _prompt_int("MQTT QoS", int(settings.get("mqtt_qos", 2)))
    print("[configuration] MQTT base updated.")


def configure_music(settings: dict, topics: dict) -> None:
    print("\n[configuration] Music integration")
    settings["enable_music"] = _prompt_bool("Enable music integration", bool(settings.get("enable_music", False)))
    if not settings["enable_music"]:
        print("[configuration] Music integration disabled.")
        return
    if not bool(settings.get("enable_mqtt", False)):
        print("First complete MQTT setup.")
        return
    print("Expected payload shape is documented in docs/music-integration.md.")
    topics["music"] = _prompt("MQTT topic to receive music state", str(topics.get("music", "music")))
    settings["home_assistant_api_base_url"] = _prompt(
        "Home Assistant API base URL (for album art proxy)",
        str(settings.get("home_assistant_api_base_url", "https://homeassistant.local")),
    )
    settings["media_show_titles"] = _prompt_bool("Show title/artist overlays", bool(settings.get("media_show_titles", True)))
    settings["media_sanitize_titles"] = _prompt_bool(
        "Sanitize long/noisy titles",
        bool(settings.get("media_sanitize_titles", True)),
    )
    settings["media_show_album"] = _prompt_bool(
        "Show album title in music overlays",
        bool(settings.get("media_show_album", True)),
    )
    _apply_feature_menu_defaults(settings, ask_overwrite=True)
    print("[configuration] Music integration updated.")


def configure_weather(settings: dict) -> None:
    print("\n[configuration] Weather integration")
    settings["enable_weather"] = _prompt_bool("Enable weather integration", bool(settings.get("enable_weather", False)))
    if not settings["enable_weather"]:
        settings["show_weather_on_idle"] = False
        print("[configuration] Weather integration disabled.")
        return
    print("OpenWeather setup: https://openweathermap.org/")
    settings["show_weather_on_idle"] = _prompt_bool(
        "Display weather when idle",
        bool(settings.get("show_weather_on_idle", True)),
    )
    settings["weather_api_key"] = _prompt("OpenWeather API key", str(settings.get("weather_api_key", "")))
    settings["weather_city_id"] = _prompt("OpenWeather city id", str(settings.get("weather_city_id", "")))
    settings["weather_langage"] = _prompt("Weather language (e.g. nl/en)", str(settings.get("weather_langage", "nl")))
    locale_input = _prompt(
        "Date locale for weather clock (e.g. nl_NL.UTF-8, en_US.UTF-8; use 'system' for OS default)",
        str(settings.get("weather_time_locale", "nl_NL.UTF-8")),
    )
    if locale_input.strip().lower() == "system":
        locale_input = ""
    settings["weather_time_locale"] = locale_input
    settings["weather_date_format"] = _prompt(
        "Date format for weather clock (strftime, e.g. %-d %b or %a %-d %b)",
        str(settings.get("weather_date_format", "%-d %b")),
    )
    _apply_feature_menu_defaults(settings, ask_overwrite=True)
    print("[configuration] Weather integration updated.")


def configure_smart_home(settings: dict, topics: dict) -> None:
    print("\n[configuration] Smart-home MQTT integration")
    if not bool(settings.get("enable_mqtt", False)):
        print("First complete MQTT setup.")
        return
    print("State topics are consumed by the app; action topics are published by the app.")
    print("Tip: leave optional integration topics empty to disable that integration.")
    topics["devices"] = _prompt(
        "State topic for device states",
        str(topics.get("devices", "screen_commands/incoming")),
    )
    topics["actions_outgoing"] = _prompt(
        "Action topic for outgoing commands",
        str(topics.get("actions_outgoing", "screen_commands/outgoing")),
    )
    topics["alert"] = _prompt(
        "Alert topic (optional but recommended)",
        str(topics.get("alert", "screen_commands/alert")),
    )
    topics["update_music"] = _prompt(
        "Action topic to request music state refresh",
        str(topics.get("update_music", "screen_commands/update_music")),
    )
    enable_doorbell = _prompt_bool("Enable doorbell integration topics?", bool(topics.get("doorbell")))
    if enable_doorbell:
        topics["doorbell"] = _prompt(
            "Doorbell state/event topic",
            str(topics.get("doorbell", "doorbell")),
        )
        default_command_topic = str(topics.get("doorbell_command", "")).strip() or "screen_commands/doorbell"
        topics["doorbell_command"] = _prompt(
            "Action topic for doorbell command",
            default_command_topic,
        )
    else:
        topics["doorbell"] = ""
        topics["doorbell_command"] = ""

    enable_calendar = _prompt_bool("Enable calendar integration topic?", bool(topics.get("calendar")))
    if enable_calendar:
        topics["calendar"] = _prompt(
            "Calendar topic",
            str(topics.get("calendar", "calendar")),
        )
    else:
        topics["calendar"] = ""

    enable_printer = _prompt_bool("Enable 3D printer integration topics?", bool(topics.get("printer_progress")))
    if enable_printer:
        topics["printer_progress"] = _prompt(
            "Printer progress topic",
            str(topics.get("printer_progress", "octoPrint/progress/printing")),
        )
        topics["print_start"] = _prompt(
            "Printer start topic",
            str(topics.get("print_start", "octoPrint/event/PrintStarted")),
        )
        topics["print_done"] = _prompt(
            "Printer done topic",
            str(topics.get("print_done", "octoPrint/event/PrintDone")),
        )
        topics["print_cancelled"] = _prompt(
            "Printer cancelled topic",
            str(topics.get("print_cancelled", "octoPrint/event/PrintCancelled")),
        )
        topics["print_change_filament"] = _prompt(
            "Printer filament-change topic",
            str(topics.get("print_change_filament", "octoPrint/event/FilamentChange")),
        )
        topics["print_change_z"] = _prompt(
            "Printer Z-change topic",
            str(topics.get("print_change_z", "octoPrint/event/ZChange")),
        )
    else:
        topics["printer_progress"] = ""
        topics["print_start"] = ""
        topics["print_done"] = ""
        topics["print_cancelled"] = ""
        topics["print_change_filament"] = ""
        topics["print_change_z"] = ""

    print("[configuration] Smart-home integration updated.")


def configure_services() -> None:
    system_name = platform.system().lower()
    if system_name != "linux":
        print("\n[configuration] Service setup is only available on Linux/systemd. Skipping on this platform.")
        return

    run = _prompt_bool(
        "Run Linux service setup helper now (systemd autostart, X display readiness, optional deploy timer)?",
        False,
    )
    if not run:
        return
    subprocess.run(["python3", "tools/service_setup.py", "wizard"], cwd=ROOT, check=False)


def main() -> int:
    settings = _load_settings()
    topics = _load_topics(settings)
    dirty = False

    try:
        while True:
            print("\n=== Homescreen Configuration ===")
            print("1) MQTT base")
            print("2) Music integration")
            print("3) Weather integration")
            print("4) Smart-home integration")
            print("5) Auto-start/update setup (Linux/systemd, recommended on Pi)")
            print("6) Save and exit")
            print("7) Exit without saving")

            choice = _prompt("Choose option", "6")
            if choice == "1":
                configure_mqtt_base(settings)
                dirty = True
            elif choice == "2":
                configure_music(settings, topics)
                dirty = True
            elif choice == "3":
                configure_weather(settings)
                dirty = True
            elif choice == "4":
                configure_smart_home(settings, topics)
                dirty = True
            elif choice == "5":
                configure_services()
            elif choice == "6":
                _save_settings(settings)
                _save_topics(topics)
                print("[configuration] Saved to local_config/settings.json")
                print("[configuration] Saved to local_config/mqtt_topics.json")
                return 0
            elif choice == "7":
                if dirty and not _prompt_bool("Discard unsaved changes?", False):
                    continue
                print("[configuration] Exiting without saving.")
                return 0
            else:
                print("Invalid option.")
    except KeyboardInterrupt:
        print("\n[configuration] Interrupted by user. No changes saved.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
