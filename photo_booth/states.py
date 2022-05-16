from typing import Any, Tuple
import abc
import os
import math
import subprocess

import cv2
import numpy
from PIL import Image
from photo_booth import output
import structlog

from . import input
from .join_images import FULL_SIZE, join_images, Vec2

_LOGGER = structlog.get_logger(__name__)
# _FONT = cv2.freetype.createFreeType2()
# _FONT.loadFontData(fontFileName="/usr/share/fonts/truetype/quicksand/Quicksand-Light.ttf", id=0)
_FONT = cv2.FONT_HERSHEY_COMPLEX

WELCOME_SCREEN = os.path.join(os.path.dirname(__file__), "welcome_screen.png")
END_SCREEN_UNDERLAY = os.path.join(os.path.dirname(__file__), "end_screen_underlay.png")
PRINTING_SCREEN = os.path.join(os.path.dirname(__file__), "printing_screen.png")


class State(abc.ABC):
    @abc.abstractmethod
    def tick(self, frame, delta_time_s: float, key: int = None) -> Tuple[Any, "State"]:
        ...


class WelcomeState(State):
    def __init__(self) -> None:
        image = Image.open(WELCOME_SCREEN)
        pixels = numpy.array(image.convert("RGB"))
        self._image = pixels[:, :, ::-1].copy()

    def tick(self, frame, delta_time_s: float, key: int = None) -> Tuple[Any, "State"]:

        input.set_blue_button_light(on=True)
        input.set_red_button_light(on=False)

        if key == 32 or input.get_blue_button():  # space
            input.set_blue_button_light(on=False)
            path = output.create_output_directory()
            return (frame, CountdownState(path))
        return (self._image, self)


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
        self._image_file = f"{out_dir}/final.png"

        joined_image = join_images(
            f"{out_dir}/photo_1.png",
            f"{out_dir}/photo_2.png",
            f"{out_dir}/photo_3.png",
            f"{out_dir}/photo_4.png",
        )
        pixels = numpy.array(joined_image.convert("RGB"))
        cv2.imwrite(self._image_file, pixels[:, :, ::-1])

        underlay_image = Image.open(END_SCREEN_UNDERLAY).convert("RGB")
        height = 720
        scale_factor = height / FULL_SIZE.y
        width = math.ceil(underlay_image.size[0] * scale_factor)
        offset_x = math.ceil((960.0 - width) * 0.5)
        joined_image = joined_image.resize((width, height))
        underlay_image.paste(joined_image.convert("RGB"), (offset_x, 0))
        pixels = numpy.array(underlay_image)
        self._joined_image = pixels[:, :, ::-1].copy()

    def tick(self, frame, delta_time_s: float, key: int = None) -> Tuple[Any, "State"]:

        input.set_blue_button_light(on=True)
        input.set_red_button_light(on=True)

        if key == 121 or input.get_blue_button():  # y
            return frame, PrintingMessageState(self._image_file)

        elif key == 110 or input.get_red_button():  # n
            _LOGGER.info("Print rejected")
            return self._joined_image, WelcomeState()

        else:
            return self._joined_image, self


class PrintingMessageState(State):
    def __init__(self, image_file) -> None:

        image = Image.open(PRINTING_SCREEN)
        pixels = numpy.array(image.convert("RGB"))

        self._printer_name = "selphy"
        self._image = pixels[:, :, ::-1].copy()
        self._ellapsed = 0.0
        self._image_file = image_file
        self._pdf_file = "/tmp/final.pdf"

        _LOGGER.info("converting image to pdf...")
        self._submitted = False
        self._cmd = subprocess.Popen(["convert", self._image_file, self._pdf_file])

    def tick(self, frame, delta_time_s: float, key: int = None) -> Tuple[Any, "State"]:

        self._ellapsed += delta_time_s

        input.set_blue_button_light(on=False)
        input.set_red_button_light(on=False)

        if self._cmd is not None:

            return_code = self._cmd.poll()
            if return_code is None:
                return (self._image, self)

            self._cmd = None
            if return_code != 0:
                _LOGGER.error("Subprocess failed during printing")
                return (self._image, self)

            if not self._submitted:
                _LOGGER.info("printing image...")
                self._cmd = subprocess.Popen(
                    ["lp", "-d", self._printer_name, self._pdf_file]
                )
                self._submitted = True

        elif self._ellapsed > 10:
            return (self._image, WelcomeState())

        return (self._image, self)


def resize_to_fit(im, desired: Vec2):
    scale_x = float(desired.x) / float(im.shape[1])
    scale_y = float(desired.y) / float(im.shape[0])
    scale = min(scale_x, scale_y)
    return cv2.resize(
        im, (math.ceil(scale * im.shape[1]), math.ceil(scale * im.shape[0]))
    )
