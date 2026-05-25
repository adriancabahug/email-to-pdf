"""
Tests for refactored MainOrchestrator using Dependencies injection.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.dependencies import Dependencies
from src.cli import CLI, ExecutionContext, ExecutionMode, SMSFEntry
from datetime import datetime
from src.main_orchestrator import SMSFSpec, MainOrchestrator, OutlookUnavailableError


@pytest.fixture
def fake_deps(tmp_path: Path) -> Dependencies:
    """Fully wired fake dependency graph."""
    pdf = MagicMock()
    pdf.start.return_value = True

    session_mgr = MagicMock()
    session_mgr.connect.return_value = True
    session_mgr.is_connected.return_value = True

    deps = Dependencies()
    deps.pdf_generator = pdf
    deps.session_manager = session_mgr
    deps.config_manager = None
    deps.email_searcher = MagicMock()
    deps.email_formatter = MagicMock()
    deps.file_manager = MagicMock()
    deps.progress_manager = MagicMock()
    deps.license_validator = MagicMock()
    deps.processed_store = MagicMock()

    return deps


def _setup_session(orch: MainOrchestrator, deps: Dependencies):
    orch._session = deps.session_manager
    orch._searcher = deps.email_searcher


@pytest.fixture
def batch_context(tmp_path: Path) -> ExecutionContext:
    return ExecutionContext(
        mode=ExecutionMode.BATCH,
        smsf_entries=[
            SMSFEntry(smsf="Aura Super", search_terms=["term1"], start_date=datetime(2025,1,1), end_date=datetime(2025,12,31)),
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
        fake_deps.license_validator.prompt_and_validate.return_value = "KEY"
        fake_deps.session_manager.connect.return_value = True
        fake_deps.session_manager.is_connected.return_value = True
        fake_deps.email_searcher.search.return_value = []
        fake_deps.processed_store.is_processed.return_value = False

        orch = MainOrchestrator(batch_context, tmp_path, deps=fake_deps)
        result = orch.run()

        assert result == 0
        fake_deps.session_manager.connect.assert_called_once()
        fake_deps.session_manager.disconnect.assert_called_once()


class TestProcessDirector:
    def test_skip_already_processed(self, batch_context: ExecutionContext, fake_deps: Dependencies, tmp_path: Path):
        fake_deps.processed_store.is_processed.return_value = True
        orch = MainOrchestrator(batch_context, tmp_path, deps=fake_deps)
        _setup_session(orch, fake_deps)

        ctx = SMSFSpec(smsf="SMSF001", search_terms=["term1"], start_date=datetime(2025,1,1), end_date=datetime(2025,12,31), mode="batch", skip_if_processed=True)
        assert orch._process_smsf(ctx) == 0
        fake_deps.progress_manager.skip.assert_called_once_with("SMSF001", "Already processed")