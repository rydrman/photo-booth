#!/usr/bin/env python3
from datetime import datetime

import structlog
import cv2

from .join_images import Vec2, join_images
from .config import init_logging, WINDOW_NAME
from . import states

LOOP_INTERVAL_MS = 16
LOOP_INTERVAL_S = LOOP_INTERVAL_MS / 1000
_LOGGER = structlog.get_logger(__name__)

if __name__ == "__main__":
    init_logging()

    state = states.WelcomeState()

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    vc = cv2.VideoCapture(0)
    rval, frame = False, []
    if vc.isOpened():
        rval, frame = vc.read()
    
    key = None
    last_frame = datetime.now().timestamp()
    while rval:
        now = datetime.now().timestamp()
        delta_s = now - last_frame
        last_frame = now

        frame = cv2.flip(frame, 1)
        frame, state = state.tick(frame, delta_s, key)

        frame = states.resize_to_fit(frame, Vec2(1920, 1080))

        cv2.imshow(WINDOW_NAME, frame)
        key = cv2.waitKey(int(max(1, (LOOP_INTERVAL_S - delta_s) * 1000)))
        if key == 27: # exit on ESC
            break
        rval, frame = vc.read()

    vc.release()
    cv2.destroyAllWindows()