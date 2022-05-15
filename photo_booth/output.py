import os
from datetime import datetime

_OUTPUT_ROOT = "/media/pi/SMALL/images"


def create_output_directory() -> str:

    now = datetime.now()
    name = now.isoformat()
    dir_name = os.path.join(_OUTPUT_ROOT, name)
    os.makedirs(dir_name)
    return dir_name
