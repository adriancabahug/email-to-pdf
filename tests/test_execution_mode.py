import pytest
from unittest.mock import patch, MagicMock
import argparse

from src.cli import ExecutionMode, ExecutionContext, resolve_mode


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
            stdin_allowed=False,
            interactive_allowed=False
        )
        assert ctx.mode == ExecutionMode.BATCH
        assert ctx.stdin_allowed is False
        assert ctx.interactive_allowed is False

    def test_execution_context_dataclass(self):
        ctx = ExecutionContext(
            mode=ExecutionMode.INTERACTIVE,
            stdin_allowed=True,
            interactive_allowed=True
        )
        assert ctx.mode == ExecutionMode.INTERACTIVE
        assert ctx.stdin_allowed is True
        assert ctx.interactive_allowed is True


class TestResolveMode:
    def test_batch_flag_returns_batch_mode(self):
        args = argparse.Namespace(interactive=False, console=False, batch=True)
        ctx = resolve_mode(args, stdin_ok=False)
        assert ctx.mode == ExecutionMode.BATCH
        assert ctx.stdin_allowed is False
        assert ctx.interactive_allowed is False

    def test_interactive_flag_returns_interactive_mode(self):
        args = argparse.Namespace(interactive=True, console=False, batch=False)
        ctx = resolve_mode(args, stdin_ok=False)
        assert ctx.mode == ExecutionMode.INTERACTIVE
        assert ctx.stdin_allowed is True
        assert ctx.interactive_allowed is True

    def test_console_flag_returns_interactive_mode(self):
        args = argparse.Namespace(interactive=False, console=True, batch=False)
        ctx = resolve_mode(args, stdin_ok=False)
        assert ctx.mode == ExecutionMode.INTERACTIVE
        assert ctx.stdin_allowed is True
        assert ctx.interactive_allowed is True

    def test_no_flags_no_stdin_falls_back_to_batch(self):
        args = argparse.Namespace(interactive=False, console=False, batch=False)
        ctx = resolve_mode(args, stdin_ok=False)
        assert ctx.mode == ExecutionMode.BATCH

    def test_no_flags_with_stdin_falls_back_to_interactive(self):
        args = argparse.Namespace(interactive=False, console=False, batch=False)
        ctx = resolve_mode(args, stdin_ok=True)
        assert ctx.mode == ExecutionMode.INTERACTIVE

    def test_interactive_flag_with_stdin_available(self):
        args = argparse.Namespace(interactive=True, console=False, batch=False)
        ctx = resolve_mode(args, stdin_ok=True)
        assert ctx.mode == ExecutionMode.INTERACTIVE
        assert ctx.stdin_allowed is True
        assert ctx.interactive_allowed is True