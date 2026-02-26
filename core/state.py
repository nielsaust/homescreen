from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class AppState:
    """Immutable app state snapshot for reducer-driven updates."""

    screen_state: str = "off"
    is_display_on: bool = False
    is_desktop: bool = True
    system_platform: str = "unknown"

    last_interaction_type: str | None = None
    last_mqtt_topic: str | None = None
    last_action: str | None = None

    music_state: str | None = None
    music_title: str | None = None
    music_artist: str | None = None
    music_channel: str | None = None
    music_album: str | None = None
    music_album_art_api_url: str | None = None
    music_album_art_music_assistant_url: str | None = None

    sleep_mode: bool | None = None
    printer_progress: float | int | None = None
    network_online: bool | None = None
    weather_source: str | None = None
    weather_cached_at_text: str | None = None

    startup_queue_size: int = 0
    data: dict[str, Any] = field(default_factory=dict)
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
