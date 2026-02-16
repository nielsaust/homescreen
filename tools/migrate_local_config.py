#!/usr/bin/env python3
"""Migrate legacy local_config/settings.json fields into dedicated local config files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config.mqtt_topics import TOPIC_DEFAULTS, save_local_mqtt_topics

SETTINGS_PATH = ROOT / "local_config" / "settings.json"
CAMERAS_PATH = ROOT / "local_config" / "cameras.json"

CAMERA_LEGACY_KEYS = (
    "doorbell_url",
    "doorbell_path",
    "doorbell_username",
    "doorbell_password",
    "printer_url",
)
OTHER_LEGACY_KEYS = (
    "menu_profile",
)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _migrate_topics(settings: dict) -> tuple[dict, list[str]]:
    topics = {}
    moved: list[str] = []
    for key in TOPIC_DEFAULTS:
        if key in settings:
            topics[key] = settings.pop(key)
            moved.append(key)
    if topics:
        save_local_mqtt_topics(topics)
    return topics, moved


def _migrate_cameras(settings: dict) -> tuple[dict, list[str]]:
    cameras_file = _load_json(CAMERAS_PATH) if CAMERAS_PATH.exists() else {"cameras": {}}
    cameras = cameras_file.get("cameras")
    if not isinstance(cameras, dict):
        cameras = {}

    moved: list[str] = []

    doorbell_url = str(settings.get("doorbell_url", "")).strip()
    doorbell_path = str(settings.get("doorbell_path", "")).strip()
    if doorbell_url:
        url = doorbell_url
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"http://{url}"
        if doorbell_path:
            url = f"{url}{doorbell_path}"
        existing = cameras.get("doorbell") if isinstance(cameras.get("doorbell"), dict) else {}
        existing.update(
            {
                "url": url,
                "username": settings.get("doorbell_username", ""),
                "password": settings.get("doorbell_password", ""),
                "overlay_data": {"active": True},
            }
        )
        cameras["doorbell"] = existing
        moved.extend(["doorbell_url", "doorbell_path", "doorbell_username", "doorbell_password"])

    printer_url = str(settings.get("printer_url", "")).strip()
    if printer_url:
        existing = cameras.get("printer") if isinstance(cameras.get("printer"), dict) else {}
        existing.update({"url": printer_url, "overlay_data": {}})
        cameras["printer"] = existing
        moved.append("printer_url")

    if moved:
        cameras_file["cameras"] = cameras
        _save_json(CAMERAS_PATH, cameras_file)
        for key in CAMERA_LEGACY_KEYS:
            settings.pop(key, None)

    return cameras_file, moved


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate legacy local settings to local_config files.")
    parser.add_argument("--apply", action="store_true", help="Write changes instead of preview.")
    args = parser.parse_args()

    settings = _load_json(SETTINGS_PATH)
    if not settings:
        print("[migrate-local] no local_config/settings.json found or file is empty")
        return 0

    settings_copy = dict(settings)
    _, moved_topics = _migrate_topics(settings_copy)
    _, moved_cameras = _migrate_cameras(settings_copy)

    removed_other = []
    for key in OTHER_LEGACY_KEYS:
        if key in settings_copy:
            settings_copy.pop(key, None)
            removed_other.append(key)

    print("[migrate-local] preview")
    print(f"- moved mqtt topic keys: {len(moved_topics)}")
    print(f"- moved camera keys: {len(moved_cameras)}")
    print(f"- removed deprecated keys: {len(removed_other)}")
    if moved_topics:
        print(f"  topics: {', '.join(sorted(moved_topics))}")
    if moved_cameras:
        print(f"  camera keys: {', '.join(sorted(moved_cameras))}")
    if removed_other:
        print(f"  deprecated keys: {', '.join(sorted(removed_other))}")

    if not args.apply:
        print("[migrate-local] dry run only. Re-run with --apply to persist.")
        return 0

    _save_json(SETTINGS_PATH, settings_copy)
    print("[migrate-local] wrote local_config/settings.json")
    print("[migrate-local] wrote local_config/mqtt_topics.json (if topic keys existed)")
    print("[migrate-local] wrote local_config/cameras.json (if camera keys existed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
