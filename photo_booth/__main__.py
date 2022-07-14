#!/usr/bin/env python3
from datetime import datetime
import argparse
import time

import structlog
import cv2
import numpy as np

from .join_images import Vec2, join_images
from .config import init_logging, WINDOW_NAME
from . import states, input

LOOP_INTERVAL_MS = 16
LOOP_INTERVAL_S = LOOP_INTERVAL_MS / 1000
BUF = np.zeros((1080, 1920, 3), np.uint8)
_LOGGER = structlog.get_logger(__name__)


def parse_args():

    parser = argparse.ArgumentParser("photo_booth")
    parser.add_argument("--button-test", action="store_true")
    parser.add_argument("--no-fullscreen", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    init_logging()

    _LOGGER.info("starting up...")

    input.initialize()
    if args.button_test:
        state = states.TestState()
    else:
        state = states.WelcomeState()

    _LOGGER.info("establishing window...")
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    if not args.no_fullscreen:
        cv2.setWindowProperty(
            WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN
        )

    _LOGGER.info("opening video stream...")
    vc = cv2.VideoCapture(0)
    rval, frame = False, []
    if vc.isOpened():
        vc.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
        vc.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        rval, frame = vc.read()

    _LOGGER.info("starting main loop...")
    key = None
    last_frame = datetime.now().timestamp()
    while rval:

        now = datetime.now().timestamp()
        delta_s = now - last_frame
        last_frame = now

        input.tick()
        frame = cv2.flip(frame, 1)
        frame, state = state.tick(frame, delta_s, key)

        frame = states.resize_to_fit(frame, Vec2(1920, 1080))
        
        xtra = (1920 - 1440) // 2
        BUF[0:1080, 240:1680] = frame

        cv2.imshow(WINDOW_NAME, BUF)
        key = cv2.waitKey(int(max(1, (LOOP_INTERVAL_S - delta_s) * 1000)))
        if key == 27:  # exit on ESC
            break
        rval, frame = vc.read()

    vc.release()
    cv2.destroyAllWindows()
