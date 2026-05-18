"""
Tests for non-singleton PDFGenerator and PDFSession context manager.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.pdf_generator import PDFGenerator, PDFSession


@pytest.fixture
def generator() -> PDFGenerator:
    return PDFGenerator()


class TestLifecycle:
    def test_start_creates_browser(self, generator: PDFGenerator):
        with patch("src.pdf_generator.sync_playwright") as mock_pw:
            mock_ctx = MagicMock()
            mock_browser = MagicMock()
            mock_ctx.start.return_value = mock_ctx
            mock_ctx.chromium.launch.return_value = mock_browser
            mock_pw.return_value = mock_ctx

            assert generator.start() is True
            assert generator.is_running()
            assert generator._browser is mock_browser

    def test_start_failure(self, generator: PDFGenerator):
        with patch("src.pdf_generator.sync_playwright", side_effect=RuntimeError("boom")):
            assert generator.start() is False
            assert not generator.is_running()

    def test_stop_idempotent(self, generator: PDFGenerator):
        generator.stop()  # should not raise when nothing started

    def test_session_context_manager(self, generator: PDFGenerator):
        with patch.object(generator, "start", return_value=True) as mock_start, \
             patch.object(generator, "stop") as mock_stop:
            with PDFSession(generator) as g:
                assert g is generator
                mock_start.assert_called_once()
            mock_stop.assert_called_once()

    def test_session_raises_if_start_fails(self, generator: PDFGenerator):
        with patch.object(generator, "start", return_value=False):
            with pytest.raises(RuntimeError, match="Could not start PDF engine"):
                with PDFSession(generator):
                    pass  # pragma: no cover


class TestGeneratePdf:
    def test_generate_pdf_success(self, generator: PDFGenerator, tmp_path: Path):
        mock_page = MagicMock()
        mock_browser = MagicMock()
        mock_browser.new_page.return_value = mock_page

        generator._browser = mock_browser
        generator._playwright = MagicMock()

        output = tmp_path / "test.pdf"
        result = generator.generate_pdf("<h1>Hello</h1>", output)

        assert result is True
        mock_page.set_content.assert_called_once_with("<h1>Hello</h1>", wait_until="networkidle")
        mock_page.pdf.assert_called_once()
        mock_page.close.assert_called_once()

    def test_generate_pdf_requires_start(self, generator: PDFGenerator, tmp_path: Path):
        with pytest.raises(RuntimeError, match="must be started"):
            generator.generate_pdf("<h1>X</h1>", tmp_path / "x.pdf")