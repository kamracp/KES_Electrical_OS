"""
Central logging configuration for KES Electrical OS.
"""

import logging
import sys
from types import FrameType

from loguru import logger

from app.core.config import Settings, get_settings


class InterceptHandler(logging.Handler):
    """Route standard logging through Loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame: FrameType | None = logging.currentframe()
        depth = 2

        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(
            depth=depth,
            exception=record.exc_info,
        ).log(level, record.getMessage())


def configure_logging(settings: Settings | None = None) -> None:
    """Configure application logging."""

    active_settings = settings or get_settings()

    serialize_logs = active_settings.ENVIRONMENT == "production"

    logger.remove()

    logger.add(
        sys.stderr,
        level=active_settings.LOG_LEVEL,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        colorize=sys.stderr.isatty() and not serialize_logs,
        serialize=serialize_logs,
        backtrace=active_settings.DEBUG,
        diagnose=False,
        enqueue=True,
    )

    logging.basicConfig(
        handlers=[InterceptHandler()],
        level=logging.NOTSET,
        force=True,
    )

    for name in (
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
        "sqlalchemy",
    ):
        log = logging.getLogger(name)
        log.handlers.clear()
        log.propagate = True


__all__ = [
    "InterceptHandler",
    "configure_logging",
]