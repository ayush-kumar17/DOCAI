"""
Structured logger using structlog.
Usage:
    from utils.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Processing document", doc_id=doc_id, file_type=file_type)
"""

import logging
import sys
import structlog
from config import settings


def setup_logging():
    """Configure structlog for the application."""

    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
            structlog.processors.StackInfoRenderer(),
            structlog.dev.ConsoleRenderer()
            if settings.DEBUG
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str):
    """Get a logger for a module. Pass __name__ always."""
    return structlog.get_logger(name)


# Run setup on import
setup_logging()