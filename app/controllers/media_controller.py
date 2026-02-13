from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class MediaController:
    """Coordinates media control actions and UI feedback labels."""

    def __init__(self, main_app):
        self.main_app = main_app

    def show_music_overlays(self):
        self.main_app.display_controller.show_music_overlays()

    def media_play_pause(self):
        self.main_app.mqtt_controller.publish_action("media-play-pause")
        if self.main_app.music_object and self.main_app.music_object.state == "playing":
            self.main_app.display_controller.place_action_label(image="pause-white.png")
        else:
            self.main_app.display_controller.place_action_label(image="play-white.png")

    def media_skip_song(self, next_previous):
        if self.main_app.music_object and self.main_app.music_object.channel is None:
            if next_previous == "next":
                self.main_app.mqtt_controller.publish_action("media-next")
                self.main_app.display_controller.place_action_label(image="forward-white.png")
            else:
                self.main_app.mqtt_controller.publish_action("media-previous")
                self.main_app.display_controller.place_action_label(image="backward-white.png")
        else:
            logger.info("Can't skip song; radio is playing.")

    def media_volume(self, up_down):
        if up_down == "up":
            self.main_app.mqtt_controller.publish_action("media-volume-up")
            self.main_app.display_controller.place_action_label(image="volume-up-white.png")
        else:
            self.main_app.mqtt_controller.publish_action("media-volume-down")
            self.main_app.display_controller.place_action_label(image="volume-down-white.png")
