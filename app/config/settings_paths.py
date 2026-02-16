from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCAL_CONFIG_DIR = ROOT / "local_config"
LOCAL_SETTINGS_PATH = LOCAL_CONFIG_DIR / "settings.json"
SETTINGS_EXAMPLE_PATH = ROOT / "settings.json.example"


def resolve_settings_path() -> Path:
    """Preferred order: local_config/settings.json, then settings.json.example."""
    if LOCAL_SETTINGS_PATH.exists():
        return LOCAL_SETTINGS_PATH
    return SETTINGS_EXAMPLE_PATH


def preferred_local_settings_path() -> Path:
    return LOCAL_SETTINGS_PATH
