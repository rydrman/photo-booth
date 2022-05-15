import atexit

import structlog
import RPi.GPIO as GPIO

REQUIRED_INPUT_FRAMES = 3

BLUE_BUTTON_LIGHT_PIN=10
BLUE_BUTTON_PIN=13
BLUE_BUTTON_HISTORY = [0, 0, 0, 0, 0]

RED_BUTTON_LIGHT_PIN=8
RED_BUTTON_PIN=15
RED_BUTTON_HISTORY = [0, 0, 0, 0, 0]

_LOGGER = structlog.get_logger(__name__)

def initialize():
    # Use physical pin numbering
    GPIO.setwarnings(False) 
    GPIO.setmode(GPIO.BOARD) 
    # Set pin 10 to be an input pin and set initial value to be pulled low (off)
    GPIO.setup(BLUE_BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) 
    GPIO.setup(BLUE_BUTTON_LIGHT_PIN, GPIO.OUT) 
    GPIO.output(BLUE_BUTTON_LIGHT_PIN, GPIO.LOW) 
    GPIO.setup(RED_BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) 
    GPIO.setup(RED_BUTTON_LIGHT_PIN, GPIO.OUT) 
    GPIO.output(RED_BUTTON_LIGHT_PIN, GPIO.LOW) 

    atexit.register(lambda: GPIO.cleanup())

def tick():

    RED_BUTTON_HISTORY.pop(0)
    RED_BUTTON_HISTORY.append(_read_red_button())
    BLUE_BUTTON_HISTORY.pop(0)
    BLUE_BUTTON_HISTORY.append(_read_blue_button())

def get_red_button() -> bool:

    return all(RED_BUTTON_HISTORY[-REQUIRED_INPUT_FRAMES:])

def _read_red_button() -> int:

    pressed = GPIO.input(RED_BUTTON_PIN)
    return pressed

def get_blue_button() -> bool:

    return all(BLUE_BUTTON_HISTORY[-REQUIRED_INPUT_FRAMES:])

def _read_blue_button() -> int:

    pressed = GPIO.input(BLUE_BUTTON_PIN)
    return pressed

def set_red_button_light(on: bool) -> None:

    _set_button_light(RED_BUTTON_LIGHT_PIN, on)

def set_blue_button_light(on: bool) -> None:

    _set_button_light(BLUE_BUTTON_LIGHT_PIN, on)

def _set_button_light(pin: int, on: bool) -> None:

    GPIO.output(pin, not on)
