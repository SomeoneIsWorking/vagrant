"""Project logging configuration for player-facing Python entry points."""

from __future__ import annotations

import logging

DEFAULT_LEVEL = logging.INFO
LOGGER_NAME = "vagrant"


def configure_logging(level: int = DEFAULT_LEVEL) -> logging.Logger:
    """Configure and return the project logger without reading process-global settings."""

    logger = logging.getLogger(LOGGER_NAME)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("[%(name)s] %(levelname)s: %(message)s"))
        logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger
