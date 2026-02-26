from __future__ import annotations

import logging

from app.observability.domain_logger import log_event

logger = logging.getLogger(__name__)


class MusicStateService:
    """Owns mutation/publication flow for the current music object."""

    def __init__(self, main_app):
        self.main_app = main_app

    def update_music_object(self, data):
        state = data.get("state")
        title = data.get("title")
        artist = data.get("artist")
        channel = data.get("channel")
        album = data.get("album")
        album_art_api_url = data.get("album_art_api_url")
        album_art_music_assistant_url = data.get("album_art_music_assistant_url")

        if self.main_app.music_object is None:
            from app.models.music_object import MusicObject

            self.main_app.music_object = MusicObject(
                state,
                title,
                artist,
                channel,
                album,
                album_art_api_url,
                album_art_music_assistant_url,
            )
        else:
            self.main_app.music_object.state = state
            self.main_app.music_object.title = title
            self.main_app.music_object.artist = artist
            self.main_app.music_object.channel = channel
            self.main_app.music_object.album = album
            self.main_app.music_object.album_art_api_url = album_art_api_url
            self.main_app.music_object.album_art_music_assistant_url = album_art_music_assistant_url

        self.main_app.log_music_debug(
            "[music] object after update",
            {
                "state": self.main_app.music_object.state,
                "title": self.main_app.music_object.title,
                "artist": self.main_app.music_object.artist,
                "channel": self.main_app.music_object.channel,
                "album": self.main_app.music_object.album,
                "album_art_api_url": self.main_app.music_object.album_art_api_url,
                "album_art_music_assistant_url": self.main_app.music_object.album_art_music_assistant_url,
            },
        )
        logger.debug("========= Music object updated =========")
        obj = self.main_app.music_object
        if self.main_app.music_debug_logging:
            for key, value in vars(obj).items():
                logger.debug("music_object.%s = %r", key, value)

        log_event(logger, logging.DEBUG, "music", "state.updated", state=state, title=title)
        self.main_app.publish_event(
            "music.updated",
            {
                "state": state,
                "title": title,
                "artist": artist,
                "channel": channel,
                "album": album,
                "album_art_api_url": album_art_api_url,
                "album_art_music_assistant_url": album_art_music_assistant_url,
            },
        )

        self.main_app.print_memory_usage()
