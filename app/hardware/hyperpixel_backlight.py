import logging
import os
from app.observability.domain_logger import log_event

logger = logging.getLogger(__name__)

try:
    import RPi.GPIO as GPIO
except ImportError:
    logger.critical("Could not import RPi.GPIO.")
    GPIO = None

BACKLIGHT_PIN = 19

class Backlight():

    def __init__(self, initial_value=False):
        """Initialize the backlight instance."""
        self.power = None

        if not GPIO:
            self.active = False
            log_event(logger, logging.ERROR, "display", "backlight.unavailable", reason="rpi_gpio_not_installed")
            return

        GPIO.setwarnings(False)
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(BACKLIGHT_PIN, GPIO.OUT)
            self.active = True
        except RuntimeError:
            self.active = False
            username = os.environ.get('USER')
            log_event(logger, logging.ERROR, "display", "backlight.unavailable", reason="gpio_permission", user=username)
            log_event(logger, logging.ERROR, "display", "backlight.permission_hint", command=f"sudo gpasswd -a {username} gpio")
        else:
            log_event(logger, logging.INFO, "display", "backlight.ready", pin=BACKLIGHT_PIN)
            self.set_power(initial_value)

    def set_power(self, new_state):
        """Control the backlight power of the HyperPixel display."""
        if not self.active:
            log_event(logger, logging.DEBUG, "display", "backlight.set_power_skipped", reason="inactive_driver")
            return

        if new_state is False and self.power:
            log_event(logger, logging.DEBUG, "display", "backlight.off")
        self.power = new_state
        log_event(logger, logging.INFO, "display", "backlight.set_power", state=bool(new_state))
        GPIO.output(BACKLIGHT_PIN, new_state)

    def cleanup(self):
        """Return the GPIO setup to initial state."""
        if self.active:
            GPIO.output(BACKLIGHT_PIN, True)
            GPIO.cleanup()
