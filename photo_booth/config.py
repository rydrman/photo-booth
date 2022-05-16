import sys
import logging

import structlog

WINDOW_NAME = "photo_booth"


def init_logging():
    logging.basicConfig(stream=sys.stderr, format="%(message)s", level=logging.CRITICAL)
    logging.getLogger("__main__").setLevel(logging.DEBUG)
    logging.getLogger("photo_booth").setLevel(logging.DEBUG)
    structlog.configure(
        processors=[
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M.%S"),
            structlog.processors.StackInfoRenderer(),
            structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
