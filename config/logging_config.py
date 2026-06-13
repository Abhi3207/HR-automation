"""
Centralized logging configuration for the HR Multi-Agent System.

Usage:
    from config.logging_config import get_logger
    logger = get_logger(__name__)
"""

import logging
import os
import sys

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Validate the log level
_valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
if LOG_LEVEL not in _valid_levels:
    LOG_LEVEL = "INFO"


def setup_logging() -> None:
    """Configure the root logger with a console handler."""
    root = logging.getLogger()

    # Avoid adding duplicate handlers on repeated calls
    if root.handlers:
        return

    root.setLevel(getattr(logging, LOG_LEVEL))

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(getattr(logging, LOG_LEVEL))

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    console.setFormatter(formatter)
    root.addHandler(console)

    # Quiet down noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a named logger, ensuring logging is configured first."""
    setup_logging()
    return logging.getLogger(name)
