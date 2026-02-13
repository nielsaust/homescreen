from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class AppEvent:
    """Domain event used by the app state machine."""

    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    source: str = "app"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
