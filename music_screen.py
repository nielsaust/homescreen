from __future__ import annotations
from itertools import cycle
import threading
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import MainApp

import sys
import logging

logger = logging.getLogger()

import tkinter as tk
from tkinter import font as tkFont
import os
import pathlib
import math
import re
from PIL import Image, ImageTk
from io import BytesIO
import aiohttp
import asyncio

class MusicScreen:
    def __init__(self, main_app: MainApp, frame):
        self._current_task = None

        self.main_app = main_app
        self.frame = frame

        self.top_text = None
        self.bottom_text = None
        self.album_art_image = None
        self.album_art_label = None
        self.top_overlay = None
        self.bottom_text_label = None
        self.bottom_overlay = None
        self.bottom_text_label_ = None
        self.music_info_timeout_ms = self.main_app.settings.media_titles_timeout
        self.timeout_future = None

        # album art & loading animation
        self.animation_id = None
        self.animation_running = False
        self.current_album_art_url = None
        self.loading_animation_frames = []
        self.loading_animation_frames_cycle = None  # This will be an iterator

        self.create()

    def create(self):
        self.album_art_label = tk.Label(self.frame, bg="black", padx=0, pady=0)
        self.album_art_label.configure(image=self.album_art_image)
        self.album_art_label.pack(fill=tk.BOTH, expand=True)

        self.top_overlay = tk.Frame(self.frame, bg="black")
        self.top_overlay.place(relx=0, rely=0, relwidth=1, relheight=self.main_app.settings.media_titles_relative_height)

        self.top_text_label = tk.Label(self.top_overlay, bg="black", fg="white",
                                        font=tkFont.Font(family="Helvetica", size=self.main_app.settings.media_titles_font_size, weight="bold"), wraplength=600)
        self.top_text_label.pack(fill=tk.BOTH, expand=True)

        self.bottom_overlay = tk.Frame(self.frame, bg="black")
        self.bottom_overlay.place(relx=0, rely=(1-self.main_app.settings.media_titles_relative_height), relwidth=1, relheight=self.main_app.settings.media_titles_relative_height)

        self.bottom_text_label = tk.Label(self.bottom_overlay, bg="black", fg="white",
                                            font=tkFont.Font(family="Helvetica", size=self.main_app.settings.media_titles_font_size, weight="bold"), wraplength=600)
        self.bottom_text_label.pack(fill=tk.BOTH, expand=True)

        self.top_overlay.place_forget()
        self.bottom_overlay.place_forget()

        self.remove_overlays_timeout()
        self.preparing_loading_gif()

    def show(self):
        logging.info("========= Music screen show =========")
        
        # overlays
        self.clear_current()

        if self.main_app.music_object is None:
            logger.error(f"No music object present in Main")
            return False
        
        obj = self.main_app.music_object
        state = getattr(obj, "state", None)
        title = getattr(obj, "title", None)
        artist = getattr(obj, "artist", None)
        channel = getattr(obj, "channel", None)
        album = getattr(obj,"album", None)
        album_art_api_url = getattr(obj, "album_art_api_url", None)
        
        if self.main_app.music_object.artist is None:
            logger.warning(f"No artist = no music")
            if getattr(self.main_app, "music_debug_logging", False):
                logger.info(
                    "[music-screen] blocked render (artist missing) state=%s title=%s channel=%s album_art=%s",
                    state,
                    title,
                    channel,
                    album_art_api_url,
                )
            return False

        logger.debug(f"album url = {album_art_api_url}, current url = {self.current_album_art_url}")
        if album_art_api_url is not None:
            image_url = self.main_app.settings.home_assistant_api_base_url + album_art_api_url
            if getattr(self.main_app, "music_debug_logging", False):
                logger.info("[music-screen] computed image_url=%s", image_url)
            if image_url != self.current_album_art_url:
                self.clear_album_art()
                self.load_image(image_url,self.main_app.settings.media_get_remote_image_retry_amount)  # Use asyncio.run to create an event loop
            else:
                logger.debug(f"Album art already loaded: {self.main_app.music_object.album_art_api_url}")
        else:
            logger.debug(f"Album art not available")

        if(self.main_app.settings.media_show_titles):
            self.show_overlays()

        return True

    def clear_current(self):
        self.top_text_label.configure(text="")
        self.bottom_text_label.configure(text="")

    def show_overlays(self):
        artist = self.main_app.music_object.artist
        title = self.main_app.music_object.title
        album = self.main_app.music_object.album
        channel = self.main_app.music_object.channel
        
        if self.main_app.settings.media_sanitize_titles:
            if title:
                title = self.clean_title(title)
            if album:
                album = self.clean_title(album)

        self.top_text = None
        if artist:
            self.top_text = artist
        elif channel:
            self.top_text = channel

        self.bottom_text = None
        if not channel and (title and album) and (title != album):
            self.bottom_text = f"{title} - {album}"
        elif title!=channel:
            self.bottom_text = title
        
        text = self.top_text if self.top_text else ""
        self.top_text_label.configure(text=text)

        text = self.bottom_text if self.bottom_text else ""
        self.bottom_text_label.configure(text=text)

        self.top_text_label.pack(fill=tk.BOTH, expand=True)
        self.bottom_text_label.pack(fill=tk.BOTH, expand=True)

        if(self.top_text):
            self.top_overlay.place(relx=0, rely=0, relwidth=1, relheight=self.main_app.settings.media_titles_relative_height)
        else:
            self.top_overlay.place_forget()
        
        if(self.bottom_text):
            self.bottom_overlay.place(relx=0, rely=(1-self.main_app.settings.media_titles_relative_height), relwidth=1, relheight=self.main_app.settings.media_titles_relative_height)
        else:
            self.top_overlay.place_forget()

        self.remove_overlays_timeout()

    def remove_overlays_timeout(self):
        # Cancel the previously scheduled job, if any
        if self.timeout_future:
            self.frame.after_cancel(self.timeout_future)

        # Schedule the new job
        self.timeout_future = self.frame.after(self.music_info_timeout_ms, self.remove_overlays)
    
    def remove_overlays(self):
        # Remove the black overlays
        self.top_overlay.place_forget()
        self.bottom_overlay.place_forget()
    
    def clear_album_art(self):
        # set image to none to make sure it doesn't display old data
        if self.main_app.settings.media_clear_image_before_getting_new:
            logger.debug("Clearing album art")
            self.album_art_image = None
            self.album_art_label.configure(image=None)


    async def run_image_task(self, image_url, num_of_tries):
        # Cancel any running task if it's still active
        if self._current_task is not None and not self._current_task.done():
            logger.debug("Cancelling previous image loading task")
            self._current_task.cancel()
            try:
                await self._current_task
            except asyncio.CancelledError:
                logger.debug("Previous task was successfully cancelled")

        # Start a new task
        logger.debug("Starting new image loading task")
        self._current_task = asyncio.create_task(self.load_and_display_remote_image(image_url, num_of_tries))
        await self._current_task

    def load_image(self, image_url, num_of_tries=3):
        # Run the async task within an asyncio loop
        if getattr(self.main_app, "music_debug_logging", False):
            logger.info("[music-screen] load_image start url=%s tries=%s", image_url, num_of_tries)
        asyncio.run(self.run_image_task(image_url, num_of_tries))

    # Add this method to load and display a remote image
    async def load_and_display_remote_image(self, url, max_retries=3):
        # Start the loading animation
        self.start_loading_animation()
        
        for retry in range(max_retries):
            logger.debug(f"getting url: {url}")
            response = None
            try:
                async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=self.main_app.settings.verify_ssl_on_trusted_sources)) as session:
                    async with session.get(url) as response:
                        try:
                            logger.debug(f"image loader got response status code: {response.status}")
                            response.raise_for_status()  # This raises an exception if the response status code is not in the 200 range
                            self.stop_loading_animation()

                            image_bytes = await response.read()

                            image = Image.open(BytesIO(image_bytes))
                            img_org_width, img_org_height = image.size
                            aspect_ratio = img_org_width/img_org_height
                            target_size = (self.main_app.settings.screen_width,math.floor(self.main_app.settings.screen_width/aspect_ratio))
                            
                            new_image = image.resize(target_size, Image.LANCZOS)                
                            new_size = (self.main_app.settings.screen_width, self.main_app.settings.screen_height)
                            if aspect_ratio != 1.0:
                                new_image.thumbnail(new_size, Image.LANCZOS)
                            
                            logger.debug(f"loaded remote image: {url}")
                            if getattr(self.main_app, "music_debug_logging", False):
                                logger.info("[music-screen] loaded remote image successfully url=%s", url)
                            self.album_art_image = ImageTk.PhotoImage(new_image)
                            self.album_art_label.configure(image=self.album_art_image)
                            self.current_album_art_url = url
                            
                            return None
                        except aiohttp.ClientError as e:
                            logger.error(f"Error applying album art to image: {e}")
                            continue

            except aiohttp.ClientError as e:
                # Handle aiohttp-specific exceptions (e.g., network errors)
                logger.error(f"Error retrieving album art from Home Assistant API (Attempt {retry + 1}/{max_retries}): {e}")
            except Exception as e:
                # Handle other exceptions (e.g., non-aiohttp exceptions)
                logger.error(f"Unexpected error retrieving album art from Home Assistant API (Attempt {retry + 1}/{max_retries}): {e}")

        # Load a local image using PIL
        self.stop_loading_animation()
        if getattr(self.main_app, "music_debug_logging", False):
            logger.info("[music-screen] using local placeholder image")
        self.load_local_image(pathlib.Path(__file__).parent / 'images/no_album_art.jpeg')
        
    def load_local_image(self, image_path):
        try:
            # Load a local image using PIL
            image = Image.open(image_path) 
            image = image.resize((self.main_app.settings.screen_width, self.main_app.settings.screen_height), Image.LANCZOS)
            
            self.album_art_image = ImageTk.PhotoImage(image)
            self.album_art_label.configure(image=self.album_art_image)

            return None
        except Exception as e:
            # Handle the exception gracefully
            logger.error(f"Error retrieving local album art placeholder: {e}")
            return None
        
    def clean_title(self, title):
        # Define a regular expression pattern to match common unwanted text
        
        pattern_remaster = r'\s*[-(].*?(\bremaster(ed)?\b|\bbonus\b|\blive\b|\bacoustic\b|\bremix\b|\b(deluxe|extended|expanded|anniversary|single)\s+(version|edition)\b|\bfeat\..*\b).*\s*((\)|\]))?'
        pattern_movie_score = r" \((Original Motion Picture Soundtrack|Soundtrack|OST|Score|Music from the Motion Picture)\)"

        # Use re.sub to replace the unwanted text with an empty string
        cleaned_title = re.sub(pattern_remaster, '', title, flags=re.IGNORECASE)
        cleaned_title = re.sub(pattern_movie_score, '', cleaned_title, flags=re.IGNORECASE)
        if title!=cleaned_title:
            logger.debug(f"=================")
            logger.debug(f"Cleaned: {title}")
            logger.debug(f"Result:  {cleaned_title}")
        else:
            logger.debug(f"Title '{title}' not altered.")

        return cleaned_title


    def preparing_loading_gif(self):
        # Load the GIF frames in advance to avoid reloading each time
        gif_path = pathlib.Path(__file__).parent / 'images/loading.gif'  # Path to your loading GIF
        gif_image = Image.open(gif_path)
        self.loading_animation_frames = []
        try:
            while True:
                self.loading_animation_frames.append(ImageTk.PhotoImage(gif_image.copy()))
                gif_image.seek(len(self.loading_animation_frames))
        except EOFError:
            pass

        # Create a cycle iterator from the loaded frames
        self.loading_animation_frames_cycle = cycle(self.loading_animation_frames)
        
    def start_loading_animation(self):
        logger.debug("Starting loading animation")
        self.stop_loading_animation()
        self.animation_running = True
        self.animate_loading()

    def animate_loading(self):
        if self.animation_running:
            # Get the next frame from the cycle iterator
            frame = next(self.loading_animation_frames_cycle)
            self.album_art_label.config(image=frame)
            # Schedule the next frame update after 100 ms
            self.animation_id = self.frame.after(100, self.animate_loading)

    def stop_loading_animation(self):
        logger.debug("Stopping loading animation")
        self.animation_running = False
        if self.animation_id is not None:
            self.frame.after_cancel(self.animation_id)  # Cancel the scheduled update
            self.animation_id = None
