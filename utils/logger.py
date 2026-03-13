"""
utils/logger.py
---------------
Consistent, colour-aware logging for the whole project.
"""

import logging
import sys


_FMT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE = "%H:%M:%S"


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Return (or create) a named logger with a StreamHandler."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(_FMT, _DATE))
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger
