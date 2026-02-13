from __future__ import annotations
from itertools import cycle
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import MainApp

import logging
import tkinter as tk
from tkinter import font as tkFont
import pathlib
import math
from PIL import Image, ImageTk
from io import BytesIO

from app.services.music_art_service import MusicArtService
from app.viewmodels.music_view_model import build_music_overlay_view_model

logger = logging.getLogger(__name__)


class MusicScreen:
    def __init__(self, main_app: MainApp, frame):
        self.main_app = main_app
        self.frame = frame

        self.album_art_image = None
        self.album_art_label = None
        self.top_overlay = None
        self.top_text_label = None
        self.bottom_overlay = None
        self.bottom_text_label = None
        self.music_info_timeout_ms = self.main_app.settings.media_titles_timeout
        self.timeout_future = None

        self.animation_id = None
        self.animation_running = False
        self.current_album_art_url = None
        self.loading_animation_frames = []
        self.loading_animation_frames_cycle = None
        self.current_album_art_request_id = 0

        self.art_service = MusicArtService(
            verify_ssl=self.main_app.settings.verify_ssl_on_trusted_sources,
        )

        self.create()

    def create(self):
        self.album_art_label = tk.Label(self.frame, bg="black", padx=0, pady=0)
        self.album_art_label.configure(image=self.album_art_image)
        self.album_art_label.pack(fill=tk.BOTH, expand=True)

        self.top_overlay = tk.Frame(self.frame, bg="black")
        self.top_overlay.place(relx=0, rely=0, relwidth=1, relheight=self.main_app.settings.media_titles_relative_height)

        self.top_text_label = tk.Label(
            self.top_overlay,
            bg="black",
            fg="white",
            font=tkFont.Font(
                family="Helvetica",
                size=self.main_app.settings.media_titles_font_size,
                weight="bold",
            ),
            wraplength=600,
        )
        self.top_text_label.pack(fill=tk.BOTH, expand=True)

        self.bottom_overlay = tk.Frame(self.frame, bg="black")
        self.bottom_overlay.place(
            relx=0,
            rely=(1 - self.main_app.settings.media_titles_relative_height),
            relwidth=1,
            relheight=self.main_app.settings.media_titles_relative_height,
        )

        self.bottom_text_label = tk.Label(
            self.bottom_overlay,
            bg="black",
            fg="white",
            font=tkFont.Font(
                family="Helvetica",
                size=self.main_app.settings.media_titles_font_size,
                weight="bold",
            ),
            wraplength=600,
        )
        self.bottom_text_label.pack(fill=tk.BOTH, expand=True)

        self.top_overlay.place_forget()
        self.bottom_overlay.place_forget()

        self.remove_overlays_timeout()
        self.preparing_loading_gif()

    def show(self):
        logger.info("========= Music screen show =========")
        self.clear_current()

        if self.main_app.music_object is None:
            logger.error("No music object present in Main")
            return False

        obj = self.main_app.music_object
        state = getattr(obj, "state", None)
        title = getattr(obj, "title", None)
        artist = getattr(obj, "artist", None)
        channel = getattr(obj, "channel", None)
        album = getattr(obj, "album", None)
        album_art_api_url = getattr(obj, "album_art_api_url", None)

        if artist is None:
            logger.warning("No artist = no music")
            if getattr(self.main_app, "music_debug_logging", False):
                logger.info(
                    "[music-screen] blocked render (artist missing) state=%s title=%s channel=%s album_art=%s",
                    state,
                    title,
                    channel,
                    album_art_api_url,
                )
            return False

        self._maybe_load_album_art(album_art_api_url)

        if self.main_app.settings.media_show_titles:
            self.show_overlays(artist, title, album, channel)

        return True

    def _maybe_load_album_art(self, album_art_api_url):
        logger.debug("album url = %s, current url = %s", album_art_api_url, self.current_album_art_url)
        if album_art_api_url is None:
            logger.debug("Album art not available")
            return

        image_url = self.main_app.settings.home_assistant_api_base_url + album_art_api_url
        track_signature = self.main_app.music_service.art_signature(self.main_app.music_object)
        if getattr(self.main_app, "music_debug_logging", False):
            logger.info("[music-screen] computed image_url=%s signature=%s", image_url, track_signature)

        if image_url == self.current_album_art_url:
            logger.debug("Album art already loaded: %s", album_art_api_url)
            return

        self.clear_album_art()
        self.load_image(
            image_url,
            self.main_app.settings.media_get_remote_image_retry_amount,
            track_signature=track_signature,
        )

    def clear_current(self):
        self.top_text_label.configure(text="")
        self.bottom_text_label.configure(text="")

    def show_overlays(self, artist, title, album, channel):
        vm = build_music_overlay_view_model(
            artist=artist,
            title=title,
            album=album,
            channel=channel,
            sanitize=self.main_app.settings.media_sanitize_titles,
        )

        self.top_text_label.configure(text=vm.top_text)
        self.bottom_text_label.configure(text=vm.bottom_text)

        self.top_text_label.pack(fill=tk.BOTH, expand=True)
        self.bottom_text_label.pack(fill=tk.BOTH, expand=True)

        if vm.show_top:
            self.top_overlay.place(relx=0, rely=0, relwidth=1, relheight=self.main_app.settings.media_titles_relative_height)
        else:
            self.top_overlay.place_forget()

        if vm.show_bottom:
            self.bottom_overlay.place(
                relx=0,
                rely=(1 - self.main_app.settings.media_titles_relative_height),
                relwidth=1,
                relheight=self.main_app.settings.media_titles_relative_height,
            )
        else:
            self.bottom_overlay.place_forget()

        self.frame.update_idletasks()
        self.remove_overlays_timeout()

    def remove_overlays_timeout(self):
        if self.timeout_future:
            self.frame.after_cancel(self.timeout_future)
        self.timeout_future = self.frame.after(self.music_info_timeout_ms, self.remove_overlays)

    def remove_overlays(self):
        self.top_overlay.place_forget()
        self.bottom_overlay.place_forget()

    def clear_album_art(self):
        if self.main_app.settings.media_clear_image_before_getting_new:
            logger.debug("Clearing album art")
            self.album_art_image = None
            self.album_art_label.configure(image=None)

    def load_image(self, image_url, num_of_tries=3, track_signature=None):
        if getattr(self.main_app, "music_debug_logging", False):
            logger.info("[music-screen] load_image start url=%s tries=%s", image_url, num_of_tries)
        self.current_album_art_request_id += 1
        request_id = self.current_album_art_request_id
        self.main_app.record_music_metric("art_requests")
        self.start_loading_animation()

        thread = threading.Thread(
            target=self._load_image_background,
            args=(image_url, num_of_tries, request_id, track_signature),
            daemon=True,
        )
        thread.start()

    def _load_image_background(self, url, max_retries, request_id, track_signature):
        image_bytes = self.art_service.fetch_album_art_bytes(url, max_retries=max_retries)

        if image_bytes is None:
            self.main_app.record_music_metric("art_errors")
            self.frame.after(0, lambda rid=request_id: self._apply_placeholder_if_current(rid))
            return

        self.frame.after(
            0,
            lambda data=image_bytes, image_url=url, rid=request_id, sig=track_signature: self._apply_remote_image_if_current(
                data, image_url, rid, sig
            ),
        )

    def _apply_remote_image_if_current(self, image_bytes, url, request_id, requested_signature):
        if request_id != self.current_album_art_request_id:
            return
        current_signature = self.main_app.music_service.art_signature(self.main_app.music_object)
        if requested_signature is not None and current_signature != requested_signature:
            self.main_app.record_music_metric("art_stale_dropped")
            if getattr(self.main_app, "music_debug_logging", False):
                logger.info(
                    "[music-screen] stale art dropped requested=%s current=%s",
                    requested_signature,
                    current_signature,
                )
            self.stop_loading_animation()
            return
        try:
            image = Image.open(BytesIO(image_bytes))
            img_org_width, img_org_height = image.size
            aspect_ratio = img_org_width / img_org_height
            target_size = (self.main_app.settings.screen_width, math.floor(self.main_app.settings.screen_width / aspect_ratio))

            new_image = image.resize(target_size, Image.LANCZOS)
            new_size = (self.main_app.settings.screen_width, self.main_app.settings.screen_height)
            if aspect_ratio != 1.0:
                new_image.thumbnail(new_size, Image.LANCZOS)

            self.album_art_image = ImageTk.PhotoImage(new_image)
            self.album_art_label.configure(image=self.album_art_image)
            self.current_album_art_url = url
            self.main_app.record_music_metric("art_success")
            if getattr(self.main_app, "music_debug_logging", False):
                logger.info("[music-screen] loaded remote image successfully url=%s", url)
        except Exception as e:
            logger.error("Error applying album art image: %s", e)
            self.main_app.record_music_metric("art_errors")
            self._apply_placeholder_if_current(request_id)
            return
        finally:
            self.stop_loading_animation()
            self.main_app.root.update_idletasks()

    def _apply_placeholder_if_current(self, request_id):
        if request_id != self.current_album_art_request_id:
            return
        self.stop_loading_animation()
        self.main_app.record_music_metric("art_placeholder")
        if getattr(self.main_app, "music_debug_logging", False):
            logger.info("[music-screen] using local placeholder image")
        self.load_local_image(pathlib.Path(__file__).parent / "images/no_album_art.jpeg")
        self.main_app.root.update_idletasks()

    def load_local_image(self, image_path):
        try:
            image = Image.open(image_path)
            image = image.resize((self.main_app.settings.screen_width, self.main_app.settings.screen_height), Image.LANCZOS)

            self.album_art_image = ImageTk.PhotoImage(image)
            self.album_art_label.configure(image=self.album_art_image)
            return None
        except Exception as e:
            logger.error("Error retrieving local album art placeholder: %s", e)
            return None

    def preparing_loading_gif(self):
        gif_path = pathlib.Path(__file__).parent / "images/loading.gif"
        gif_image = Image.open(gif_path)
        self.loading_animation_frames = []
        try:
            while True:
                self.loading_animation_frames.append(ImageTk.PhotoImage(gif_image.copy()))
                gif_image.seek(len(self.loading_animation_frames))
        except EOFError:
            pass

        self.loading_animation_frames_cycle = cycle(self.loading_animation_frames)

    def start_loading_animation(self):
        logger.debug("Starting loading animation")
        self.stop_loading_animation()
        self.animation_running = True
        self.animate_loading()

    def animate_loading(self):
        if self.animation_running:
            frame = next(self.loading_animation_frames_cycle)
            self.album_art_label.config(image=frame)
            self.animation_id = self.frame.after(100, self.animate_loading)

    def stop_loading_animation(self):
        logger.debug("Stopping loading animation")
        self.animation_running = False
        if self.animation_id is not None:
            self.frame.after_cancel(self.animation_id)
            self.animation_id = None
