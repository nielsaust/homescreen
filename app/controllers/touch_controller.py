from __future__ import annotations
import sys
from tkinter import messagebox
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import MainApp


import subprocess
import logging
logger = logging.getLogger(__name__)
from app.observability.domain_logger import log_event

import time

class TouchController:
    def __init__(self, main_app: MainApp):  # You can set the default hold_time here (in seconds)
        self.main_app = main_app
        from app.controllers.action_dispatcher import ActionDispatcher
        self.action_dispatcher = ActionDispatcher(main_app, self)
        # Expose dispatcher on main_app for startup/background action flows.
        self.main_app.action_dispatcher = self.action_dispatcher
        self.hold_time = self.main_app.settings.hold_time  # Store the hold time threshold
        self.click_time = None  # To store the time of the initial click
        self.ignore_next_click = False
        self.ignore_click_until = 0.0
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
        if self._handle_menu_edit_icon_key(-1):
            return "break"
        self.main_app.interaction_service.handle("left")
        return "break"

    def handle_right_key(self, event):
        if self._handle_menu_edit_icon_key(1):
            return "break"
        self.main_app.interaction_service.handle("right")
        return "break"

    def handle_up_key(self, event):
        self.main_app.interaction_service.handle("up")

    def handle_down_key(self, event):
        self.main_app.interaction_service.handle("down")

    def _handle_menu_edit_icon_key(self, step):
        display = getattr(self.main_app, "display_controller", None)
        if display is None:
            return False
        menu_screen = getattr(display, "screen_objects", {}).get("menu")
        if menu_screen is None:
            return False
        handler = getattr(menu_screen, "handle_edit_icon_key", None)
        if not callable(handler):
            return False
        try:
            return bool(handler(step))
        except Exception:
            return False

    def handle_double_click(self, event):
        log_event(logger, logging.DEBUG, "touch", "gesture.double_click_ignored")

    def handle_space_down(self, event):
        self.handle_down(event)

    def handle_space_up(self, event):
        self.handle_up(event)

    def handle_down(self, event):
        # Record the time of the initial click
        self.click_time = time.time()
        self.start_x = event.x_root
        self.start_y = event.y_root
        log_event(logger, logging.DEBUG, "touch", "gesture.down", ts=self.click_time)

    def handle_up(self, event):
        self.handle_gestures(event)
        self.click_time = None  # Reset click time

    def handle_hold(self, time_held):
        log_event(logger, logging.DEBUG, "touch", "gesture.hold", hold_threshold=self.hold_time, held_seconds=time_held)
        self.main_app.interaction_service.handle("hold")

    def handle_gestures(self, event):
        # Determine the direction of the swipe
        x_dir = event.x_root - self.start_x
        y_dir = event.y_root - self.start_y
        x_abs = abs(x_dir)
        y_abs = abs(y_dir)
        min_movement = self.main_app.settings.gesture_min_movement
        action = None
        
        if x_abs > y_abs and x_dir > min_movement:
            self.main_app.interaction_service.handle("left")
        elif x_abs > y_abs and x_dir < -min_movement:
            self.main_app.interaction_service.handle("right")
        elif x_abs < y_abs and y_dir > min_movement:
            self.main_app.interaction_service.handle("down")
        elif x_abs < y_abs and y_dir < -min_movement:
            self.main_app.interaction_service.handle("up")
        else:
            log_event(logger, logging.DEBUG, "touch", "gesture.single_click_candidate", click_time=self.click_time)
            # no swipe (click or hold)
            if self.click_time is not None:
                release_time = time.time()
                time_elapsed = release_time - self.click_time

                if time_elapsed >= self.hold_time:
                    self.handle_hold(time_elapsed)
                else:
                    log_event(logger, logging.DEBUG, "touch", "gesture.single_click", elapsed_seconds=time_elapsed)
                    self.main_app.interaction_service.handle("single_click")
            else:
                log_event(logger, logging.ERROR, "touch", "gesture.error", reason="click_time_missing")

    def handle_menu_button(self, action):
        log_event(logger, logging.DEBUG, "touch", "menu.button_action", action=action)
        self.action_dispatcher.dispatch(action)

    def suppress_next_click(self, window_ms=350):
        # Guard against duplicate root single-click callbacks after menu button handlers.
        self.ignore_next_click = True
        self.ignore_click_until = time.time() + (window_ms / 1000.0)

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
        title = self.main_app.t("dialog.recover_network.title", default="Recover Network")
        question = self.main_app.t(
            "dialog.recover_network.question",
            default="Shall we try to recover network connectivity?",
        )
        if messagebox.askyesno(title, question):
            log_event(logger, logging.WARNING, "network", "recovery.start")

            # Bring the interface down
            log_event(logger, logging.INFO, "network", "recovery.interface_down", interface=interface)
            self.shell_command(f"ip link set {interface} down", use_sudo=True, ask=False)

            # Bring the interface back up
            log_event(logger, logging.INFO, "network", "recovery.interface_up", interface=interface)
            self.shell_command(f"ip link set {interface} up", use_sudo=True, ask=False)

            # Renew the DHCP lease
            log_event(logger, logging.INFO, "network", "recovery.dhcp_renew", interface=interface)
            self.shell_command(f"dhcpcd -k {interface}", use_sudo=True, ask=False)
            self.shell_command(f"dhcpcd {interface}", use_sudo=True, ask=False)

            # Reset DNS
            log_event(logger, logging.INFO, "network", "recovery.dns_reset")
            try:
                self.shell_command("resolvectl flush-caches", use_sudo=True, ask=False)
            except Exception:
                self.shell_command('echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf', use_sudo=False)

            # Rebuild routing table
            log_event(logger, logging.INFO, "network", "recovery.route_rebuild")
            self.shell_command("ip route flush table main", use_sudo=True, ask=False)
            self.shell_command("systemctl restart dhcpcd", use_sudo=True, ask=False)

            # Step 6: Test connectivity with retries
            log_event(logger, logging.INFO, "network", "recovery.ping_test_start", retries=retries)
            for attempt in range(1, retries + 1):
                stdout, stderr, return_code = self.shell_command("ping -c 1 8.8.8.8", use_sudo=False)
                if return_code == 0:
                    log_event(logger, logging.INFO, "network", "recovery.success")
                    break
                else:
                    log_event(logger, logging.WARNING, "network", "recovery.ping_failed", attempt=attempt, retries=retries, error=stderr)
                    if attempt < retries:
                        log_event(logger, logging.INFO, "network", "recovery.retry_scheduled", delay_seconds=delay)
                        time.sleep(delay)
                    else:
                        log_event(logger, logging.ERROR, "network", "recovery.failed")
            log_event(logger, logging.WARNING, "network", "recovery.completed")
        else:
            log_event(logger, logging.INFO, "network", "recovery.canceled")

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
            log_event(logger, logging.INFO, "touch", "shell.command", command=command, ask=ask)

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
            log_event(logger, logging.CRITICAL, "touch", "shell.command_failed", command=command, error=e)
            return "", str(e), -1  # Always return a tuple, even on failure
