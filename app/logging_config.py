"""Logging configuration for the application."""

import logging
import sys

LOGGER_NAME = "ai_product_lab"


def configure_logging() -> logging.Logger:
    """Configure and return the application logger."""
    logger = logging.getLogger(LOGGER_NAME)

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        (
            "%(asctime)s "
            "level=%(levelname)s "
            "logger=%(name)s "
            "%(message)s"
        )
    )

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False

    return logger