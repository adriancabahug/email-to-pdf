import pytest
from unittest.mock import patch, MagicMock, Mock
from pathlib import Path
import os
from src.file_manager import FileManager


def make_mock_file_manager(output_base="C:/Output"):
    """Create FileManager with mocked dependencies"""
    mock_pdf = Mock()
    mock_formatter = Mock()
    return FileManager(mock_pdf, mock_formatter, output_base=output_base)


class TestFileManager:
    """Test FileManager - creates folders and saves PDFs"""

    def test_get_output_base_path_returns_configured_path(self):
        """Should return the configured output base path"""
        manager = make_mock_file_manager(output_base="C:/Output/Folder")
        assert manager.get_output_base() == Path("C:/Output/Folder")

    def test_get_output_base_uses_default_when_not_specified(self):
        """Should use default path when not specified"""
        mock_pdf = Mock()
        mock_formatter = Mock()
        manager = FileManager(mock_pdf, mock_formatter)
        default_path = manager.get_output_base()
        assert "EmailPDFs" in str(default_path)

    def test_generate_filename_creates_correct_format(self):
        """Should create filename in format: {First Last} - {SMSF}.pdf"""
        manager = make_mock_file_manager()
        filename = manager.generate_filename("John", "Smith", "Test SMSF")

        assert "John Smith" in filename
        assert "Test SMSF" in filename
        assert filename.endswith(".pdf")

    def test_generate_filename_handles_empty_smsf(self):
        """Should handle empty SMSF name"""
        manager = make_mock_file_manager()
        filename = manager.generate_filename("John", "Smith", "")

        assert "John Smith" in filename
        assert "- .pdf" in filename or " -.pdf" in filename

    @patch('pathlib.Path.mkdir')
    def test_create_smsf_folder_creates_directory(self, mock_mkdir):
        """Should create SMSF folder"""
        manager = make_mock_file_manager(output_base="C:/Output")
        manager.create_smsf_folder("Test SMSF")

        mock_mkdir.assert_called()

    @patch('os.path.exists', return_value=True)
    @patch('builtins.open', create=True)
    @patch('os.makedirs')
    def test_save_pdf_copies_html_to_pdf_path(self, mock_makedirs, mock_open, mock_exists):
        """Should save HTML to PDF path"""
        manager = make_mock_file_manager(output_base="C:/Output")
        manager.pdf_generator.generate_pdf = Mock(return_value=True)
        result = manager.save_pdf("<html>test</html>", "John", "Smith", "Test SMSF")

        assert result is not None

    def test_get_full_path_returns_correct_path(self):
        """Should return full path including folder and filename"""
        manager = make_mock_file_manager(output_base="C:/Output")
        path = manager.get_full_path("Test SMSF", "John Smith- Test SMSF.pdf")

        assert "Test SMSF" in str(path)
        assert "John Smith- Test SMSF.pdf" in str(path)

    @patch('pathlib.Path.mkdir')
    def test_ensure_folder_exists_creates_when_missing(self, mock_mkdir):
        """Should create folder when it doesn't exist"""
        manager = make_mock_file_manager(output_base="C:/Output")
        result = manager.ensure_folder_exists("C:/Output/NewFolder")

        assert result is True
        mock_mkdir.assert_called()