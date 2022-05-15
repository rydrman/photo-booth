from typing import Any, Tuple
import abc
import cv2
import math

import numpy
import structlog

from . import input
from .join_images import join_images, Vec2

_LOGGER = structlog.get_logger(__name__)
#_FONT = cv2.freetype.createFreeType2()
#_FONT.loadFontData(fontFileName="/usr/share/fonts/truetype/quicksand/Quicksand-Light.ttf", id=0)
_FONT = cv2.FONT_HERSHEY_COMPLEX

class State(abc.ABC):

    @abc.abstractmethod
    def tick(self, frame, delta_time_s: float, key: int = None) -> Tuple[Any, "State"]:
        ...


class WelcomeState(State):

    def tick(self, frame, delta_time_s: float, key: int = None) -> Tuple[Any, "State"]:

        input.set_blue_button_light(on=True)
        input.set_red_button_light(on=False)
        
        cv2.putText(frame, "Mike & Caro's Photo Booth!", (100,100), _FONT, 1, (0,0,0))
        cv2.putText(frame, "Mike & Caro's Photo Booth!", (101,101), _FONT, 1, (255, 255, 255))
        cv2.putText(frame, "Get ready for FOUR photos.", (100,200), _FONT, 1, (0,0,0))
        cv2.putText(frame, "Get ready for FOUR photos.", (101,201), _FONT, 1, (255, 255, 255))
        cv2.putText(frame, "Press the blue button to start.", (100,300), _FONT, 1, (0,0,0))
        cv2.putText(frame, "Press the blue button to start.", (101,301), _FONT, 1, (255, 255, 255))
        
        if key == 32 or input.get_blue_button(): # space
            input.set_blue_button_light(on=False)
            return (frame, CountdownState())
        return (frame, self)

class TestState(State):

    def tick(self, frame, delta_time_s: float, key: int = None) -> Tuple[Any, "State"]:
        
        input.set_blue_button_light(on=input.get_blue_button())
        input.set_red_button_light(on=input.get_red_button())
        return (frame, self)

class CountdownState(State):

    def __init__(self, photo_number: int = 0) -> None:
        self._total_delay_s = 3.0
        self._ellapsed_s = 0
        self._photo_number = photo_number

    def tick(self, frame, delta_time_s: float, key: int = None) -> Tuple[Any, "State"]:
        
        self._ellapsed_s += delta_time_s
        remaining_time = self._total_delay_s - self._ellapsed_s
        if remaining_time <= 0 or key == 32: # space
            return frame, TakePhotoState(frame, self._photo_number)

        cv2.putText(frame, str(math.ceil(remaining_time)), (100,100), cv2.FONT_HERSHEY_COMPLEX, 1, (0,0,0))
        return (frame, self)


class TakePhotoState(State):

    def __init__(self, frame, photo_number: int = 0) -> None:

        self._ellapsed = 0
        self._frame = frame
        self._photo_number = photo_number
        self._white_frame = numpy.full_like(frame, 255)

        filename = f"photo_{photo_number+1}.png"
        _LOGGER.info(f"saving image {filename}...")
        cv2.imwrite(filename, frame)


    def tick(self, frame, delta_time_s: float, key: int = None) -> Tuple[Any, "State"]:
        
        self._ellapsed += delta_time_s

        transition_amount = self._ellapsed / 1.0
        if transition_amount < 1:

            frame = cv2.addWeighted(frame, 1.0, self._white_frame, 1.0-transition_amount, 0.0)
            return frame, self

        next_photo = self._photo_number + 1
        if next_photo < 4:
            return frame, CountdownState(next_photo) 
        else:
            # TODO: print dialog state
            return frame, PrintPhotoState()
    

class PrintPhotoState(State):

    def __init__(self) -> None:
        self._joined_image = join_images("photo_1.png", "photo_2.png", "photo_3.png", "photo_4.png")
        cv2.imwrite("out.png", self._joined_image)

    def tick(self, frame, delta_time_s: float, key: int = None) -> Tuple[Any, "State"]:

        input.set_blue_button_light(on=True)
        input.set_red_button_light(on=True)

        if key == 121 or input.get_blue_button(): # y
            _LOGGER.info("printing image...")
            # TODO: print
            return frame, WelcomeState()
        elif key == 110 or input.get_red_button(): # n
            _LOGGER.info("saving image secretly... 🤫")
            return frame, WelcomeState()
        else:
            return self._joined_image, self




def resize_to_fit(im, desired: Vec2):
    scale_x = float(desired.x) / float(im.shape[1])
    scale_y = float(desired.y) / float(im.shape[0])
    scale = min(scale_x, scale_y)
    return cv2.resize(im, (math.ceil(scale * im.shape[1]), math.ceil(scale * im.shape[0])))