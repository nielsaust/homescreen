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
from app.observability.domain_logger import log_event

logger = logging.getLogger(__name__)
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
IMAGES_DIR = PROJECT_ROOT / "images"


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
        log_event(logger, logging.INFO, "music", "screen.show")
        self.clear_current()

        if self.main_app.music_object is None:
            log_event(logger, logging.ERROR, "music", "screen.show_blocked", reason="missing_music_object")
            return False

        obj = self.main_app.music_object
        state = getattr(obj, "state", None)
        title = getattr(obj, "title", None)
        artist = getattr(obj, "artist", None)
        channel = getattr(obj, "channel", None)
        album = getattr(obj, "album", None)
        album_art_api_url = getattr(obj, "album_art_api_url", None)

        if artist is None:
            log_event(logger, logging.WARNING, "music", "screen.show_blocked", reason="missing_artist", state=state)
            if getattr(self.main_app, "music_debug_logging", False):
                log_event(
                    logger,
                    logging.INFO,
                    "music",
                    "screen.render_blocked_details",
                    state=state,
                    title=title,
                    channel=channel,
                    album_art=album_art_api_url,
                )
            return False

        self._maybe_load_album_art(album_art_api_url)

        if self.main_app.settings.media_show_titles:
            self.show_overlays(artist, title, album, channel)

        return True

    def apply_state_update(self, state, title, artist, channel, album, album_art_api_url):
        if state != "playing":
            self.remove_overlays()
            return

        if artist is None and channel is None and title is None:
            return

        self._maybe_load_album_art(album_art_api_url)
        if self.main_app.settings.media_show_titles:
            self.show_overlays(artist, title, album, channel)

    def _maybe_load_album_art(self, album_art_api_url):
        log_event(
            logger,
            logging.DEBUG,
            "music",
            "art.check",
            requested=album_art_api_url,
            current=self.current_album_art_url,
        )
        if album_art_api_url is None:
            log_event(logger, logging.DEBUG, "music", "art.skipped", reason="missing_url")
            return

        image_url = self.main_app.settings.home_assistant_api_base_url + album_art_api_url
        track_signature = self.main_app.music_service.art_signature(self.main_app.music_object)
        if getattr(self.main_app, "music_debug_logging", False):
            log_event(logger, logging.INFO, "music", "art.request_computed", image_url=image_url, signature=track_signature)

        if image_url == self.current_album_art_url:
            log_event(logger, logging.DEBUG, "music", "art.skipped", reason="already_loaded")
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
            log_event(logger, logging.DEBUG, "music", "art.clear_before_load")
            self.album_art_image = None
            self.album_art_label.configure(image=None)

    def load_image(self, image_url, num_of_tries=3, track_signature=None):
        if getattr(self.main_app, "music_debug_logging", False):
            log_event(logger, logging.INFO, "music", "art.load_start", image_url=image_url, retries=num_of_tries)
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
                log_event(
                    logger,
                    logging.INFO,
                    "music",
                    "art.stale_dropped",
                    requested_signature=requested_signature,
                    current_signature=current_signature,
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
                log_event(logger, logging.INFO, "music", "art.load_success", url=url)
        except Exception as e:
            log_event(logger, logging.ERROR, "music", "art.apply_failed", error=e)
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
            log_event(logger, logging.INFO, "music", "art.placeholder_used")
        self.load_local_image(IMAGES_DIR / "no_album_art.jpeg")
        self.main_app.root.update_idletasks()

    def load_local_image(self, image_path):
        try:
            image = Image.open(image_path)
            image = image.resize((self.main_app.settings.screen_width, self.main_app.settings.screen_height), Image.LANCZOS)

            self.album_art_image = ImageTk.PhotoImage(image)
            self.album_art_label.configure(image=self.album_art_image)
            return None
        except Exception as e:
            log_event(logger, logging.ERROR, "music", "art.placeholder_load_failed", error=e)
            return None

    def preparing_loading_gif(self):
        gif_path = IMAGES_DIR / "loading.gif"
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
        log_event(logger, logging.DEBUG, "music", "art.loading_animation_start")
        self.stop_loading_animation()
        self.animation_running = True
        self.animate_loading()

    def animate_loading(self):
        if self.animation_running:
            frame = next(self.loading_animation_frames_cycle)
            self.album_art_label.config(image=frame)
            self.animation_id = self.frame.after(100, self.animate_loading)

    def stop_loading_animation(self):
        log_event(logger, logging.DEBUG, "music", "art.loading_animation_stop")
        self.animation_running = False
        if self.animation_id is not None:
            self.frame.after_cancel(self.animation_id)
            self.animation_id = None
