import tkinter as tk
import aiohttp
import asyncio
from PIL import Image, ImageTk
from io import BytesIO

class MainApp:
    def __init__(self, root):
        self.root = root
        self.root.geometry("500x500")
        self.root.title("Async Image Fetch")

        self.label = tk.Label(root)
        self.label.pack()

        # Bind the mouse press event to the fetch_image method
        self.root.bind("<Button-1>", self.on_mouse_press)

    async def fetch_image(self):
        url = "https://cataas.com/cat"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                image_bytes = await response.read()
                image = Image.open(BytesIO(image_bytes))
                image = ImageTk.PhotoImage(image)
                self.label.configure(image=image)
                self.label.image = image  # Keep a reference to prevent garbage collection

    def on_mouse_press(self, event):
        asyncio.run(self.fetch_image())  # Use asyncio.run to create an event loop

if __name__ == "__main__":
    root = tk.Tk()
    app = MainApp(root)
    root.mainloop()
