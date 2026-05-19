import pytest
from unittest.mock import patch, MagicMock
import argparse

from src.cli import ExecutionMode, ExecutionContext, CLI


class TestExecutionMode:
    def test_execution_mode_batch_exists(self):
        assert hasattr(ExecutionMode, 'BATCH')
        assert ExecutionMode.BATCH.value == "batch"

    def test_execution_mode_interactive_exists(self):
        assert hasattr(ExecutionMode, 'INTERACTIVE')
        assert ExecutionMode.INTERACTIVE.value == "interactive"


class TestExecutionContext:
    def test_execution_context_has_required_fields(self):
        ctx = ExecutionContext(
            mode=ExecutionMode.BATCH,
            directors=[],
            output_dir=None
        )
        assert ctx.mode == ExecutionMode.BATCH
        assert ctx.directors == []

    def test_execution_context_dataclass(self):
        ctx = ExecutionContext(
            mode=ExecutionMode.INTERACTIVE,
            directors=[{"first": "John", "last": "Doe", "smsf": "Test"}],
            output_dir=None,
            verbose=True
        )
        assert ctx.mode == ExecutionMode.INTERACTIVE
        assert len(ctx.directors) == 1
        assert ctx.verbose is True


class TestCLIResolve:
    def test_resolve_batch_mode(self):
        with patch.object(CLI, '_stdin_available', return_value=True):
            with patch('builtins.open', MagicMock()):
                with patch('json.load', return_value=[{"first": "John", "last": "Doe", "smsf": "Test"}]):
                    ctx = CLI.resolve(['--batch', 'test.json'])
                    assert ctx.mode == ExecutionMode.BATCH

    def test_resolve_interactive_requires_tty(self):
        with patch.object(CLI, '_stdin_available', return_value=False):
            with pytest.raises(SystemExit):
                CLI.resolve([])