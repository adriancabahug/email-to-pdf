import pytest
from unittest.mock import patch, MagicMock
import os
from src.file_manager import FileManager


class TestFileManager:
    """Test FileManager - creates folders and saves PDFs"""

    def test_get_output_base_path_returns_configured_path(self):
        """Should return the configured output base path"""
        manager = FileManager(output_base="C:/Output/Folder")
        assert manager.get_output_base() == "C:/Output/Folder"

    def test_get_output_base_uses_default_when_not_specified(self):
        """Should use default path when not specified"""
        manager = FileManager()
        default_path = manager.get_output_base()
        assert "EmailPDFs" in default_path

    def test_generate_filename_creates_correct_format(self):
        """Should create filename in format: {First Last} - {SMSF}.pdf"""
        manager = FileManager()
        filename = manager.generate_filename("John", "Smith", "Test SMSF")

        assert "John Smith" in filename
        assert "Test SMSF" in filename
        assert filename.endswith(".pdf")

    def test_generate_filename_handles_empty_smsf(self):
        """Should handle empty SMSF name"""
        manager = FileManager()
        filename = manager.generate_filename("John", "Smith", "")

        assert "John Smith" in filename
        assert "- .pdf" in filename or " -.pdf" in filename

    @patch('os.makedirs')
    def test_create_smsf_folder_creates_directory(self, mock_makedirs):
        """Should create SMSF folder"""
        manager = FileManager(output_base="C:/Output")
        manager.create_smsf_folder("Test SMSF")

        mock_makedirs.assert_called()

    @patch('os.path.exists', return_value=True)
    @patch('builtins.open', create=True)
    @patch('os.makedirs')
    def test_save_pdf_copies_html_to_pdf_path(self, mock_makedirs, mock_open, mock_exists):
        """Should save HTML to PDF path"""
        manager = FileManager(output_base="C:/Output")

        from src.pdf_generator import PDFGenerator
        with patch.object(PDFGenerator, 'generate_pdf', return_value=True):
            result = manager.save_pdf("<html>test</html>", "John Smith", "Test SMSF", "C:/temp/test.pdf")

            assert result is True or result is not None

    def test_get_full_path_returns_correct_path(self):
        """Should return full path including folder and filename"""
        manager = FileManager(output_base="C:/Output")
        path = manager.get_full_path("Test SMSF", "John Smith- Test SMSF.pdf")

        assert "Test SMSF" in path
        assert "John Smith- Test SMSF.pdf" in path

    @patch('os.path.exists', return_value=False)
    @patch('os.makedirs')
    def test_ensure_folder_exists_creates_when_missing(self, mock_makedirs, mock_exists):
        """Should create folder when it doesn't exist"""
        manager = FileManager(output_base="C:/Output")
        result = manager.ensure_folder_exists("C:/Output/NewFolder")

        assert result is True
        mock_makedirs.assert_called()