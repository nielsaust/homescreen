from __future__ import annotations
import sys
from tkinter import messagebox
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import MainApp


import subprocess
import logging
logger = logging.getLogger(__name__)

import time

class TouchController:
    def __init__(self, main_app: MainApp):  # You can set the default hold_time here (in seconds)
        self.main_app = main_app
        from app.controllers.action_dispatcher import ActionDispatcher
        self.action_dispatcher = ActionDispatcher(main_app, self)
        self.hold_time = self.main_app.settings.hold_time  # Store the hold time threshold
        self.click_time = None  # To store the time of the initial click
        self.ignore_next_click = False
        self.start_x = 0
        self.start_y = 0

    def bind_events(self, root):
        root.bind("<Button-1>", self.handle_down)
        root.bind("<ButtonRelease-1>", self.handle_up)
        root.bind("<Left>", self.handle_left_key)
        root.bind("<Right>", self.handle_right_key)
        root.bind("<Up>", self.handle_up_key)
        root.bind("<Down>", self.handle_down_key)
        root.bind("<KeyPress-space>", self.handle_space_down)
        root.bind("<KeyRelease-space>", self.handle_space_up)

    def handle_left_key(self, event):
        self.main_app.perform_action("left")

    def handle_right_key(self, event):
        self.main_app.perform_action("right")

    def handle_up_key(self, event):
        self.main_app.perform_action("up")

    def handle_down_key(self, event):
        self.main_app.perform_action("down")

    def handle_double_click(self, event):
        logger.debug("Double click performed; no action performed.")

    def handle_space_down(self, event):
        self.handle_down(event)

    def handle_space_up(self, event):
        self.handle_up(event)

    def handle_down(self, event):
        # Record the time of the initial click
        self.click_time = time.time()
        self.start_x = event.x_root
        self.start_y = event.y_root
        logger.debug(f"Touch down @ {self.click_time}")

    def handle_up(self, event):
        self.handle_gestures(event)
        self.click_time = None  # Reset click time

    def handle_hold(self, time_held):
        logger.debug(f"Touch held for more than {self.hold_time} ({time_held}) seconds")
        self.main_app.perform_action("hold")

    def handle_gestures(self, event):
        # Determine the direction of the swipe
        x_dir = event.x_root - self.start_x
        y_dir = event.y_root - self.start_y
        x_abs = abs(x_dir)
        y_abs = abs(y_dir)
        min_movement = self.main_app.settings.gesture_min_movement
        action = None
        
        if x_abs > y_abs and x_dir > min_movement:
            self.main_app.perform_action("left")
        elif x_abs > y_abs and x_dir < -min_movement:
            self.main_app.perform_action("right")
        elif x_abs < y_abs and y_dir > min_movement:
            self.main_app.perform_action("down")
        elif x_abs < y_abs and y_dir < -min_movement:
            self.main_app.perform_action("up")
        else:
            logger.debug(f"Should be single click (click_time = {self.click_time})")
            # no swipe (click or hold)
            if self.click_time is not None:
                release_time = time.time()
                time_elapsed = release_time - self.click_time

                if time_elapsed >= self.hold_time:
                    self.handle_hold(time_elapsed)
                else:
                    logger.debug(f"Time between click and release: {time_elapsed} seconds")
                    self.main_app.perform_action("single_click")
            else:
                logger.error("click_time is NONE")


    def handle_alt_menu_button(self, action): # hold actions
        self.ignore_next_click = True
        
        if action=="light_woonkamer":
            self.main_app.display_controller.show_show_slider("light_woonkamer","Woonkamer licht")
        elif action=="light_keuken":
            self.main_app.display_controller.show_show_slider("light_keuken","Keuken licht")
        elif action=="light_kleur":
            self.main_app.display_controller.show_show_slider("light_kleur","Kleur licht")
        elif action=="light_tafel":
            self.main_app.display_controller.show_show_slider("light_tafel","Tafel licht")
        elif action=="cover_kitchen":
            self.main_app.display_controller.show_show_slider("cover_kitchen","Rolgordijn keuken","cover")


    def handle_menu_button(self, action):
        logger.debug(f"handle_menu_button: {action}")
        self.ignore_next_click = True
        self.action_dispatcher.dispatch(action)

    def quit_app(self):
        quit();

    def reboot(self,ask=True):
        """Reboots the system."""
        self.shell_command("reboot", use_sudo=True, ask=ask)

    def disable_networking(self):
        """Disables networking using nmcli."""
        self.shell_command("systemctl stop dhcpcd", use_sudo=True, ask=True)

    def enable_networking(self):
        """Enables networking using nmcli."""
        self.shell_command("systemctl start dhcpcd", use_sudo=True, ask=True)

    def recover_network(self, interface="wlan0", retries=5, delay=2):
        """
        Attempts to recover network connectivity by restarting the network interface,
        renewing DHCP, and resetting DNS and routes.

        Args:
            interface (str): The name of the network interface to recover (e.g., 'wlan0').
        """
        if messagebox.askyesno("Recover Network", f"Shall we try to recover network connectivity?"):
            logger.warning("Starting network recovery process.")

            # Bring the interface down
            logger.info(f"Bringing down the interface: {interface}")
            self.shell_command(f"ip link set {interface} down", use_sudo=True, ask=False)

            # Bring the interface back up
            logger.info(f"Bringing up the interface: {interface}")
            self.shell_command(f"ip link set {interface} up", use_sudo=True, ask=False)

            # Renew the DHCP lease
            logger.info(f"Renewing DHCP lease on interface: {interface}")
            self.shell_command(f"dhcpcd -k {interface}", use_sudo=True, ask=False)
            self.shell_command(f"dhcpcd {interface}", use_sudo=True, ask=False)

            # Reset DNS
            logger.info("Resetting DNS resolver.")
            try:
                self.shell_command("resolvectl flush-caches", use_sudo=True, ask=False)
            except Exception:
                self.shell_command('echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf', use_sudo=False)

            # Rebuild routing table
            logger.info("Rebuilding routing table.")
            self.shell_command("ip route flush table main", use_sudo=True, ask=False)
            self.shell_command("systemctl restart dhcpcd", use_sudo=True, ask=False)

            # Step 6: Test connectivity with retries
            logger.info(f"Testing connectivity to 8.8.8.8 with up to {retries} retries.")
            for attempt in range(1, retries + 1):
                stdout, stderr, return_code = self.shell_command("ping -c 1 8.8.8.8", use_sudo=False)
                if return_code == 0:
                    logger.info("Network recovery successful.")
                    break
                else:
                    logger.warning(f"Ping failed (attempt {attempt}/{retries}): {stderr}")
                    if attempt < retries:
                        logger.info(f"Retrying in {delay} seconds...")
                        time.sleep(delay)
                    else:
                        logger.error("Network recovery failed after multiple attempts.")
            logger.warning("Network recovery process completed.")
        else:
            logger.info("Network recovery process canceled.")

    def shell_command(self, command, use_sudo=False, ask=True):
        """
        Executes a shell command with optional sudo privileges.

        Args:
            command (str): The command to execute.
            use_sudo (bool): Whether to prepend 'sudo' to the command.

        Returns:
            tuple: (stdout, stderr, return_code)
        """
        try:
            # Prepend sudo if needed
            command = f"sudo {command}" if use_sudo else command
            logger.info(f"Executing shell command: {command}, ask: {ask}")

            # Execute the command
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            out, err = process.communicate()

            # Decode stdout and stderr
            stdout = out.decode('utf-8').strip()
            stderr = err.decode('utf-8').strip()

            # Return the results
            return stdout, stderr, process.returncode
        except Exception as e:
            logger.critical(f"Failed to execute command '{command}': {e}")
            return "", str(e), -1  # Always return a tuple, even on failure
