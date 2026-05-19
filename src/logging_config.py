"""Centralized logging configuration with structured output and rotation."""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

LOG_DIR = Path("./logs")
LOG_FILE = LOG_DIR / "application.log"

DEFAULT_MAX_BYTES = 5 * 1024 * 1024
DEFAULT_BACKUP_COUNT = 3


def setup_logging(
    level: Optional[str] = None,
    log_dir: Optional[Path] = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
    verbose_console: bool = False,
) -> logging.Logger:
    """Configure logging with console and rotating file handlers.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL). Defaults to INFO.
        log_dir: Directory for log files. Defaults to ./logs
        max_bytes: Max size per log file before rotation.
        backup_count: Number of backup files to keep.
        verbose_console: Enable verbose (DEBUG) console output.

    Returns:
        Root logger with configured handlers.
    """
    log_level = _parse_level(level)
    console_level = logging.DEBUG if verbose_console else logging.INFO

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    if root_logger.handlers:
        return root_logger

    log_path = log_dir or LOG_DIR
    log_path.mkdir(parents=True, exist_ok=True)
    log_file = log_path / "application.log"

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    return root_logger


def _parse_level(level: Optional[str]) -> int:
    """Parse log level string to logging constant."""
    if not level:
        return logging.INFO
    level_upper = level.upper()
    if level_upper == "VERBOSE":
        return logging.DEBUG
    if hasattr(logging, level_upper):
        return getattr(logging, level_upper)
    return logging.INFO


def get_logger(name: str) -> logging.Logger:
    """Get a logger for the specified module name."""
    return logging.getLogger(name)


def log_exception(logger: logging.Logger, msg: str, exc: Exception) -> None:
    """Log an exception with full traceback at ERROR level."""
    logger.exception("%s: %s", msg, exc)


def is_frozen() -> bool:
    """Check if running as a PyInstaller frozen executable."""
    return getattr(sys, "frozen", False)


def get_log_dir() -> Path:
    """Get the directory where log files should be stored."""
    if is_frozen():
        exe_dir = Path(sys.executable).parent
        log_path = exe_dir / "logs"
        try:
            log_path.mkdir(parents=True, exist_ok=True)
        except OSError:
            return LOG_DIR
        return log_path
    return LOG_DIR


def ensure_log_dir() -> Path:
    """Ensure log directory exists and return its path."""
    log_dir = get_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir