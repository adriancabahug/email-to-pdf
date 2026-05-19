"""
Tests for PDFGenerator with browser recycling support.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.pdf_generator import PDFGenerator, DEFAULT_RECYCL_THRESHOLD


class TestBrowserRecycling:
    """Tests for browser recycling functionality."""

    def test_default_recycle_threshold(self):
        gen = PDFGenerator()
        assert gen._recycle_threshold == DEFAULT_RECYCL_THRESHOLD
        assert gen._pdf_count == 0

    def test_custom_recycle_threshold(self):
        gen = PDFGenerator(recycle_threshold=10)
        assert gen._recycle_threshold == 10
        assert gen._pdf_count == 0

    def test_pdf_count_increments_on_success(self):
        gen = PDFGenerator(recycle_threshold=5)
        gen._browser = MagicMock()
        gen._playwright = MagicMock()

        gen._browser.new_page.return_value = MagicMock()

        result = gen.generate_pdf("<html></html>", Path("test.pdf"))

        assert result is True
        assert gen._pdf_count == 1

    def test_pdf_count_increments_on_file_method(self):
        gen = PDFGenerator(recycle_threshold=5)
        gen._browser = MagicMock()
        gen._playwright = MagicMock()

        page_mock = MagicMock()
        gen._browser.new_page.return_value = page_mock

        result = gen.generate_pdf_from_file("input.html", "output.pdf")

        assert result is True
        assert gen._pdf_count == 1

    def test_reset_count_method(self):
        gen = PDFGenerator()
        gen._pdf_count = 10
        gen.reset_count()
        assert gen._pdf_count == 0

    def test_count_resets_on_restart(self):
        gen = PDFGenerator(recycle_threshold=3)
        gen._pdf_count = 3

        with patch.object(gen, 'start', return_value=True):
            gen._restart_browser()

        assert gen._pdf_count == 0


class TestPDFGenerator:
    """Basic tests for PDFGenerator to ensure existing behavior works."""

    def test_initial_state(self):
        gen = PDFGenerator()
        assert gen._browser is None
        assert gen._playwright is None
        assert not gen.is_running()

    def test_stop_resets_count(self):
        gen = PDFGenerator()
        gen._pdf_count = 5
        gen._browser = MagicMock()
        gen._playwright = MagicMock()

        gen.stop()

        assert gen._pdf_count == 0
        assert gen._browser is None
        assert gen._playwright is None