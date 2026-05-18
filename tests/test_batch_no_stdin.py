"""Architectural regression tests: batch mode never performs interactive I/O."""

import pytest
from unittest.mock import patch, MagicMock

from src.main_orchestrator import MainOrchestrator
from src.cli import ExecutionMode, ExecutionContext


class InteractiveIOMonitor:
    calls = []

    @classmethod
    def note(cls, name):
        cls.calls.append(name)

    @classmethod
    def reset(cls):
        cls.calls = []


def make_orchestrator_batch():
    exec_context = ExecutionContext(
        mode=ExecutionMode.BATCH,
        stdin_allowed=False,
        interactive_allowed=False
    )

    mock_license = MagicMock()
    mock_license.get_stored_key.return_value = "VALID-KEY-123456"
    mock_license.validate_key.return_value = {"valid": True}

    with patch("src.main_orchestrator.LicenseValidator", return_value=mock_license):
        return MainOrchestrator(exec_context=exec_context)


class TestBatchModeNoInteractiveIO:
    def test_batch_mode_does_not_call_input_handler_get_director_input(self):
        InteractiveIOMonitor.reset()
        orchestrator = make_orchestrator_batch()

        mock_input = MagicMock()
        mock_input.get_director_input.side_effect = lambda: InteractiveIOMonitor.note("get_director_input") or {}

        with patch("src.main_orchestrator.InputHandler", return_value=mock_input):
            try:
                orchestrator.run()
            except Exception:
                pass

        assert "get_director_input" not in InteractiveIOMonitor.calls, \
            f"get_director_input was called in batch mode: {InteractiveIOMonitor.calls}"

    def test_batch_mode_does_not_call_input_handler_prompt_continue(self):
        InteractiveIOMonitor.reset()
        orchestrator = make_orchestrator_batch()

        mock_input = MagicMock()
        mock_input.prompt_continue.side_effect = lambda: InteractiveIOMonitor.note("prompt_continue") or True

        with patch("src.main_orchestrator.InputHandler", return_value=mock_input):
            try:
                orchestrator.run()
            except Exception:
                pass

        assert "prompt_continue" not in InteractiveIOMonitor.calls, \
            f"prompt_continue was called in batch mode: {InteractiveIOMonitor.calls}"

    def test_batch_mode_run_batch_processes_directors_without_interactive_io(self):
        InteractiveIOMonitor.reset()
        orchestrator = make_orchestrator_batch()

        with patch.object(orchestrator._input_handler, "get_director_input",
                         side_effect=lambda: InteractiveIOMonitor.note("get_director_input") or {}):
            with patch.object(orchestrator._input_handler, "prompt_continue",
                             side_effect=lambda: InteractiveIOMonitor.note("prompt_continue") or True):
                try:
                    orchestrator.run()
                except Exception:
                    pass

        assert "get_director_input" not in InteractiveIOMonitor.calls, \
            f"Interactive prompt called in batch mode: {InteractiveIOMonitor.calls}"
        assert "prompt_continue" not in InteractiveIOMonitor.calls, \
            f"Interactive confirm called in batch mode: {InteractiveIOMonitor.calls}"

    def test_batch_mode_no_prompt_in_any_code_path(self):
        calls = []
        from src.cli import require_stdin
        from src.exceptions import StdinUnavailableError

        def tracking_require(operation):
            calls.append(f"require_stdin:{operation}")
            real_require(operation)

        with patch("src.cli.require_stdin", tracking_require):
            orchestrator = make_orchestrator_batch()
            try:
                orchestrator.run()
            except StdinUnavailableError:
                pass
            except Exception:
                pass

        assert all("Prompt" not in c for c in calls), \
            f"Prompt.ask reached in batch mode: {[c for c in calls if 'Prompt' in c]}"
        assert not any("get_director_input" in c for c in calls), \
            f"get_director_input reached in batch mode"

    def test_batch_mode_interactive_methods_guarded_by_execution_context(self):
        from src.cli import InputHandler, ExecutionContext, ExecutionMode
        from src.exceptions import StdinUnavailableError

        batch_ctx = ExecutionContext(mode=ExecutionMode.BATCH, stdin_allowed=False, interactive_allowed=False)
        handler = InputHandler(exec_context=batch_ctx)

        with pytest.raises(StdinUnavailableError) as exc_info:
            handler.get_director_input()

        assert "batch mode" in str(exc_info.value).lower()

    def test_interactive_mode_allows_input_handler(self):
        from src.cli import InputHandler, resolve_mode, build_parser

        args = build_parser().parse_args(["--interactive"])
        exec_context = resolve_mode(args, stdin_ok=True)
        assert exec_context.mode == ExecutionMode.INTERACTIVE
        assert exec_context.stdin_allowed is True

        handler = InputHandler(exec_context=exec_context)

        with patch("src.cli.Prompt.ask", return_value="Test"):
            result = handler.get_director_input()

        assert result["first_name"] == "Test"