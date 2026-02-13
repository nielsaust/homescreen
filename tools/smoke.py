#!/usr/bin/env python3
"""Fast, side-effect-light smoke checks for local development."""

from __future__ import annotations

import importlib
import argparse
import os
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CORE_MODULES = [
    "main",
    "settings",
    "device_states",
    "display_controller",
    "touch_controller",
    "mqtt_controller",
    "weather_screen",
    "music_screen",
    "menu_screen",
    "core.event_bus",
    "core.events",
    "core.reducer",
    "core.state",
    "core.store",
    "app.controllers.action_dispatcher",
    "app.ui.widgets.network_status_widget",
]

CORE_FILES = [
    "main.py",
    "settings.py",
    "device_states.py",
    "display_controller.py",
    "touch_controller.py",
    "mqtt_controller.py",
    "weather_screen.py",
    "music_screen.py",
    "menu_screen.py",
    "core/event_bus.py",
    "core/events.py",
    "core/reducer.py",
    "core/state.py",
    "core/store.py",
    "app/controllers/action_dispatcher.py",
    "app/ui/widgets/network_status_widget.py",
]


def _compile_files() -> list[str]:
    errors: list[str] = []
    for filename in CORE_FILES:
        try:
            py_compile.compile(str(ROOT / filename), doraise=True)
        except Exception as exc:  # pragma: no cover
            errors.append(f"Compile failed for {filename}: {exc}")
    return errors


def _import_modules() -> list[str]:
    errors: list[str] = []
    for module_name in CORE_MODULES:
        try:
            importlib.import_module(module_name)
        except Exception as exc:
            errors.append(f"Import failed for {module_name}: {exc}")
    return errors


def _load_settings() -> list[str]:
    errors: list[str] = []
    settings_file = "settings.json" if (ROOT / "settings.json").exists() else "settings.json.example"

    try:
        from settings import Settings

        Settings(settings_file)
    except Exception as exc:
        errors.append(f"Settings load failed ({settings_file}): {exc}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Homescreen smoke tests")
    parser.add_argument(
        "--compile-only",
        action="store_true",
        help="Only run syntax/compile checks (no imports, no settings load).",
    )
    args = parser.parse_args()

    os.chdir(ROOT)
    print(f"[smoke] project root: {ROOT}")
    print(f"[smoke] python: {sys.version.split()[0]}")

    errors: list[str] = []
    errors.extend(_compile_files())
    if not args.compile_only:
        errors.extend(_import_modules())
        errors.extend(_load_settings())

    if errors:
        for error in errors:
            print(f"[smoke][error] {error}")
        print("[smoke] FAILED")
        return 1

    print("[smoke] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
