import datetime
import pathlib
import logging
logger = logging.getLogger(__name__)

import os
import pathlib
import random
import tkinter as tk
from PIL import Image, ImageTk
from time import sleep

class SlideShow():
    def __init__(self, main_app):
        self.main_app = main_app
        self.image_folder = pathlib.Path(__file__).parent / f'images/photos/love'
        self.display_time = 5  # The time in seconds to display each image
        self.image_files = None
        self.root_width = 720  # Width of the root window
        self.root_height = 720  # Width of the root window
        self.is_showing = False

    def show(self):
        self.is_showing = True

        self.photo_frame = tk.Toplevel(self.main_app.root)
        if(not self.main_app.system_info["is_desktop"]):
            self.photo_frame.attributes('-fullscreen', True)  # Make it fullscreen
        else:
            self.photo_frame.geometry(f"{self.main_app.settings.screen_width}x{self.main_app.settings.screen_height}")

        self.photo_frame.configure(bg="#000000")
        self.label = tk.Label(self.photo_frame, bg="#000000")
        self.label.pack(fill=tk.BOTH, expand=True)
        
        self.show_images_in_random_order(self.image_folder)

        # Schedule a function to destroy the QR code overlay
        click_bind = self.photo_frame.bind("<ButtonRelease-1>", self.destroy)
        
    def show_images_in_random_order(self, image_folder):
        self.image_files = self.reorder_images(image_folder)
        self.show_image()
        
    def reorder_images(self, image_folder):
        image_files = [f for f in os.listdir(image_folder) if f.endswith(('.jpg', '.jpeg', '.png', '.gif'))]
        random.shuffle(image_files)
        return image_files
    
    def show_image(self):
        if self.image_files:
            image_file = self.image_files.pop()
            image_path = os.path.join(self.image_folder, image_file)
            
            image = Image.open(image_path)
            image.thumbnail((self.main_app.settings.screen_width, self.main_app.settings.screen_height))
            photo = ImageTk.PhotoImage(image)

            # Get the creation and modification datetime of the file
            creation_time = os.path.getctime(image_path)

            # Format the datetime as a nice, human-readable date
            creation_datetime = datetime.datetime.fromtimestamp(creation_time)
            creation_datetime = creation_datetime.strftime("%d %B %Y")

            # Print the datetime information
            logger.debug(f"Photo creation datetime: {creation_datetime}")
            
            self.label.config(image=photo)
            self.label.image = photo
            
            self.photo_frame.after(self.display_time * 1000, self.show_image)  # Schedule the next image
        else:
            self.show_images_in_random_order(self.image_folder)
 
    def destroy(self, event=None):
        if(self.is_showing):
            self.is_showing = False
            self.photo_frame.destroy()