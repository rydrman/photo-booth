from typing import Any, Tuple
import abc
import cv2
import math
import subprocess

import numpy
from photo_booth import output
import structlog

from . import input
from .join_images import join_images, Vec2

_LOGGER = structlog.get_logger(__name__)
# _FONT = cv2.freetype.createFreeType2()
# _FONT.loadFontData(fontFileName="/usr/share/fonts/truetype/quicksand/Quicksand-Light.ttf", id=0)
_FONT = cv2.FONT_HERSHEY_COMPLEX


class State(abc.ABC):
    @abc.abstractmethod
    def tick(self, frame, delta_time_s: float, key: int = None) -> Tuple[Any, "State"]:
        ...


class WelcomeState(State):
    def tick(self, frame, delta_time_s: float, key: int = None) -> Tuple[Any, "State"]:

        input.set_blue_button_light(on=True)
        input.set_red_button_light(on=False)

        cv2.putText(
            frame, "Mike & Caro's Photo Booth!", (100, 100), _FONT, 1, (0, 0, 0)
        )
        cv2.putText(
            frame, "Mike & Caro's Photo Booth!", (101, 101), _FONT, 1, (255, 255, 255)
        )
        cv2.putText(
            frame, "Get ready for FOUR photos.", (100, 200), _FONT, 1, (0, 0, 0)
        )
        cv2.putText(
            frame, "Get ready for FOUR photos.", (101, 201), _FONT, 1, (255, 255, 255)
        )
        cv2.putText(
            frame, "Press the blue button to start.", (100, 300), _FONT, 1, (0, 0, 0)
        )
        cv2.putText(
            frame,
            "Press the blue button to start.",
            (101, 301),
            _FONT,
            1,
            (255, 255, 255),
        )

        if key == 32 or input.get_blue_button():  # space
            input.set_blue_button_light(on=False)
            path = output.create_output_directory()
            return (frame, CountdownState(path))
        return (frame, self)


class TestState(State):
    def tick(self, frame, delta_time_s: float, key: int = None) -> Tuple[Any, "State"]:

        input.set_blue_button_light(on=input.get_blue_button())
        input.set_red_button_light(on=input.get_red_button())
        return (frame, self)


class CountdownState(State):
    def __init__(self, out_dir: str, photo_number: int = 0) -> None:
        self._total_delay_s = 3.0
        self._ellapsed_s = 0
        self._photo_number = photo_number
        self._out_dir = out_dir

    def tick(self, frame, delta_time_s: float, key: int = None) -> Tuple[Any, "State"]:

        self._ellapsed_s += delta_time_s
        remaining_time = self._total_delay_s - self._ellapsed_s
        if remaining_time <= 0 or key == 32:  # space
            return frame, TakePhotoState(frame, self._out_dir, self._photo_number)

        cv2.putText(
            frame,
            str(math.ceil(remaining_time)),
            (100, 100),
            cv2.FONT_HERSHEY_COMPLEX,
            1,
            (0, 0, 0),
        )
        return (frame, self)


class TakePhotoState(State):
    def __init__(self, frame, out_dir: str, photo_number: int = 0) -> None:

        self._ellapsed = 0
        self._frame = frame
        self._out_dir = out_dir
        self._photo_number = photo_number
        self._white_frame = numpy.full_like(frame, 255)

        filename = f"{self._out_dir}/photo_{photo_number+1}.png"
        _LOGGER.info(f"saving image {filename}...")
        cv2.imwrite(filename, frame)

    def tick(self, frame, delta_time_s: float, key: int = None) -> Tuple[Any, "State"]:

        self._ellapsed += delta_time_s

        transition_amount = self._ellapsed / 1.0
        if transition_amount < 1:

            frame = cv2.addWeighted(
                frame, 1.0, self._white_frame, 1.0 - transition_amount, 0.0
            )
            return frame, self

        next_photo = self._photo_number + 1
        if next_photo < 4:
            return frame, CountdownState(self._out_dir, next_photo)
        else:
            return frame, PrintDialogState(self._out_dir)


class PrintDialogState(State):
    def __init__(self, out_dir: str) -> None:
        self._printer_name = "selphy"
        self._image_file = f"{out_dir}/final.png"
        self._pdf_file = f"{out_dir}/final.pdf"
        self._joined_image = join_images(
            f"{out_dir}/photo_1.png",
            f"{out_dir}/photo_2.png",
            f"{out_dir}/photo_3.png",
            f"{out_dir}/photo_4.png",
        )
        cv2.imwrite(self._image_file, self._joined_image)

    def tick(self, frame, delta_time_s: float, key: int = None) -> Tuple[Any, "State"]:

        input.set_blue_button_light(on=True)
        input.set_red_button_light(on=True)

        if key == 121 or input.get_blue_button():  # y
            _LOGGER.info("converting image to pdf...")
            try:
                subprocess.check_call(["convert", self._image_file, self._pdf_file])
            except subprocess.CalledProcessError as e:
                _LOGGER.error("Failed to convert to pdf", err=e)

            _LOGGER.info("printing image...")
            try:
                subprocess.check_call(["lp", "-d", self._printer_name, self._pdf_file])
            except subprocess.CalledProcessError as e:
                _LOGGER.error("Failed to submit print job", err=e)

            return frame, PrintingMessageState()

        elif key == 110 or input.get_red_button():  # n
            _LOGGER.info("Print rejected")
            return frame, WelcomeState()

        else:
            return self._joined_image, self


class PrintingMessageState(State):
    def __init__(self) -> None:
        self._ellapsed = 0.0

    def tick(self, frame, delta_time_s: float, key: int = None) -> Tuple[Any, "State"]:

        self._ellapsed += delta_time_s

        input.set_blue_button_light(on=True)
        input.set_red_button_light(on=False)

        cv2.putText(frame, "Your photo is printing!", (100, 100), _FONT, 1, (0, 0, 0))
        cv2.putText(
            frame, "Your photo is printing!", (101, 101), _FONT, 1, (255, 255, 255)
        )
        cv2.putText(
            frame, "Go check the printer outside", (100, 200), _FONT, 1, (0, 0, 0)
        )
        cv2.putText(
            frame, "Go check the printer outside", (101, 201), _FONT, 1, (255, 255, 255)
        )

        if self._ellapsed > 10:
            return (frame, WelcomeState())
        return (frame, self)


def resize_to_fit(im, desired: Vec2):
    scale_x = float(desired.x) / float(im.shape[1])
    scale_y = float(desired.y) / float(im.shape[0])
    scale = min(scale_x, scale_y)
    return cv2.resize(
        im, (math.ceil(scale * im.shape[1]), math.ceil(scale * im.shape[0]))
    )
