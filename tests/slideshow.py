import os
import pathlib
import random
import tkinter as tk
from PIL import Image, ImageTk
from time import sleep

class SlideShow():
    def __init__(self, root):
        self.root = root
        self.image_folder = pathlib.Path(__file__).parent / f'photos'
        self.display_time = 1  # The time in seconds to display each image
        self.image_files = None
        self.root_width = 720  # Width of the root window
        self.root_height = 720  # Width of the root window

        self.root.geometry(f"{self.root_width}x{self.root_height}")  # Set the root window size

        self.label = tk.Label(root)
        self.label.pack(fill=tk.BOTH, expand=True)
        
        self.show_images_in_random_order(self.image_folder)
        
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
            image.thumbnail((self.root_width, self.root_height))
            photo = ImageTk.PhotoImage(image)
            
            self.label.config(image=photo)
            self.label.image = photo
            
            self.root.after(self.display_time * 1000, self.show_image)  # Schedule the next image
        else:
            self.show_images_in_random_order(self.image_folder)
        
    
if __name__ == "__main__":
    root = tk.Tk()
    app = SlideShow(root)

    root.mainloop()









