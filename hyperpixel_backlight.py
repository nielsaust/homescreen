import logging
import os

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
            logger.error("Backlight control not available, please ensure RPi.GPIO python3 package is installed")
            return

        GPIO.setwarnings(False)
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(BACKLIGHT_PIN, GPIO.OUT)
            self.active = True
        except RuntimeError:
            self.active = False
            username = os.environ.get('USER')
            logger.error("Backlight control not available, please ensure '%s' is part of group 'gpio'.", username)
            logger.error("To add user to group: `sudo gpasswd -a %s gpio`", username)
        else:
            self.set_power(initial_value)

    def set_power(self, new_state):
        """Control the backlight power of the HyperPixel display."""
        if not self.active:
            return

        if new_state is False and self.power:
            logger.debug("Going idle, turning backlight off")
        self.power = new_state
        GPIO.output(BACKLIGHT_PIN, new_state)

    def cleanup(self):
        """Return the GPIO setup to initial state."""
        if self.active:
            GPIO.output(BACKLIGHT_PIN, True)
            GPIO.cleanup()
