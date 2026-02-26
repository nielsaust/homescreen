from __future__ import annotations

from typing import Any


class UiIntentMapperService:
    """Maps store events/state to UI intents."""

    def map_event(self, state: Any, event: Any) -> list[dict]:
        event_type = getattr(event, "event_type", None)
        payload = getattr(event, "payload", {}) or {}

        if event_type == "network.status":
            return [
                {
                    "type": "network.status",
                    "online": state.network_online,
                }
            ]

        if event_type == "weather.updated":
            return [
                {
                    "type": "weather.cache.status",
                    "source": state.weather_source,
                    "cached_at_text": state.weather_cached_at_text,
                }
            ]

        if event_type == "music.updated":
            return [
                {
                    "type": "music.render",
                    "state": state.music_state,
                    "title": state.music_title,
                    "artist": state.music_artist,
                    "channel": state.music_channel,
                    "album": state.music_album,
                    "album_art_api_url": state.music_album_art_api_url,
                    "album_art_music_assistant_url": state.music_album_art_music_assistant_url,
                },
                {
                    "type": "ui.music.playback",
                    "state": state.music_state,
                },
            ]

        if event_type == "ui.screen.changed":
            intents = [
                {
                    "type": "ui.screen.changed",
                    "screen": state.screen_state,
                    "is_display_on": state.is_display_on,
                    "force": bool(payload.get("force", False)),
                }
            ]
            if state.screen_state == "menu":
                intents.append({"type": "menu.refresh"})
            return intents

        if event_type == "menu.refresh.requested":
            return [{"type": "menu.refresh"}]

        if event_type == "menu.navigation.requested":
            return [
                {
                    "type": "menu.navigate",
                    "command": payload.get("command"),
                }
            ]

        if event_type == "ui.overlay.requested":
            return [
                {
                    "type": "ui.overlay.requested",
                    "command": payload.get("command"),
                    "data": payload.get("data"),
                    "url": payload.get("url"),
                    "username": payload.get("username"),
                    "password": payload.get("password"),
                    "progress": payload.get("progress"),
                    "reset": bool(payload.get("reset", False)),
                }
            ]

        return []
