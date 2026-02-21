#!/usr/bin/env python3
"""Interactive navigator for Make targets."""

from __future__ import annotations

import subprocess
import sys


MENU: list[dict] = [
    {
        "title": "Onboarding & Setup",
        "items": [
            ("install", "Bootstrap venv/dependencies and local defaults."),
            ("configuration", "Interactive feature configuration wizard."),
            ("mqtt-topics", "Configure MQTT topic keys and values."),
            ("locale-setup", "Configure locale support for date/time rendering."),
            ("service-setup", "Configure systemd service and deploy polling."),
            ("migrate-local-config", "Migrate older local config formats."),
        ],
    },
    {
        "title": "Run & Network",
        "items": [
            ("run", "Start the app locally."),
            ("net-status", "Show network simulation status."),
            ("net-down", "Simulate network outage."),
            ("net-up", "End simulated network outage."),
            ("net-recover", "Try local network recovery script."),
            ("test-device", "Run device-oriented smoke checks."),
        ],
    },
    {
        "title": "Menu & Content",
        "items": [
            ("menu-item-scaffold", "Create/edit/remove/verify menu items."),
            ("menu-item-verify-toggle", "Quick verify one menu item wiring."),
            ("menu-contract-check", "Validate menu contracts and references."),
            ("menu-migrate-actions", "Migrate menu action metadata format."),
        ],
    },
    {
        "title": "Validation & Tests",
        "items": [
            ("doctor", "Check runtime prerequisites."),
            ("baseline", "Compile/import baseline checks."),
            ("smoke", "Runtime smoke tests."),
            ("test-unit", "Run unit tests."),
            ("check-local", "Run local config/contract/guard checks."),
            ("test-local", "Run full local validation suite."),
            ("localization-check", "Check translation consistency/unused keys."),
            ("py39-guard", "Guard against Python 3.9-incompatible syntax."),
            ("perf-check", "Run lightweight performance checks."),
        ],
    },
    {
        "title": "Settings Maintenance",
        "items": [
            ("settings-check", "Compare local settings to example."),
            ("settings-update-example", "Add missing keys into settings example."),
            ("settings-update-local", "Add missing example keys into local settings."),
            ("settings-prune-local-preview", "Preview removable local-only keys."),
            ("settings-prune-local", "Remove removable local-only keys."),
        ],
    },
    {
        "title": "Security & Hygiene",
        "items": [
            ("precommit-install", "Install pre-commit hooks."),
            ("precommit-run", "Run all pre-commit hooks."),
            ("security-scan", "Run gitleaks scan and write JSON report."),
        ],
    },
    {
        "title": "Deploy Helpers",
        "items": [
            ("deploy-dry-run", "Preview deploy script invocation."),
        ],
    },
]


def _prompt(text: str) -> str:
    try:
        return input(text).strip()
    except (KeyboardInterrupt, EOFError):
        print("\n[wizard] canceled.")
        raise SystemExit(0)


def _pick_index(max_value: int, allow_back: bool = True) -> int | None:
    while True:
        raw = _prompt("Choose number: ")
        if raw.lower() in {"q", "quit", "x", "exit"}:
            raise SystemExit(0)
        if allow_back and raw in {"0", "b", "back"}:
            return None
        if raw.isdigit():
            idx = int(raw)
            if 1 <= idx <= max_value:
                return idx - 1
        print("Invalid choice. Use listed number, 0 for back, q to quit.")


def _run_make(target: str) -> int:
    print(f"\n[wizard] running: make {target}\n")
    return subprocess.call(["make", target])


def _show_categories() -> int | None:
    print("\nMake Wizard")
    print("Select a category (q to quit):")
    for idx, category in enumerate(MENU, start=1):
        print(f"{idx:2d}) {category['title']}")
    print(" 0) Quit")
    picked = _pick_index(len(MENU), allow_back=True)
    if picked is None:
        return None
    return picked


def _show_targets(category: dict) -> str | None:
    items = category["items"]
    print(f"\n{category['title']}")
    print("Select a target (0 = back, q = quit):")
    for idx, (target, desc) in enumerate(items, start=1):
        print(f"{idx:2d}) {target:26} - {desc}")
    picked = _pick_index(len(items), allow_back=True)
    if picked is None:
        return None
    target, _ = items[picked]
    return target


def main() -> int:
    while True:
        category_idx = _show_categories()
        if category_idx is None:
            print("[wizard] bye.")
            return 0
        category = MENU[category_idx]
        target = _show_targets(category)
        if target is None:
            continue
        code = _run_make(target)
        print(f"\n[wizard] make {target} exited with code {code}")
        _prompt("Press Enter to continue...")


if __name__ == "__main__":
    raise SystemExit(main())
