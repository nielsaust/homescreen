import pathlib
import sys
import logging
import time
logger = logging.getLogger()

from requests.auth import HTTPDigestAuth
from PIL import Image, ImageTk
from io import BytesIO
import requests
import tkinter as tk

class CamScreen:
    def __init__(self, main_app):
        self.main_app = main_app
        self.url = None
        self.username = None
        self.password = None
        self.cam_window = None
        self.is_showing = False

    def show(self, data, url, username=None, password=None):        
        active = data.get('active')
        if active is not None and active == False:
            self.destroy()
            return
        
        logger.debug(f"Show cam with data: {data} [url={url}]")
        self.url = url
        self.is_showing = True
        cam_image = self.retrieve_image(url, username, password)

        if cam_image is None:
            self.destroy()
            return

        self.cam_window = tk.Toplevel(self.main_app.root)
        if(not self.main_app.system_info["is_desktop"]):
            self.cam_window.attributes('-fullscreen', True)  # Make it fullscreen
        else:
            self.cam_window.geometry(f"{self.main_app.settings.screen_width}x{self.main_app.settings.screen_height}")

        # Create a label to display the image
        cam_window_label = tk.Label(self.cam_window, image=cam_image, bg="black")
        cam_window_label.image = cam_image
        cam_window_label.pack(fill=tk.BOTH, expand=True)

        self.main_app.print_memory_usage()

        # Schedule a function to destroy the cam
        fullscreen_cam_bind = self.cam_window.bind("<ButtonRelease-1>", self.destroy)
        self.cam_window.after(self.main_app.settings.destroy_cam_timeout, self.destroy)
    
    def destroy(self, event=None):
        if(self.is_showing):
            self.is_showing = False
            self.url = None
            self.username = None
            self.password = None

            self.main_app.display_controller.check_idle()

            if self.cam_window:
                self.cam_window.destroy()
                self.cam_window = None
            self.main_app.root.focus_set()
    
    def make_request(self, url, auth=None):
        for i in range(3):
            try:
                if(auth):
                    response = requests.get(url, auth=auth)
                else:
                    response = requests.get(url)
                return response
            except Exception as e:
                logger.error(f'Error getting the image: {e}')
                time.sleep(5)
                if i == 2:
                    raise
        return None
    
    def retrieve_image(self,url,username=None,password=None):
        if username is not None and password is not None:
            auth = HTTPDigestAuth(username,password)
            image_response = self.make_request(url,auth)
        else:
            image_response = self.make_request(url)

        if image_response is None:
            return None

        img = Image.open(BytesIO(image_response.content))        
        img = self.image_resize_to_fit(img)
        return ImageTk.PhotoImage(img)
    
    def image_resize_to_fit(self,image):
        # Get the size of the label
        label_width = self.main_app.settings.screen_width
        label_height = self.main_app.settings.screen_height

        # Resize the image while maintaining its aspect ratio
        image_width, image_height = image.size
        aspect_ratio = image_width / image_height

        if label_width / label_height > aspect_ratio:
            # The label is wider than the image, fit by height
            new_width = int(label_height * aspect_ratio)
            new_height = label_height
        else:
            # The label is taller than the image, fit by width
            new_width = label_width
            new_height = int(label_width / aspect_ratio)

        resized_image = image.resize((new_width, new_height), Image.LANCZOS)
        return resized_image
