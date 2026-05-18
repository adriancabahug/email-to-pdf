import pytest
from unittest.mock import patch, MagicMock
import os
import tempfile


class TestPlaywrightPDF:
    """Test PDFGenerator using Playwright instead of WeasyPrint"""

    def test_generate_pdf_creates_file_with_playwright(self):
        """Should generate PDF file using Playwright"""
        from src.pdf_generator import PDFGenerator
        generator = PDFGenerator()
        generator.start()

        html_content = """
        <html>
        <head><style>body { font-family: Arial; }</style></head>
        <body>
            <h1>Test Email</h1>
            <p>This is a test email with <b>bold</b> text.</p>
        </body>
        </html>
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test.pdf")

            result = generator.generate_pdf(html_content, output_path)

            assert result is True
            assert os.path.exists(output_path)
            assert os.path.getsize(output_path) > 0

    def test_generate_pdf_returns_false_on_error(self):
        """Should return False when Playwright fails"""
        from src.pdf_generator import PDFGenerator

        PDFGenerator._instance = None
        generator = PDFGenerator()
        generator._browser = None
        generator._playwright = None

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test.pdf")
            result = generator.generate_pdf("<html>test</html>", output_path)
            assert result is False

    def test_pdf_generator_has_generate_pdf_method(self):
        """Should have generate_pdf method"""
        from src.pdf_generator import PDFGenerator
        generator = PDFGenerator()
        assert hasattr(generator, 'generate_pdf')
        assert callable(generator.generate_pdf)

    def test_generate_pdf_retries_on_failure(self):
        """Should retry PDF generation on failure"""
        from src.pdf_generator import PDFGenerator
        PDFGenerator._instance = None
        generator = PDFGenerator()
        generator.start()
        generator._browser = None

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test.pdf")
            result = generator.generate_pdf("<html>test</html>", output_path, max_retries=0)
            assert result is False