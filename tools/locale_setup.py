#!/usr/bin/env python3
"""Interactive helper to configure OS locales for date/time formatting."""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess


def _prompt(text: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{text}{suffix}: ").strip()
    return value if value else default


def _prompt_bool(text: str, default: bool) -> bool:
    default_text = "y" if default else "n"
    while True:
        raw = _prompt(f"{text} (y/n)", default_text).lower()
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("Please answer y or n.")


def _run(cmd: list[str]) -> int:
    print(f"[locale-setup] running: {' '.join(cmd)}")
    return subprocess.run(cmd, check=False).returncode


def wizard() -> int:
    if platform.system().lower() != "linux":
        print("[locale-setup] Locale generation helper is Linux-only.")
        print("[locale-setup] On macOS/Windows, install locales via OS settings/package manager.")
        return 0
    if shutil.which("locale-gen") is None:
        print("[locale-setup] locale-gen not found. Install locales package first (e.g. locales).")
        return 1

    locale_name = _prompt("Locale to enable", "nl_NL.UTF-8")
    print("\n[locale-setup] summary")
    print(f"- locale: {locale_name}")
    print("- this updates /etc/locale.gen and runs locale-gen")
    if not _prompt_bool("Apply now?", False):
        print("[locale-setup] canceled.")
        return 0

    escaped = locale_name.replace("/", r"\/")
    _run(["sudo", "sed", "-i", f"s/^# *{escaped}/{escaped}/", "/etc/locale.gen"])
    rc = _run(["sudo", "locale-gen"])
    if rc != 0:
        return rc

    print("[locale-setup] done")
    print(f"[locale-setup] You can now set time_locale to '{locale_name}' in local_config/settings.json")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Locale setup helper")
    sub = parser.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("wizard", help="Interactive setup")
    w.set_defaults(func=lambda _: wizard())
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

