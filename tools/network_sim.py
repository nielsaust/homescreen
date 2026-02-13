#!/usr/bin/env python3
"""Toggle network outage simulation by creating/removing a flag file."""

from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FLAG = ROOT / ".sim" / "network_down.flag"


def set_down() -> None:
    FLAG.parent.mkdir(parents=True, exist_ok=True)
    FLAG.write_text("down\n")
    print(f"[network-sim] DOWN enabled ({FLAG})")


def set_up() -> None:
    if FLAG.exists():
        FLAG.unlink()
    print(f"[network-sim] DOWN disabled ({FLAG})")


def show_status() -> None:
    if FLAG.exists():
        print("[network-sim] status=DOWN (simulated outage enabled)")
    else:
        print("[network-sim] status=UP (normal network behavior)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Network outage simulator")
    parser.add_argument("command", choices=["down", "up", "status"])
    args = parser.parse_args()

    if args.command == "down":
        set_down()
    elif args.command == "up":
        set_up()
    else:
        show_status()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
