from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import MainApp

import logging
logger = logging.getLogger(__name__)

import math
import os
import pathlib
import tkinter as tk

class SliderScreen:
    def __init__(self, main_app: MainApp, entity, title, type):
        self.main_app = main_app
        self.window = None
        self.close_timeout = None
        self.type = type

        self.data = self.main_app.device_states.data
        self.entity = entity
        self.title = title

        self.value_scale = 2.56

        self.show()
        self.main_app.check_idle_timer(False)

    def show(self):
        self.window = tk.Toplevel(self.main_app.root)
        self.close_timer()

        if(not self.main_app.system_info["is_desktop"]):
            self.window.attributes('-fullscreen', True)  # Make it fullscreen
        else:
            self.window.geometry(f"{self.main_app.settings.screen_width}x{self.main_app.settings.screen_height}")

        # Create a tkinter window
        frame = tk.Frame(self.window, bg="black")
        frame.pack(fill=tk.BOTH, expand=True)

        # Create a Label to display the slider value
        self.title = tk.Label(frame, text=self.title, bg="black", fg="white", font=("Helvetica", 40))
        self.title.pack(pady=50)

        # Create an IntVar to hold the scale value
        self.scale_var = tk.IntVar()

        # Set the initial value to data value
        if self.type=="light":
            normalized_value = math.ceil(self.data[self.entity]["brightness"]/self.value_scale)
            self.scale_var.set(normalized_value)
        else:
            self.scale_var.set(self.data[self.entity])


        # Create a Canvas widget for the color box
        self.box_width = 720
        self.box_height = 490
        text_box_width = 130
        if self.type=="cover":
            text_box_width = 300
        text_box_height = 100
        self.canvas = tk.Canvas(frame, background="#000000", width=self.box_width, height=self.box_height, highlightthickness=0, relief=tk.FLAT, borderwidth=0)
        self.canvas.pack(pady=0)

        # Create an initial color box
        self.feedback_box = self.canvas.create_rectangle(-1, -1, self.box_width, self.box_height, fill="#FFFFFF")
        self.text_box = self.canvas.create_rectangle(math.ceil((self.box_width-text_box_width)/2), math.ceil((self.box_height-text_box_height)/2), self.box_width-math.ceil((self.box_width-text_box_width)/2), self.box_height-math.ceil((self.box_height-text_box_height)/2), fill="#000000", width=0)

        # Create a text item to display the slider value
        self.value_text = self.canvas.create_text(math.ceil(self.box_width/2), math.ceil(self.box_height/2), text="", font=("Helvetica", 40), fill="white")

        # Update the color box initially
        self.update_box(self.scale_var.get())

        # Create a Slider widget
        slider_width = 120
        slider_height = 80
        slider = tk.Scale(frame, 
                        showvalue=False,
                        from_=0, 
                        to=100, 
                        bg=self.main_app.settings.button_color.get("down"), 
                        activebackground=self.main_app.settings.button_color.get("down"),
                        fg="white",
                        sliderrelief="flat", 
                        sliderlength=slider_width, 
                        width=slider_height,
                        orient="horizontal", 
                        #tickinterval=50, 
                        length=self.box_width,
                        variable=self.scale_var,
                        borderwidth=0,
                        command=self.on_slider_change
                        )

        slider.bind("<ButtonRelease-1>", self.on_slider_release)
        slider.pack()

        # Create another widget using place and position it absolutely
        image_path= os.fspath(pathlib.Path(__file__).parent / f'images/buttons/back-white.png')
        button_image = tk.PhotoImage(file=image_path)
        back_label = tk.Label(frame, bg="black", image=button_image)
        back_label.image = button_image
        back_label.place(x=27, y=27)
        back_label.bind('<ButtonRelease-1>', self.destroy_slider)

    def on_slider_change(self,value):
        self.update_box(value)

    def on_slider_release(self,event):
        # This function is called when the slider value changes
        self.main_app.mqtt_controller.publish_action(self.entity,self.scale_var.get())
        self.close_timer()

    def update_box(self,value):
        if self.type=="cover":
            self.update_box_size(self.scale_var.get())
            self.canvas.itemconfig(self.value_text, text=f"{int(value)}% open")
        elif self.type=="light":
            self.update_color_box(self.scale_var.get())
            self.canvas.itemconfig(self.value_text, text=f"{int(value)}%")

    def update_box_size(self,value):
        percent = 1-(value/100)
        self.canvas.coords(self.feedback_box, -1, -1, self.box_width, self.box_height*percent)

    def update_color_box(self,value):
        color = self.interpolate_color(value)
        self.canvas.itemconfig(self.feedback_box, fill=color)

    def interpolate_color(self,input_value):
        # Define the start (black) and end (yellow) colors
        start_color = "#000000"
        end_color = "#FFE500"

        # Convert hex colors to RGB tuples
        start_rgb = tuple(int(start_color[i:i+2], 16) for i in (1, 3, 5))
        end_rgb = tuple(int(end_color[i:i+2], 16) for i in (1, 3, 5))

        # Calculate the intermediate RGB values
        interpolated_rgb = tuple(int(start_rgb[i] + (end_rgb[i] - start_rgb[i]) * (input_value / 100.0)) for i in range(3))

        # Convert the interpolated RGB value to a hex color
        interpolated_color = f'#{interpolated_rgb[0]:02X}{interpolated_rgb[1]:02X}{interpolated_rgb[2]:02X}'

        return interpolated_color

    def close_timer(self,startnew=True):
        if self.close_timeout:
            self.window.after_cancel(self.close_timeout)

        if(startnew):
            self.close_timeout = self.window.after(self.main_app.settings.destroy_slider_timeout, self.destroy_slider)


    def destroy_slider(self, event=None):
        self.main_app.check_idle_timer()
        self.main_app.display_controller.start_menu_timer()
        self.window.destroy()

