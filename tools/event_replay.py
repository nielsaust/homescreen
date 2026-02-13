#!/usr/bin/env python3
"""Replay JSONL events through the reducer to inspect resulting app state."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.events import AppEvent
from core.state import AppState
from core.store import AppStore


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay events to validate state transitions")
    parser.add_argument("event_file", help="Path to JSONL file with events")
    args = parser.parse_args()

    event_file = Path(args.event_file)
    if not event_file.exists():
        print(f"[event-replay][error] file not found: {event_file}")
        return 1

    store = AppStore(AppState())
    total = 0
    for line in event_file.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        event = AppEvent(
            event_type=row["event_type"],
            payload=row.get("payload", {}),
            source=row.get("source", "replay"),
        )
        store.dispatch(event)
        total += 1

    state = store.get_state()
    print(f"[event-replay] processed={total}")
    print(json.dumps(state.__dict__, default=str, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
