import pytest
from unittest.mock import MagicMock, patch
import os
import tempfile
from src.file_manager import FileManager
from src.pdf_generator import PDFGenerator


class TestPDFGeneratorInjection:
    """Test that FileManager accepts PDFGenerator as injectable dependency"""

    def test_file_manager_accepts_pdf_generator_parameter(self):
        """FileManager should accept pdf_generator as optional constructor parameter"""
        mock_pdf = MagicMock(spec=PDFGenerator)
        
        manager = FileManager(output_base="C:/test", pdf_generator=mock_pdf)

        assert manager.pdf_generator is mock_pdf

    def test_file_manager_uses_default_pdf_generator_when_none_provided(self):
        """FileManager should create default PDFGenerator when not provided"""
        manager = FileManager(output_base="C:/test")

        assert manager.pdf_generator is not None
        assert isinstance(manager.pdf_generator, PDFGenerator)

    def test_file_manager_with_custom_pdf_generator(self):
        """Should use custom PDFGenerator"""
        mock_pdf = MagicMock()
        mock_pdf.generate_pdf.return_value = True

        manager = FileManager(output_base="C:/test", pdf_generator=mock_pdf)

        result = manager.save_pdf("<html>test</html>", "John", "Smith", "Test SMSF")

        mock_pdf.generate_pdf.assert_called_once()

    def test_file_manager_can_be_tested_with_mock_pdf(self):
        """Should be able to inject mock PDFGenerator for testing"""
        mock_pdf = MagicMock()
        mock_pdf.generate_pdf.return_value = True

        manager = FileManager(output_base="C:/test", pdf_generator=mock_pdf)

        result = manager.save_pdf("<html>test</html>", "John", "Smith", "Test SMSF")

        assert mock_pdf.generate_pdf.called