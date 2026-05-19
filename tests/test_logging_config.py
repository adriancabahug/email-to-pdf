"""
Tests for logging configuration.
"""

import logging
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.logging_config import (
    setup_logging,
    get_logger,
    log_exception,
    is_frozen,
    get_log_dir,
    ensure_log_dir,
    DEFAULT_MAX_BYTES,
    DEFAULT_BACKUP_COUNT,
)


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_setup_creates_handlers(self, caplog):
        with patch("src.logging_config.ensure_log_dir") as mock_ensure:
            mock_ensure.return_value = Path(".")

            root = setup_logging(level="info", verbose_console=False)

            assert root.level == logging.DEBUG
            assert len(root.handlers) >= 2

    def test_setup_with_different_levels(self):
        with patch("src.logging_config.ensure_log_dir") as mock_ensure:
            mock_ensure.return_value = Path(".")

            root = setup_logging(level="error")
            assert root is not None

    def test_setup_creates_formatter(self):
        with patch("src.logging_config.ensure_log_dir") as mock_ensure:
            mock_ensure.return_value = Path(".")

            root = setup_logging()

            for handler in root.handlers:
                if isinstance(handler, logging.FileHandler):
                    assert handler.formatter is not None


class TestGetLogger:
    """Tests for get_logger function."""

    def test_get_logger_returns_logger(self):
        logger = get_logger("test.module")
        assert logger.name == "test.module"
        assert isinstance(logger, logging.Logger)


class TestLogException:
    """Tests for log_exception function."""

    def test_log_exception_uses_exception_level(self):
        logger = MagicMock()
        exc = ValueError("test error")

        log_exception(logger, "Test message", exc)

        logger.exception.assert_called_once()
        call_args = logger.exception.call_args
        call_str = str(call_args)
        assert "Test message" in call_str
        assert "test error" in call_str


class TestIsFrozen:
    """Tests for is_frozen detection."""

    def test_is_frozen_not_frozen(self):
        original = getattr(sys, 'frozen', None)
        try:
            sys.frozen = False
            assert is_frozen() is False
        finally:
            if original is not None:
                sys.frozen = original
            elif hasattr(sys, 'frozen'):
                delattr(sys, 'frozen')

    def test_is_frozen_frozen(self):
        original = getattr(sys, 'frozen', None)
        try:
            sys.frozen = True
            assert is_frozen() is True
        finally:
            if original is not None:
                sys.frozen = original
            elif hasattr(sys, 'frozen'):
                delattr(sys, 'frozen')


class TestLogDir:
    """Tests for log directory functions."""

    def test_get_log_dir_default(self):
        with patch("src.logging_config.is_frozen", return_value=False):
            log_dir = get_log_dir()
            assert log_dir == Path("./logs")

    def test_ensure_log_dir_creates_directory(self, tmp_path):
        with patch("src.logging_config.get_log_dir", return_value=tmp_path / "logs"):
            result = ensure_log_dir()
            assert result.exists()
            assert result.is_dir()