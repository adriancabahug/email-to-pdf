"""
Tests for refactored MainOrchestrator using Dependencies injection.
No @patch decorators needed — we pass fake dependencies directly.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.dependencies import Dependencies
from src.cli import CLI, ExecutionContext, ExecutionMode
from src.main_orchestrator import DirectorContext, MainOrchestrator, OutlookUnavailableError


@pytest.fixture
def fake_deps(tmp_path: Path) -> Dependencies:
    """Fully wired fake dependency graph."""
    pdf = MagicMock()
    pdf.start.return_value = True

    session_mgr = MagicMock()
    session_mgr.discover_email_from_name.return_value = None
    session_mgr.connect.return_value = True
    session_mgr.is_connected.return_value = True

    mock_email_searcher = MagicMock()
    mock_email_searcher.search.return_value = []

    processed_store = MagicMock()
    processed_store.is_processed.return_value = False

    deps = Dependencies(
        session_manager=session_mgr,
        email_searcher=mock_email_searcher,
        email_formatter=MagicMock(),
        pdf_generator=pdf,
        file_manager=MagicMock(),
        config_manager=MagicMock(),
        processed_store=processed_store,
        progress_manager=MagicMock(),
        license_validator=MagicMock(),
    )
    return deps


def _setup_session(orch: MainOrchestrator, deps: Dependencies) -> None:
    """Set up session and searcher for direct _process_director calls."""
    orch._session = deps.session_manager
    orch._searcher = deps.email_searcher


@pytest.fixture
def batch_context(tmp_path: Path) -> ExecutionContext:
    return ExecutionContext(
        mode=ExecutionMode.BATCH,
        directors=[
            {"first": "Alice", "last": "Smith", "smsf": "SMSF001"},
            {"first": "Bob", "last": "Jones", "smsf": "SMSF002"},
        ],
        output_dir=tmp_path,
        verbose=False,
    )


class TestRunLifecycle:
    def test_run_validates_license(self, batch_context: ExecutionContext, fake_deps: Dependencies, tmp_path: Path):
        fake_deps.license_validator.prompt_and_validate.return_value = None
        fake_deps.session_manager.connect.return_value = True
        fake_deps.session_manager.is_connected.return_value = True
        orch = MainOrchestrator(batch_context, tmp_path, deps=fake_deps)
        assert orch.run() == 1
        fake_deps.progress_manager.error.assert_called_once()

    def test_run_batch_success(self, batch_context: ExecutionContext, fake_deps: Dependencies, tmp_path: Path):
        fake_deps.license_validator.prompt_and_validate.return_value = "VALID-KEY"
        fake_deps.session_manager.discover_email_from_name.return_value = "alice@example.com"
        fake_deps.session_manager.connect.return_value = True
        fake_deps.session_manager.is_connected.return_value = True
        fake_deps.email_searcher.search.return_value = [MagicMock()]
        fake_deps.email_formatter.format_multiple_emails.return_value = "<html></html>"
        fake_deps.file_manager.save_pdf.return_value = tmp_path / "out.pdf"

        orch = MainOrchestrator(batch_context, tmp_path, deps=fake_deps)
        result = orch.run()

        assert result == 0  # no failures
        assert fake_deps.processed_store.mark_processed.call_count == 2


class TestProcessDirector:
    def test_skip_already_processed(self, batch_context: ExecutionContext, fake_deps: Dependencies, tmp_path: Path):
        fake_deps.processed_store.is_processed.return_value = True
        orch = MainOrchestrator(batch_context, tmp_path, deps=fake_deps)
        _setup_session(orch, fake_deps)

        ctx = DirectorContext("A", "B", "SMSF001", "batch", skip_if_processed=True)
        assert orch._process_director(ctx) == 0
        fake_deps.progress_manager.skip.assert_called_once_with("SMSF001", "Already processed")

    def test_email_not_found(self, batch_context: ExecutionContext, fake_deps: Dependencies, tmp_path: Path):
        fake_deps.session_manager.discover_email_from_name.return_value = None
        orch = MainOrchestrator(batch_context, tmp_path, deps=fake_deps)
        _setup_session(orch, fake_deps)

        ctx = DirectorContext("A", "B", "SMSF001", "batch")
        assert orch._process_director(ctx) == 1
        fake_deps.progress_manager.error.assert_called_once_with("SMSF001", "No Outlook identity found")

    def test_no_emails_found(self, batch_context: ExecutionContext, fake_deps: Dependencies, tmp_path: Path):
        fake_deps.session_manager.discover_email_from_name.return_value = "a@b.com"
        fake_deps.email_searcher.search.return_value = []
        orch = MainOrchestrator(batch_context, tmp_path, deps=fake_deps)
        _setup_session(orch, fake_deps)

        ctx = DirectorContext("A", "B", "SMSF001", "batch")
        assert orch._process_director(ctx) == 0
        fake_deps.processed_store.mark_processed.assert_called_once_with("SMSF001")

    def test_success_pipeline(self, batch_context: ExecutionContext, fake_deps: Dependencies, tmp_path: Path):
        fake_deps.session_manager.discover_email_from_name.return_value = "a@b.com"
        fake_deps.email_searcher.search.return_value = [MagicMock()]
        fake_deps.email_formatter.format_multiple_emails.return_value = "<html>X</html>"
        fake_deps.file_manager.save_pdf.return_value = tmp_path / "final.pdf"

        orch = MainOrchestrator(batch_context, tmp_path, deps=fake_deps)
        _setup_session(orch, fake_deps)
        ctx = DirectorContext("A", "B", "SMSF001", "batch")
        assert orch._process_director(ctx) == 0

        fake_deps.file_manager.save_pdf.assert_called_once_with(
            "<html>X</html>", "A", "B", "SMSF001"
        )
        fake_deps.progress_manager.complete.assert_called_once()

    def test_outlook_unavailable_escalates(self, batch_context: ExecutionContext, fake_deps: Dependencies, tmp_path: Path):
        fake_deps.session_manager.discover_email_from_name.side_effect = OutlookUnavailableError("boom")
        orch = MainOrchestrator(batch_context, tmp_path, deps=fake_deps)
        _setup_session(orch, fake_deps)

        ctx = DirectorContext("A", "B", "SMSF001", "batch")
        with pytest.raises(OutlookUnavailableError):
            orch._process_director(ctx)
        fake_deps.session_manager.disconnect.assert_called_once()


class TestInteractiveMode:
    def test_interactive_prompts_until_declined(self, batch_context: ExecutionContext, fake_deps: Dependencies, tmp_path: Path):
        fake_deps.license_validator.prompt_and_validate.return_value = "KEY"

        inputs = iter([
            {"first": "A", "last": "B", "smsf": "001"},
            {"first": "C", "last": "D", "smsf": "002"},
        ])
        confirms = iter([True, False])

        with patch.object(CLI, "get_director_input", side_effect=lambda: next(inputs)), \
             patch.object(CLI, "prompt_continue", side_effect=lambda: next(confirms)):

            fake_deps.session_manager.discover_email_from_name.return_value = "x@y.com"
            fake_deps.email_searcher.search.return_value = [MagicMock()]
            fake_deps.email_formatter.format_multiple_emails.return_value = "<html/>"
            fake_deps.file_manager.save_pdf.return_value = tmp_path / "x.pdf"

            ctx = ExecutionContext(
                mode=ExecutionMode.INTERACTIVE,
                directors=[],
                output_dir=tmp_path,
            )
            orch = MainOrchestrator(ctx, tmp_path, deps=fake_deps)
            result = orch.run()

            assert result == 0