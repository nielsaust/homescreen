import pathlib
import tkinter as tk
from itertools import cycle
from PIL import Image, ImageTk

root = tk.Tk()
root.title("Loading...")

# Load the GIF and split it into frames
gif_path = pathlib.Path(__file__).parent / 'loading.gif'  # Path to your GIF file
gif_image = Image.open(gif_path)
frames = []
try:
    while True:
        frame = ImageTk.PhotoImage(gif_image.copy())
        frames.append(frame)
        gif_image.seek(len(frames))  # Move to the next frame
except EOFError:
    pass  # End of frames

frame_cycle = cycle(frames)

# Label to display the GIF
label = tk.Label(root)
label.pack()

# Function to loop through GIF frames
def animate():
    label.config(image=next(frame_cycle))
    root.after(100, animate)  # Adjust delay for speed

animate()
root.mainloop()