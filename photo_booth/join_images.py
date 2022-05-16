from typing import NamedTuple
from math import ceil
import os

import structlog
from PIL import Image
import numpy


class Vec2(NamedTuple):
    x: int
    y: int


MASK_FILE = os.path.join(os.path.dirname(__file__), "photo_mask.png")

FULL_SIZE = Vec2(1200, 1800)
DESIRED_SIZE = Vec2(540, 375)
OUTER_MARGIN = 29
INNER_GAP = 15
POSITIONS = (
    Vec2(OUTER_MARGIN, OUTER_MARGIN),
    Vec2(OUTER_MARGIN, OUTER_MARGIN + DESIRED_SIZE.y + INNER_GAP),
    Vec2(OUTER_MARGIN, OUTER_MARGIN + (DESIRED_SIZE.y + INNER_GAP) * 2),
    Vec2(OUTER_MARGIN, OUTER_MARGIN + (DESIRED_SIZE.y + INNER_GAP) * 3),
)

POSITION_RIGHT_X = FULL_SIZE.x - DESIRED_SIZE.x - OUTER_MARGIN
POSITIONS_RIGHT = tuple(Vec2(POSITION_RIGHT_X, pos.y) for pos in POSITIONS)

_LOGGER = structlog.get_logger(__name__)


def resize_to_fill(im: Image) -> Image:
    scale_x = float(DESIRED_SIZE.x + 5) / float(im.size[0])
    scale_y = float(DESIRED_SIZE.y + 5) / float(im.size[1])
    scale = max(scale_x, scale_y)
    return im.resize((ceil(scale * im.size[0]), ceil(scale * im.size[1])))


def join_images(file1, file2, file3, file4) -> Image:
    new_image = Image.new("RGBA", FULL_SIZE)
    overlay = Image.open(MASK_FILE)
    images = (
        resize_to_fill(Image.open(file1)),
        resize_to_fill(Image.open(file2)),
        resize_to_fill(Image.open(file3)),
        resize_to_fill(Image.open(file4)),
    )
    for image, left, right in zip(images, POSITIONS, POSITIONS_RIGHT):
        overhang = Vec2(
            (image.size[0] - DESIRED_SIZE.x),
            (image.size[1] - DESIRED_SIZE.y),
        )
        left_pos_centered = Vec2(
            int(left.x - overhang.x * 0.5),
            int(left.y - overhang.y * 0.5),
        )
        right_pos_centered = Vec2(
            int(right.x - overhang.x * 0.5), int(right.y - overhang.y * 0.5)
        )
        new_image.paste(image, left_pos_centered)
        new_image.paste(image, right_pos_centered)
    new_image.alpha_composite(overlay, (0, 0))
    return new_image
