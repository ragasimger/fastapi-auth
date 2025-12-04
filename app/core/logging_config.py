import logging
import os
import sys
from functools import lru_cache
from pathlib import Path

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DIR = "logs"

Path(LOG_DIR).mkdir(exist_ok=True)


class NoTracebackConsoleHandler(logging.StreamHandler):
    """Console handler that suppresses traceback output"""

    def emit(self, record):
        exc_info = record.exc_info
        record.exc_info = None
        super().emit(record)
        record.exc_info = exc_info


class ColoredFormatter(logging.Formatter):
    """Colored log formatter for terminal output"""

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def format(self, record):
        levelname = record.levelname  # Color the level name
        if levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[levelname]}{self.BOLD}{levelname}{self.RESET}"
            )

        formatted = super().format(record)  # Format the message

        record.levelname = levelname  # Restore original levelname

        return formatted


class LevelFilter(logging.Filter):
    def __init__(self, level: int):
        super().__init__()
        self.level = level

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno == self.level


@lru_cache
def get_logging_configs() -> dict:
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {"format": LOG_FORMAT},
            "colored": {
                "()": ColoredFormatter,
                "format": LOG_FORMAT,
            },
        },
        "handlers": {
            "access_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "standard",
                "filename": os.path.join(LOG_DIR, "access.log"),
                "maxBytes": 10485760,
                "backupCount": 5,
            },
            # Info log
            "info_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "standard",
                "filename": os.path.join(LOG_DIR, "info.log"),
                "maxBytes": 10485760,
                "backupCount": 5,
                "filters": [LevelFilter(logging.INFO)],
            },
            # Warning log
            "warning_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "WARNING",
                "formatter": "standard",
                "filename": os.path.join(LOG_DIR, "warning.log"),
                "maxBytes": 10485760,
                "backupCount": 5,
                "filters": [LevelFilter(logging.WARNING)],
            },
            # Error log (with stack traces)
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "standard",
                "filename": os.path.join(LOG_DIR, "error.log"),
                "maxBytes": 10485760,
                "backupCount": 5,
                "filters": [LevelFilter(logging.ERROR)],
            },
            # Critical log
            "critical_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "CRITICAL",
                "formatter": "standard",
                "filename": os.path.join(LOG_DIR, "critical.log"),
                "maxBytes": 10485760,
                "backupCount": 5,
                "filters": [LevelFilter(logging.CRITICAL)],
            },
            # Console logging
            "console": {
                "()": NoTracebackConsoleHandler,
                "level": LOG_LEVEL,
                "formatter": "colored",
                "stream": sys.stdout,
            },
        },
        "loggers": {
            "": {
                "handlers": [
                    "console",
                    "access_file",
                    "info_file",
                    "warning_file",
                    "error_file",
                    "critical_file",
                ],
                "level": LOG_LEVEL,
                "propagate": True,
            },
        },
    }
