from pathlib import Path
import tempfile

from unittest.mock import patch


class TestPlaywrightPDF:
    """Test PDFGenerator using Playwright instead of WeasyPrint"""

    def test_generate_pdf_creates_file_with_playwright(self):
        """Should generate PDF file using Playwright"""
        from src.pdf_generator import PDFGenerator
        generator = PDFGenerator()

        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch("src.pdf_generator.sync_playwright") as mock_pw,
        ):
            mock_page = mock_pw.return_value.start.return_value.chromium.launch.return_value.new_page.return_value
            generator.start()

            html_content = "<html><body><h1>Test</h1></body></html>"
            output_path = Path(tmpdir) / "test.pdf"

            result = generator.generate_pdf(html_content, output_path)

            assert result is True
            mock_page.set_content.assert_called_once_with(html_content, wait_until="networkidle")
            mock_page.pdf.assert_called_once_with(
                path=str(output_path),
                format="A4",
                print_background=True,
                margin={"top": "20mm", "bottom": "20mm", "left": "15mm", "right": "15mm"},
            )
            mock_page.close.assert_called_once()

    def test_generate_pdf_returns_false_on_error(self):
        """Should return False when Playwright fails"""
        from src.pdf_generator import PDFGenerator

        generator = PDFGenerator()
        generator._browser = None
        generator._playwright = None

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.pdf"
            result = generator.generate_pdf("<html>test</html>", output_path)
            assert result is False

    def test_pdf_generator_has_generate_pdf_method(self):
        """Should have generate_pdf method"""
        from src.pdf_generator import PDFGenerator
        generator = PDFGenerator()
        assert hasattr(generator, 'generate_pdf')
        assert callable(generator.generate_pdf)

    def test_generate_pdf_retries_on_failure(self):
        """Should return False when browser is None after start failure"""
        from src.pdf_generator import PDFGenerator
        generator = PDFGenerator()

        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch("src.pdf_generator.sync_playwright") as mock_pw,
        ):
            mock_pw.start.side_effect = RuntimeError("Browser unavailable")
            generator.start()
            generator._browser = None

            output_path = Path(tmpdir) / "test.pdf"
            result = generator.generate_pdf("<html>test</html>", output_path)
            assert result is False