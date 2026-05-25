"""
Tests for AsyncPDFGenerator and AsyncPipelineOrchestrator.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.email_searcher import ExtractedEmail
from src.main_orchestrator import (
    AsyncPipelineOrchestrator,
    PDFJob,
    SMSFSpec,
)
from src.pdf_generator import AsyncPDFGenerator


# ------------------------------------------------------------------ #
# Fixtures
# ------------------------------------------------------------------ #

@pytest.fixture
def sample_email() -> ExtractedEmail:
    return ExtractedEmail(
        entry_id="msg1",
        sender_name="Alice Smith",
        sender_email="alice@test.com",
        to_recipients=["bob@test.com"],
        cc_recipients=[],
        bcc_recipients=[],
        subject="Test Email",
        html_body="<p>Hello</p>",
        body="Hello",
        received_time=datetime(2025, 1, 15, 10, 30),
        sent_on=datetime(2025, 1, 15, 10, 30),
        internet_message_id="<abc@test.com>",
        conversation_id="conv1",
    )


@pytest.fixture
def mock_deps():
    deps = MagicMock()
    deps.progress_manager = MagicMock()
    deps.session_manager = MagicMock()
    deps.email_searcher = MagicMock()
    deps.email_formatter = MagicMock()
    deps.config_manager = MagicMock()
    deps.cache = MagicMock()
    deps.processed_store = MagicMock()
    deps.email_formatter.format_multiple_emails.return_value = "<html><body>Formatted</body></html>"
    return deps


@pytest.fixture
def mock_browser_stack():
    """Returns a tuple (mock_async_pw_fn, mock_browser, mock_page) wired for
    the `async_playwright().start()` pattern used by AsyncPDFGenerator."""
    mock_page = AsyncMock()
    mock_browser = AsyncMock()
    mock_browser.new_page.return_value = mock_page
    mock_pw_instance = AsyncMock()
    mock_pw_instance.chromium.launch.return_value = mock_browser
    mock_pw_fn = MagicMock()
    mock_pw_fn.start = AsyncMock(return_value=mock_pw_instance)
    return mock_pw_fn, mock_browser, mock_page


@pytest.fixture
def orchestrator(mock_deps, tmp_path):
    orch = AsyncPipelineOrchestrator(mock_deps, tmp_path)
    orch._searcher = mock_deps.email_searcher
    orch._store = mock_deps.processed_store
    orch._advisor_matcher = MagicMock()
    orch._search_engine = MagicMock()
    orch._deduplicator = MagicMock()
    orch._pdf_grouper = MagicMock()
    orch._session = mock_deps.session_manager
    return orch


# ------------------------------------------------------------------ #
# PDFJob dataclass
# ------------------------------------------------------------------ #

class TestPDFJob:
    def test_fields(self, sample_email):
        job = PDFJob(group_name="MyGroup", emails=[sample_email], smsf_name="SMSF001")
        assert job.group_name == "MyGroup"
        assert job.emails == [sample_email]
        assert job.smsf_name == "SMSF001"


# ------------------------------------------------------------------ #
# AsyncPDFGenerator
# ------------------------------------------------------------------ #

class TestAsyncPDFGenerator:
    @pytest.mark.anyio
    async def test_start_stop_lifecycle(self, mock_browser_stack):
        mock_pw_fn, mock_browser, _ = mock_browser_stack
        with patch("src.pdf_generator.async_playwright", return_value=mock_pw_fn):
            gen = AsyncPDFGenerator()
            started = await gen.start()
            assert started is True
            assert gen._browser is not None

            await gen.stop()
            assert gen._browser is None

    @pytest.mark.anyio
    async def test_generate_pdf_success(self, tmp_path, mock_browser_stack):
        mock_pw_fn, mock_browser, mock_page = mock_browser_stack
        with patch("src.pdf_generator.async_playwright", return_value=mock_pw_fn):
            gen = AsyncPDFGenerator()
            await gen.start()

            out_path = tmp_path / "out.pdf"
            result = await gen.generate_pdf("<html><body>Test</body></html>", out_path)
            assert result is True
            mock_page.set_content.assert_called_once()
            mock_page.pdf.assert_called_once_with(
                path=str(out_path),
                format="A4",
                print_background=True,
                margin={"top": "20mm", "bottom": "20mm", "left": "15mm", "right": "15mm"},
            )
            mock_page.close.assert_called_once()

            await gen.stop()

    @pytest.mark.anyio
    async def test_generate_pdf_failure(self, tmp_path, mock_browser_stack):
        mock_pw_fn, mock_browser, mock_page = mock_browser_stack
        mock_page.set_content.side_effect = Exception("Render failed")
        with patch("src.pdf_generator.async_playwright", return_value=mock_pw_fn):
            gen = AsyncPDFGenerator()
            await gen.start()

            out_path = tmp_path / "fail.pdf"
            result = await gen.generate_pdf("<html><body>Fail</body></html>", out_path)
            assert result is False

            await gen.stop()

    @pytest.mark.anyio
    async def test_recycle_threshold(self, tmp_path, mock_browser_stack):
        mock_pw_fn, mock_browser, mock_page = mock_browser_stack
        with patch("src.pdf_generator.async_playwright", return_value=mock_pw_fn):
            gen = AsyncPDFGenerator(recycle_threshold=2)
            await gen.start()

            for i in range(3):
                out_path = tmp_path / f"test_{i}.pdf"
                result = await gen.generate_pdf("<html></html>", out_path)
                assert result is True

            # After 3 PDFs with threshold 2, browser should have been restarted
            assert gen._pdf_count == 1  # Reset after recycle

            await gen.stop()

    @pytest.mark.anyio
    async def test_not_available_returns_false(self):
        with patch("src.pdf_generator.ASYNC_PLAYWRIGHT_AVAILABLE", False):
            gen = AsyncPDFGenerator()
            started = await gen.start()
            assert started is False

            result = await gen.generate_pdf("<html></html>", Path("out.pdf"))
            assert result is False


# ------------------------------------------------------------------ #
# AsyncPipelineOrchestrator
# ------------------------------------------------------------------ #

class TestAsyncPipelineOrchestrator:
    @pytest.mark.anyio
    async def test_producer_empty_smsf_list(self, orchestrator):
        result = await orchestrator.run([])
        assert result == 0

    @pytest.mark.anyio
    async def test_producer_skips_processed(self, orchestrator, sample_email):
        orchestrator._store.is_processed.return_value = True
        orchestrator._searcher.search.return_value = [sample_email]

        ctx = SMSFSpec(
            smsf="SMSF001",
            search_terms=["test"],
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2025, 12, 31),
            mode="batch",
            skip_if_processed=True,
        )

        jobs = []

        async def collecting_consumer(pdf_gen):
            while True:
                job = await orchestrator._queue.get()
                if job is None:
                    orchestrator._queue.task_done()
                    break
                jobs.append(job)
                orchestrator._queue.task_done()

        with patch.object(orchestrator, "_consumer", collecting_consumer):
            result = await orchestrator.run([ctx])
            assert isinstance(result, int)
            assert len(jobs) == 0

    @pytest.mark.anyio
    async def test_producer_yields_pdfjobs(self, orchestrator, sample_email):
        orchestrator._searcher.search.return_value = [sample_email]
        isnone = MagicMock()
        isnone.__eq__ = lambda s, o: o is None
        orchestrator._search_engine.is_relevant.return_value = isnone
        orchestrator._deduplicator.deduplicate.return_value = [sample_email]
        orchestrator._pdf_grouper.group_emails.return_value = {
            "AdvisorOrg": [sample_email],
        }
        orchestrator._store.is_processed.return_value = False

        ctx = SMSFSpec(
            smsf="SMSF001",
            search_terms=["advisor"],
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2025, 12, 31),
            mode="batch",
            skip_if_processed=False,
        )

        jobs = []

        async def collecting_consumer(pdf_gen):
            while True:
                job = await orchestrator._queue.get()
                if job is None:
                    orchestrator._queue.task_done()
                    break
                jobs.append(job)
                orchestrator._queue.task_done()

        with patch.object(orchestrator, "_consumer", collecting_consumer):
            result = await orchestrator.run([ctx])
            assert len(jobs) == 1
            assert jobs[0].group_name == "AdvisorOrg"
            assert jobs[0].smsf_name == "SMSF001"

    @pytest.mark.anyio
    async def test_producer_fallback_group(self, orchestrator, sample_email):
        orchestrator._searcher.search.return_value = [sample_email]
        isnone = MagicMock()
        isnone.__eq__ = lambda s, o: o is None
        orchestrator._search_engine.is_relevant.return_value = isnone
        orchestrator._deduplicator.deduplicate.return_value = [sample_email]
        orchestrator._pdf_grouper.group_emails.return_value = {}
        orchestrator._store.is_processed.return_value = False

        ctx = SMSFSpec(
            smsf="SMSF001",
            search_terms=["test"],
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2025, 12, 31),
            mode="batch",
            skip_if_processed=False,
        )

        jobs = []

        async def collecting_consumer(pdf_gen):
            while True:
                job = await orchestrator._queue.get()
                if job is None:
                    orchestrator._queue.task_done()
                    break
                jobs.append(job)
                orchestrator._queue.task_done()

        with patch.object(orchestrator, "_consumer", collecting_consumer):
            result = await orchestrator.run([ctx])
            assert len(jobs) == 1
            assert jobs[0].group_name == "SMSF001"

    @pytest.mark.anyio
    async def test_consumer_writes_pdf(self, orchestrator, sample_email, mock_deps, tmp_path):
        mock_pdf_gen = AsyncMock()
        mock_pdf_gen.generate_pdf.return_value = True

        await orchestrator._queue.put(PDFJob(
            group_name="TestGroup",
            emails=[sample_email],
            smsf_name="SMSF001",
        ))
        await orchestrator._queue.put(None)

        await orchestrator._consumer(mock_pdf_gen)

        expected_folder = tmp_path / "SMSF001"
        expected_path = expected_folder / "TestGroup.pdf"
        mock_pdf_gen.generate_pdf.assert_called_once()
        args, _ = mock_pdf_gen.generate_pdf.call_args
        assert args[1] == expected_path
        mock_deps.progress_manager.complete.assert_called_once()

    @pytest.mark.anyio
    async def test_consumer_handles_failure(self, orchestrator, sample_email):
        mock_pdf_gen = AsyncMock()
        mock_pdf_gen.generate_pdf.return_value = False

        await orchestrator._queue.put(PDFJob(
            group_name="FailGroup",
            emails=[sample_email],
            smsf_name="SMSF001",
        ))
        await orchestrator._queue.put(None)

        await orchestrator._consumer(mock_pdf_gen)
        assert orchestrator._failed_count == 1

    @pytest.mark.anyio
    async def test_connect_failure(self, mock_deps, tmp_path):
        mock_deps.session_manager.connect.return_value = False
        orch = AsyncPipelineOrchestrator(mock_deps, tmp_path)
        assert orch.connect() is False

    @pytest.mark.anyio
    async def test_connect_success(self, mock_deps, tmp_path):
        mock_deps.session_manager.connect.return_value = True
        mock_deps.session_manager.is_connected.return_value = True
        orch = AsyncPipelineOrchestrator(mock_deps, tmp_path)
        assert orch.connect() is True
        assert orch._searcher is not None
