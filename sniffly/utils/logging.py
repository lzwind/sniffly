"""Logging configuration for Sniffly."""

import logging
import sys

from ..config import Config


def setup_logging(log_level: str | None = None) -> None:
    """Configure logging for the application.

    Args:
        log_level: Override log level. If None, uses config value.
    """
    if log_level is None:
        config = Config()
        log_level = config.get("log_level", "INFO")

    # Convert to uppercase to handle any case variations
    log_level = log_level.upper()

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )

    # Silence noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # Log the configuration
    logger = logging.getLogger(__name__)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
