import os
import tkinter as tk
from tkinter import messagebox

def reboot_system():
    """Reboot the system after confirmation."""
    if messagebox.askyesno("Reboot System", "Are you sure you want to reboot the system?"):
        try:
            os.system("sudo reboot")
        except Exception as e:
            print(f"Failed to reboot the system: {e}")
            messagebox.showerror("Error", f"Failed to reboot the system: {e}")

def update_network_availability(self, network_available):
    """
    Updates the UI based on network availability.
    """
    if network_available:
        self.no_connection_label.place_forget()
        self.no_connection_label.unbind("<Button-1>")
    else:
        print("Network unavailable.")

        # Make the label tappable
        self.no_connection_label.config(
            text="No Connection. Tap to reboot.",
            fg="red",
            cursor="hand2"
        )
        self.no_connection_label.place(relx=.95, rely=.95, anchor='se')

        # Bind click event to reboot function
        self.no_connection_label.bind("<Button-1>", lambda event: reboot_system())

reboot_system()