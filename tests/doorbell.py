import logging

from settings import Settings
logger = logging.getLogger(__name__)

from requests.auth import HTTPDigestAuth
from PIL import Image, ImageTk
from io import BytesIO
import requests
import time
import paho.mqtt.client as mqtt
import tkinter as tk
import os

UPDATE_IMAGE_INTERAL = 10
UPDATE_AMOUNT = 3

class FrontDoor:
    def __init__(self):
        self.is_showing = False
        self.is_created = False

        # load settings
        self.settings = Settings("settings.json")
        self.image_width = self.settings.screen_width
        self.image_height = self.settings.screen_height
        self.loop_amount = 0
        self.init_mqtt()

    def init_mqtt(self):
        # Create an MQTT client
        client = mqtt.Client()

        # Set the on_connect and on_message callback functions
        client.on_connect = self.on_connect
        client.on_message = self.on_message

        username = self.settings.mqtt_user
        password = self.settings.mqtt_password
        
        client.username_pw_set(username, password)
        client.connect(self.settings.mqtt_broker)  

        client.loop_forever()  
    
    def make_request(self, url, auth):
        for i in range(3):
            try:
                if(auth):
                    response = requests.get(url, auth=auth)
                else:
                    response = requests.get(url)
                # If the request was successful, return the response
                return response
            except Exception as e:
                # Log the error
                logger.error(f'Error getting the image: {e}')
                # If this is the last attempt, re-raise the exception to propagate it up the call stack
                if i == 2:
                    raise
        # If the request was not successful after three attempts, return None
        return None

    def doorbell_loop(self):
        refresh_amount = 0
        self.running = True
        self.show_door(True)
        first_run = True

        while self.running:
            if self.loop_amount >= UPDATE_IMAGE_INTERAL or first_run:
                self.update_image()
                if(refresh_amount>=UPDATE_AMOUNT):
                    self.stop_doorbell()
                    break
                refresh_amount+=1
                self.loop_amount=0
                
            self.loop_amount+=1
            first_run = False
            self.root.update()
            time.sleep(1)


    def stop_doorbell(self):
        self.running = False
        self.show_door(False)
    
    def update_image(self):
        ip = self.settings.doorbell_url
        path = self.settings.doorbell_path

        capture_url = f'http://{ip}{path}'
        auth = HTTPDigestAuth(self.settings.doorbell_username,self.settings.doorbell_password)
        frontdoor_image_response = self.make_request(capture_url,auth)

        frontdoor_img = Image.open(BytesIO(frontdoor_image_response.content))
        
        self.frontdoor_image = ImageTk.PhotoImage(frontdoor_img)

        self.label_condition.configure(image=self.frontdoor_image, width=self.image_width, height=self.image_height)
        self.root.update()
        
    def show_door(self, show=True):
        self.is_showing = show
        if(show):
            self.root = tk.Tk()
            self.root.geometry(f"{self.settings.screen_width}x{self.settings.screen_height}")
            if os.name!='nt':
                self.root.attributes("-fullscreen", True)
            
            background_color = 'black'
            foreground_color = 'white'

            self.main_frame = tk.Frame(self.root, background=background_color, width=self.image_width, height=self.image_height)
            self.sub_frame = tk.Frame(self.main_frame, background=background_color, width=self.image_width, height=self.image_height)
            self.sub_frame.grid_propagate(False)

            self.main_frame.grid(row=0, column=0, sticky="nsew")
            self.sub_frame.grid(row=0, column=0, sticky="nsew")
            
            self.label_condition = tk.Label(self.sub_frame,text='IMAGE', bg=background_color, fg=foreground_color)
            self.label_condition.grid(row=0,column=0)
            
            self.click_bind = self.root.bind("<Button-1>", self.on_click)
            
            self.is_created = True
        else:
            self.root.unbind("<Button-1>", self.click_bind)
            self.root.destroy()

    
    def on_click(self, event):
        self.stop_doorbell()
         

    def on_connect(self, client, userdata, flags, rc):
        # Subscribe to the doorbell topic
        client.subscribe("doorbell")

    def on_message(self, client, userdata, msg):
        # Get the message payload
        payload = msg.payload.decode()

        # If the payload is "True", start the video stream
        if payload == "True":
            self.doorbell_loop()

class Main:    
    def __init__(self):       
        self.frontdoor = FrontDoor()

if __name__ == "__main__":
    main = Main()
