#!/usr/bin/env python3
"""Contract checks between menu schema, action specs, state resolver and settings."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.controllers.action_registry import ACTION_SPECS
from app.ui.menu_registry import MENU_SCHEMA
from app.ui.menu_config_loader import get_state_specs

SETTINGS_EXAMPLE = ROOT / "settings.json.example"
SETTINGS_LOCAL = ROOT / "local_config" / "settings.json"
QR_ITEMS_LOCAL = ROOT / "local_config" / "qr_items.json"
CAMERAS_LOCAL = ROOT / "local_config" / "cameras.json"
MQTT_TOPICS_LOCAL = ROOT / "local_config" / "mqtt_topics.json"
MQTT_TOPICS_EXAMPLE = ROOT / "local_config" / "mqtt_topics.json.example"
MQTT_ROUTES_LOCAL = ROOT / "local_config" / "mqtt_routes.json"
IMAGES_DIR = ROOT / "images" / "buttons"


def flatten_menu_entries(entries):
    out = []
    for entry in entries:
        out.append(entry)
        children = entry.get("screen") or []
        out.extend(flatten_menu_entries(children))
    return out


def extract_state_button_ids() -> set[str]:
    return {
        str(spec.get("button_id"))
        for spec in get_state_specs()
        if spec.get("button_id")
    }


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _camera_items() -> dict:
    payload = _load_json(CAMERAS_LOCAL)
    cameras = payload.get("cameras")
    return cameras if isinstance(cameras, dict) else {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate menu/action/state/settings contracts.")
    parser.parse_args()

    issues: list[str] = []
    warnings: list[str] = []
    all_entries = flatten_menu_entries(MENU_SCHEMA)

    # Duplicate ids are allowed when action is identical across submenus.
    # Hard-fail only when the same id maps to different actions.
    ids = [entry["id"] for entry in all_entries]
    duplicates = sorted({button_id for button_id in ids if ids.count(button_id) > 1})
    if duplicates:
        id_to_actions: dict[str, set[str]] = {}
        for entry in all_entries:
            id_to_actions.setdefault(entry["id"], set()).add(entry["action"])
        conflicting = sorted(button_id for button_id in duplicates if len(id_to_actions.get(button_id, set())) > 1)
        if conflicting:
            issues.append(f"Duplicate menu ids with conflicting actions: {conflicting}")
        else:
            warnings.append(f"Duplicate menu ids reused safely: {duplicates}")

    # Images must exist
    missing_images = sorted(
        {
            entry["image"]
            for entry in all_entries
            if not (IMAGES_DIR / entry["image"]).exists()
        }
    )
    if missing_images:
        issues.append(f"Missing images in images/buttons: {missing_images}")

    # Leaves must map to action specs
    missing_action_specs = sorted(
        {
            entry["action"]
            for entry in all_entries
            if not (entry.get("screen") or []) and entry["action"] not in ACTION_SPECS
        }
    )
    if missing_action_specs:
        issues.append(f"Leaf actions missing in ACTION_SPECS: {missing_action_specs}")

    state_button_ids = extract_state_button_ids()
    menu_button_ids = set(ids)
    missing_state_buttons = sorted(state_button_ids - menu_button_ids)
    if missing_state_buttons:
        issues.append(f"MenuStateResolver references unknown button ids: {missing_state_buttons}")

    # setting_toggle checks
    local_settings = _load_json(SETTINGS_LOCAL)
    example_settings = _load_json(SETTINGS_EXAMPLE)
    setting_toggle_actions = {
        action: spec["attr"]
        for action, spec in ACTION_SPECS.items()
        if spec.get("kind") == "setting_toggle"
    }
    menu_setting_toggles = {
        entry["id"]: setting_toggle_actions[entry["action"]]
        for entry in all_entries
        if entry["action"] in setting_toggle_actions
    }

    missing_state_specs = sorted(
        button_id for button_id in menu_setting_toggles if button_id not in state_button_ids
    )
    if missing_state_specs:
        warnings.append(f"Setting-toggle buttons missing state resolver spec: {missing_state_specs}")

    missing_settings_example = sorted(
        attr for attr in menu_setting_toggles.values() if attr not in example_settings
    )
    if missing_settings_example:
        issues.append(f"Missing keys in settings.json.example: {missing_settings_example}")

    if local_settings:
        missing_settings_local = sorted(
            attr for attr in menu_setting_toggles.values() if attr not in local_settings
        )
        if missing_settings_local:
            issues.append(f"Missing keys in settings.json: {missing_settings_local}")

    # linked config checks
    qr_items = _load_json(QR_ITEMS_LOCAL)
    cameras = _camera_items()
    mqtt_topics_local = _load_json(MQTT_TOPICS_LOCAL)
    mqtt_topics_example = _load_json(MQTT_TOPICS_EXAMPLE)
    mqtt_topics: dict = {}
    if isinstance(mqtt_topics_example.get("topics"), dict):
        mqtt_topics.update(mqtt_topics_example.get("topics"))
    if isinstance(mqtt_topics_local.get("topics"), dict):
        mqtt_topics.update(mqtt_topics_local.get("topics"))

    referenced_qr_ids = set()
    referenced_camera_ids = set()
    referenced_topic_keys = set()
    for action_id, spec in ACTION_SPECS.items():
        kind = str(spec.get("kind", "")).strip()
        if kind == "show_qr":
            item_id = str(spec.get("item_id", "")).strip()
            if item_id:
                referenced_qr_ids.add(item_id)
                if qr_items and item_id not in qr_items:
                    warnings.append(f"Action '{action_id}' references missing QR item: '{item_id}'")
        elif kind == "show_camera":
            camera_id = str(spec.get("camera_id", "")).strip()
            if camera_id:
                referenced_camera_ids.add(camera_id)
                if cameras and camera_id not in cameras:
                    warnings.append(f"Action '{action_id}' references missing camera: '{camera_id}'")
        elif kind in ("mqtt_action", "mqtt_message", "mqtt_publish"):
            topic_key = str(spec.get("topic_key", "")).strip()
            if topic_key:
                referenced_topic_keys.add(topic_key)
                if mqtt_topics and topic_key not in mqtt_topics:
                    issues.append(f"Action '{action_id}' references missing mqtt topic key: '{topic_key}'")

    if qr_items:
        orphan_qr = sorted(set(qr_items.keys()) - referenced_qr_ids)
        if orphan_qr:
            warnings.append(f"Orphan qr_items not referenced by menu actions: {orphan_qr}")
    if cameras:
        orphan_cameras = sorted(set(cameras.keys()) - referenced_camera_ids)
        if orphan_cameras:
            warnings.append(f"Orphan camera entries not referenced by menu actions: {orphan_cameras}")

    routes = _load_json(MQTT_ROUTES_LOCAL)
    route_topic_keys = set()
    for entry in routes.get("routes", []) if isinstance(routes.get("routes"), list) else []:
        if isinstance(entry, dict):
            key = str(entry.get("topic_key", "")).strip()
            if key:
                route_topic_keys.add(key)
                if mqtt_topics and key not in mqtt_topics:
                    issues.append(f"MQTT route references missing topic key: '{key}'")
    unused_topic_keys = sorted(set(mqtt_topics.keys()) - (referenced_topic_keys | route_topic_keys))
    if unused_topic_keys:
        warnings.append(f"MQTT topic keys defined but unused by menu actions/routes: {unused_topic_keys}")

    print("[menu-contract] check")
    print(f"- menu entries: {len(all_entries)}")
    print(f"- setting toggles exposed in menu: {len(menu_setting_toggles)}")
    print(f"- warnings: {len(warnings)}")
    print(f"- issues: {len(issues)}")

    if warnings:
        print("\n[warnings]")
        for warning in warnings:
            print(f"- {warning}")

    if issues:
        print("\n[issues]")
        for issue in issues:
            print(f"- {issue}")
        print("\n[hint] fix manually or rerun after aligning menu_registry/action_registry/menu_state_resolver/settings files.")
        return 1

    print("[menu-contract] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
