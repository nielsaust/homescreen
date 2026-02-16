#!/usr/bin/env python3
"""Interactive helper to configure Linux/systemd auto-start and deploy timer."""

from __future__ import annotations

import argparse
import getpass
import platform
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SYSTEMD_DIR = ROOT / "deploy" / "systemd"


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
    print(f"[service-setup] running: {' '.join(cmd)}")
    return subprocess.run(cmd, check=False).returncode


def wizard() -> int:
    if platform.system().lower() != "linux":
        print("[service-setup] Linux/systemd only. Current platform is not supported.")
        return 0
    if shutil.which("systemctl") is None:
        print("[service-setup] systemctl not found; skipping service setup.")
        return 0

    user = _prompt("Linux user for service", getpass.getuser())
    app_dir = _prompt("Homescreen app directory", str(ROOT))
    service_name = _prompt("Service name", "homescreen.service")
    install_now = _prompt_bool("Install/update systemd units now?", False)

    print("\n[service-setup] summary")
    print(f"- user: {user}")
    print(f"- app_dir: {app_dir}")
    print(f"- service: {service_name}")
    print("- deploy timer: homescreen-deploy.timer")

    if not install_now:
        print("[service-setup] Skipped installation. You can run this helper later.")
        return 0

    # Copy unit files to /etc/systemd/system and patch placeholders.
    _run(["sudo", "cp", str(SYSTEMD_DIR / "homescreen.service.example"), "/etc/systemd/system/homescreen.service"])
    _run(
        [
            "sudo",
            "cp",
            str(SYSTEMD_DIR / "homescreen-deploy.service.example"),
            "/etc/systemd/system/homescreen-deploy.service",
        ]
    )
    _run(
        [
            "sudo",
            "cp",
            str(SYSTEMD_DIR / "homescreen-deploy.timer.example"),
            "/etc/systemd/system/homescreen-deploy.timer",
        ]
    )

    # Patch service files.
    _run(["sudo", "sed", "-i", f"s|^User=.*|User={user}|", "/etc/systemd/system/homescreen.service"])
    _run(
        [
            "sudo",
            "sed",
            "-i",
            f"s|^WorkingDirectory=.*|WorkingDirectory={app_dir}|",
            "/etc/systemd/system/homescreen.service",
        ]
    )
    _run(
        [
            "sudo",
            "sed",
            "-i",
            f"s|^ExecStart=.*|ExecStart={app_dir}/.venv/bin/python {app_dir}/main.py|",
            "/etc/systemd/system/homescreen.service",
        ]
    )
    _run(
        [
            "sudo",
            "sed",
            "-i",
            f"s|^Environment=XAUTHORITY=.*|Environment=XAUTHORITY=/home/{user}/.Xauthority|",
            "/etc/systemd/system/homescreen.service",
        ]
    )

    _run(["sudo", "sed", "-i", f"s|^User=.*|User={user}|", "/etc/systemd/system/homescreen-deploy.service"])
    _run(
        [
            "sudo",
            "sed",
            "-i",
            f"s|^WorkingDirectory=.*|WorkingDirectory={app_dir}|",
            "/etc/systemd/system/homescreen-deploy.service",
        ]
    )
    _run(
        [
            "sudo",
            "sed",
            "-i",
            f"s|^ExecStart=.*|ExecStart=/usr/bin/bash {app_dir}/tools/deploy_on_pi.sh {app_dir} main {service_name}|",
            "/etc/systemd/system/homescreen-deploy.service",
        ]
    )

    _run(["sudo", "systemctl", "daemon-reload"])
    _run(["sudo", "systemctl", "enable", "--now", "homescreen.service"])

    enable_timer = _prompt_bool("Enable deploy auto-update timer?", True)
    if enable_timer:
        _run(["sudo", "systemctl", "enable", "--now", "homescreen-deploy.timer"])

    print("[service-setup] done")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Service setup helper")
    sub = parser.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("wizard", help="Interactive setup")
    w.set_defaults(func=lambda _: wizard())
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
