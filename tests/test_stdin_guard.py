import pytest
from unittest.mock import patch, MagicMock

from src.cli import CLI, ExecutionContext, ExecutionMode


class TestStdinGuard:
    def test_stdin_available_returns_true_when_isatty_true(self):
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = True
            assert CLI._stdin_available() is True

    def test_stdin_available_returns_false_when_stdin_none(self):
        mock_stdin = MagicMock()
        mock_stdin.isatty.side_effect = AttributeError()
        with patch("sys.stdin", mock_stdin):
            assert CLI._stdin_available() is False

    def test_stdin_available_returns_false_when_isatty_false(self):
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = False
            assert CLI._stdin_available() is False

    def test_stdin_available_returns_false_when_isatty_missing(self):
        mock_stdin = MagicMock(spec=[])
        assert not hasattr(mock_stdin, "isatty")
        with patch("sys.stdin", mock_stdin):
            assert CLI._stdin_available() is False

    def test_require_stdin_raises_when_unavailable(self):
        mock_stdin = MagicMock()
        mock_stdin.isatty.side_effect = AttributeError()
        with patch("sys.stdin", mock_stdin):
            with pytest.raises(RuntimeError) as exc_info:
                CLI.require_stdin("test operation")
            assert "test operation" in str(exc_info.value)

    def test_require_stdin_raises_when_not_tty(self):
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = False
            with pytest.raises(RuntimeError):
                CLI.require_stdin("prompt")

    def test_require_stdin_silent_when_available(self):
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = True
            CLI.require_stdin("test")

    def test_require_stdin_message_contains_operation(self):
        mock_stdin = MagicMock()
        mock_stdin.isatty.side_effect = AttributeError()
        with patch("sys.stdin", mock_stdin):
            with pytest.raises(RuntimeError) as exc_info:
                CLI.require_stdin("continue prompt")
            assert "continue prompt" in str(exc_info.value)