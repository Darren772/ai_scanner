"""
Simple rotating file logger for debugging. Writes to renscan.log.
This is NOT the history log — it's for app errors and events only.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

_LOG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "renscan.log"
)

_logger = logging.getLogger("renscan")
_logger.setLevel(logging.DEBUG)

if not _logger.handlers:
    _handler = RotatingFileHandler(
        _LOG_PATH, maxBytes=1_000_000, backupCount=2, encoding="utf-8"
    )
    _handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )
    _logger.addHandler(_handler)


def info(msg: str) -> None:
    _logger.info(msg)


def error(msg: str) -> None:
    _logger.error(msg)
