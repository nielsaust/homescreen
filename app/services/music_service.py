from __future__ import annotations

from typing import Any


class MusicService:
    """Normalizes and coalesces incoming music payloads."""

    def __init__(self):
        self._last_signature: tuple[Any, ...] | None = None

    def normalize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        state = payload.get("state")
        title = payload.get("title")
        artist = payload.get("artist")
        channel = payload.get("channel")
        album = payload.get("album")
        album_art_api_url = payload.get("album_art_api_url")

        if not artist and channel:
            artist = channel

        return {
            "state": state,
            "title": title,
            "artist": artist,
            "channel": channel,
            "album": album,
            "album_art_api_url": album_art_api_url,
        }

    def signature(self, payload: dict[str, Any]) -> tuple[Any, ...]:
        return (
            payload.get("state"),
            payload.get("title"),
            payload.get("artist"),
            payload.get("channel"),
            payload.get("album"),
            payload.get("album_art_api_url"),
        )

    def should_process(self, payload: dict[str, Any], drop_duplicates: bool = True) -> bool:
        if not drop_duplicates:
            return True
        signature = self.signature(payload)
        if signature == self._last_signature:
            return False
        self._last_signature = signature
        return True
