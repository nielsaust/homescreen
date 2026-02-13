from __future__ import annotations

from typing import Any


class MusicService:
    """Normalizes and coalesces incoming music payloads."""

    def __init__(self):
        self._last_signature: tuple[Any, ...] | None = None

    def normalize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        allowed_keys = (
            "state",
            "title",
            "artist",
            "channel",
            "album",
            "album_art_api_url",
        )
        return {key: payload.get(key) for key in allowed_keys if key in payload}

    def resolve_payload(self, current: Any, incoming_partial: dict[str, Any]) -> dict[str, Any]:
        """Build full payload by overlaying incoming partial update on current state."""
        resolved = {
            "state": getattr(current, "state", None),
            "title": getattr(current, "title", None),
            "artist": getattr(current, "artist", None),
            "channel": getattr(current, "channel", None),
            "album": getattr(current, "album", None),
            "album_art_api_url": getattr(current, "album_art_api_url", None),
        }
        resolved.update(incoming_partial)

        # Normalize common edge-cases
        if resolved.get("album_art_api_url") == "":
            resolved["album_art_api_url"] = None
        if not resolved.get("artist") and resolved.get("channel"):
            resolved["artist"] = resolved["channel"]
        return resolved

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
