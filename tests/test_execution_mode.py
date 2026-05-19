import pytest
from unittest.mock import patch, MagicMock
import argparse

from src.cli import ExecutionMode, ExecutionContext, CLI


class TestExecutionMode:
    def test_execution_mode_batch_exists(self):
        assert hasattr(ExecutionMode, 'BATCH')
        assert ExecutionMode.BATCH.name == "BATCH"

    def test_execution_mode_interactive_exists(self):
        assert hasattr(ExecutionMode, 'INTERACTIVE')
        assert ExecutionMode.INTERACTIVE.name == "INTERACTIVE"


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
    def test_resolve_batch_mode(self, tmp_path):
        batch_file = tmp_path / "batch.json"
        batch_file.write_text('[{"first": "John", "last": "Doe", "smsf": "Test"}]')
        with patch.object(CLI, '_stdin_available', return_value=True):
            ctx = CLI.resolve(['--batch', str(batch_file)])
            assert ctx.mode == ExecutionMode.BATCH

    def test_resolve_interactive_requires_tty(self):
        with patch.object(CLI, '_stdin_available', return_value=False):
            with pytest.raises(SystemExit):
                CLI.resolve([])