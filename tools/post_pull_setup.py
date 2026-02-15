#!/usr/bin/env python3
"""Post-pull/project bootstrap tasks that should always be safe and idempotent."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SETTINGS = ROOT / "settings.json"
SETTINGS_EXAMPLE = ROOT / "settings.json.example"


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=4) + "\n", encoding="utf-8")


def ensure_settings_file() -> None:
    if SETTINGS.exists():
        return
    shutil.copy2(SETTINGS_EXAMPLE, SETTINGS)
    print("[setup] created settings.json from settings.json.example")


def ensure_settings_keys() -> None:
    local = _load_json(SETTINGS)
    example = _load_json(SETTINGS_EXAMPLE)
    missing = [key for key in example.keys() if key not in local]
    if not missing:
        return
    for key in missing:
        local[key] = example[key]
    _save_json(SETTINGS, local)
    print(f"[setup] added missing settings keys to settings.json: {len(missing)}")


def ensure_directories() -> None:
    for rel in ("logs", ".sim"):
        path = ROOT / rel
        path.mkdir(parents=True, exist_ok=True)
        print(f"[setup] ensured directory: {rel}")


def main() -> int:
    ensure_settings_file()
    ensure_settings_keys()
    ensure_directories()
    print("[setup] post-pull setup complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
