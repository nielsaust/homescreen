import math
import tkinter as tk

# Create a tkinter window
window = tk.Tk()
window.title("Slider Example")
frame = tk.Frame(window, bg="black")
frame.pack(fill=tk.BOTH, expand=True)
window.geometry("720x720")

# Create a Label to display the slider value
label = tk.Label(frame, text="Woonkamer lamp", bg="black", fg="white", font=("Helvetica", 40))
label.pack(pady=50)

# Create an IntVar to hold the scale value
scale_var = tk.IntVar()

# Set the initial value to 60
scale_var.set(60)
def on_slider_change(value):
    new_height = math.floor(box_height-box_height/(100-(scale_var.get()+1)))
    print(new_height, scale_var.get()/100)
    percent = 1-(scale_var.get()/100)
    canvas.coords(color_box, -1, -1, box_width, box_height*percent)
    update_color_box(scale_var.get())

def on_slider_release(event):
    # This function is called when the slider value changes
    print(f"Slider Released: {scale_var.get()}")

def update_color_box(value):
    # Update the color box based on the slider value
    red_value = int((value / 100) * 255)
    green_value = int((value / 100) * 255)
    blue_value = int((value / 100) * 255)
    color = f'#{red_value:02X}{green_value:02X}{blue_value:02X}'
    canvas.itemconfig(color_box, fill=color)
    canvas.itemconfig(value_text, text=f"{int(value)}")


# Create a Canvas widget for the color box
box_width = 500
box_height = 400
text_box_width = 100
text_box_height = 50
canvas = tk.Canvas(frame, width=box_width, height=box_height, highlightthickness=0, relief=tk.FLAT, borderwidth=0)
canvas.pack(pady=0)

# Create an initial color box
color_box = canvas.create_rectangle(-1, -1, box_width, box_height, fill="#000000")
text_box = canvas.create_rectangle(math.ceil((box_width-text_box_width)/2), math.ceil((box_height-text_box_height)/2), box_width-math.ceil((box_width-text_box_width)/2), box_height-math.ceil((box_height-text_box_height)/2), fill="#000000", width=0)

# Create a text item to display the slider value
value_text = canvas.create_text(math.ceil(box_width/2), math.ceil(box_height/2), text="", font=("Helvetica", 40), fill="white")

# Update the color box initially
update_color_box(scale_var.get())

# Create a Slider widget
slider_width = 80
slider_height = 50
slider = tk.Scale(frame, 
                  showvalue=False,
                  from_=0, 
                  to=100, 
                  bg="blue", 
                  activebackground="blue",
                  fg="white",
                  sliderrelief="flat", 
                  sliderlength=slider_width, 
                  width=slider_height,
                  orient="horizontal", 
                  #tickinterval=50, 
                  length=box_width,
                  variable=scale_var,
                  borderwidth=0,
                  command=on_slider_change
                  )

slider.bind("<ButtonRelease-1>", on_slider_release)
slider.pack()


# Create another widget using place and position it absolutely
label2 = tk.Label(frame, text="close")
label2.place(x=10, y=10)

# Start the tkinter main loop
window.mainloop()
