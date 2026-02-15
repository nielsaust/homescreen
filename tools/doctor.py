#!/usr/bin/env python3
"""Environment and configuration checks for local and Raspberry Pi runs."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_IMPORTS = [
    "tkinter",
    "PIL",
    "paho.mqtt.client",
    "requests",
    "aiohttp",
    "psutil",
    "ping3",
]

REQUIRED_SETTINGS_KEYS = [
    "screen_width",
    "screen_height",
    "mqtt_broker",
    "mqtt_port",
    "mqtt_user",
    "mqtt_password",
    "mqtt_topic_music",
    "mqtt_topic_devices",
    "weather_api_key",
    "weather_city_id",
]


def _check_imports() -> list[str]:
    errors: list[str] = []
    hints: list[str] = []
    for module_name in REQUIRED_IMPORTS:
        try:
            importlib.import_module(module_name)
        except Exception as exc:  # pragma: no cover
            errors.append(f"Missing import '{module_name}': {exc}")
            if module_name == "tkinter":
                system = platform.system()
                py = f"{sys.version_info.major}.{sys.version_info.minor}"
                if system == "Darwin":
                    hints.append(
                        f"Install Tk for Homebrew Python: brew install python-tk@{py}"
                    )
                elif system == "Linux":
                    hints.append("Install Tk package: sudo apt install -y python3-tk")
                else:
                    hints.append("Install Tk support for your Python distribution.")
    if hints:
        errors.extend([f"Hint: {hint}" for hint in hints])
    return errors


def _load_settings() -> tuple[dict, Path] | tuple[None, None]:
    primary = ROOT / "settings.json"
    fallback = ROOT / "settings.json.example"

    settings_file = primary if primary.exists() else fallback
    if not settings_file.exists():
        return None, None

    try:
        return json.loads(settings_file.read_text()), settings_file
    except json.JSONDecodeError:
        return None, settings_file


def _check_settings() -> list[str]:
    errors: list[str] = []
    data, path = _load_settings()
    if data is None:
        if path is None:
            errors.append("Missing both settings.json and settings.json.example")
        else:
            errors.append(f"Invalid JSON in {path}")
        return errors

    missing = [key for key in REQUIRED_SETTINGS_KEYS if key not in data]
    if missing:
        errors.append(f"Missing settings keys in {path}: {', '.join(missing)}")

    if bool(data.get("do_sentry_logging", False)):
        if not str(data.get("sentry_dsn", "")).strip():
            errors.append("Sentry enabled but sentry_dsn is empty")
        try:
            importlib.import_module("sentry_sdk")
        except Exception as exc:  # pragma: no cover
            errors.append(f"Sentry enabled but sentry-sdk import failed: {exc}")

    return errors


def _check_repo_files() -> list[str]:
    errors: list[str] = []
    required_files = [
        "main.py",
        "app/config/settings.py",
        "app/controllers/display_controller.py",
        "app/controllers/mqtt_controller.py",
        "app/observability/logger.py",
        "app/observability/sentry_setup.py",
    ]
    for filename in required_files:
        if not (ROOT / filename).exists():
            errors.append(f"Required file missing: {filename}")
    return errors


def _device_checks() -> list[str]:
    warnings: list[str] = []
    if platform.system() != "Linux":
        warnings.append("Device mode expected Linux (Raspberry Pi).")
        return warnings

    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.exists():
        text = cpuinfo.read_text(errors="ignore").lower()
        if "raspberry pi" not in text and "bcm" not in text:
            warnings.append("Linux detected but Raspberry Pi hardware marker not found.")
    else:
        warnings.append("/proc/cpuinfo not available; cannot verify Raspberry Pi hardware.")

    return warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Homescreen environment checker")
    parser.add_argument("--device", action="store_true", help="Run extra Raspberry Pi checks")
    args = parser.parse_args()

    print(f"[doctor] project root: {ROOT}")
    print(f"[doctor] python: {sys.version.split()[0]}")
    print(f"[doctor] platform: {platform.system()} {platform.release()}")

    errors: list[str] = []
    warnings: list[str] = []

    errors.extend(_check_repo_files())
    errors.extend(_check_imports())
    errors.extend(_check_settings())
    if args.device:
        warnings.extend(_device_checks())

    if warnings:
        for warning in warnings:
            print(f"[doctor][warn] {warning}")

    if errors:
        for error in errors:
            print(f"[doctor][error] {error}")
        print("[doctor] FAILED")
        return 1

    print("[doctor] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
