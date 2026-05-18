import pytest
from unittest.mock import patch, MagicMock

from src.cli import stdin_available, require_stdin, ExecutionContext, ExecutionMode
from src.exceptions import StdinUnavailableError


class TestStdinAvailable:
    def test_stdin_available_returns_true_when_isatty_true(self):
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = True
            assert stdin_available() is True

    def test_stdin_available_returns_false_when_stdin_none(self):
        with patch("sys.stdin", None):
            assert stdin_available() is False

    def test_stdin_available_returns_false_when_isatty_false(self):
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = False
            assert stdin_available() is False

    def test_stdin_available_returns_false_when_isatty_missing(self):
        mock_stdin = MagicMock(spec=[])
        assert not hasattr(mock_stdin, "isatty")
        with patch("sys.stdin", mock_stdin):
            assert stdin_available() is False


class TestRequireStdin:
    def test_require_stdin_raises_when_unavailable(self):
        with patch("sys.stdin", None):
            with pytest.raises(StdinUnavailableError) as exc_info:
                require_stdin("test operation")
            assert "test operation" in str(exc_info.value)

    def test_require_stdin_raises_when_not_tty(self):
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = False
            with pytest.raises(StdinUnavailableError):
                require_stdin("prompt")

    def test_require_stdin_silent_when_available(self):
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = True
            require_stdin("test")

    def test_require_stdin_message_contains_operation(self):
        with patch("sys.stdin", None):
            try:
                require_stdin("continue prompt")
            except RuntimeError as e:
                assert "continue prompt" in str(e)
                assert "--interactive" in str(e)