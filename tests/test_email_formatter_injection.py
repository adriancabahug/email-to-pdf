import pytest
from unittest.mock import MagicMock
from src.file_manager import FileManager
from src.email_formatter import EmailFormatter


class TestEmailFormatterInjection:
    """Test that EmailFormatter can be injected into FileManager"""

    def test_file_manager_accepts_email_formatter_parameter(self):
        """FileManager should accept email_formatter as constructor parameter"""
        formatter = EmailFormatter()
        manager = FileManager(output_base="C:/test", email_formatter=formatter)

        assert manager.email_formatter is formatter

    def test_file_manager_uses_default_email_formatter_when_none_provided(self):
        """FileManager should create its own EmailFormatter when none provided"""
        manager = FileManager(output_base="C:/test")

        assert isinstance(manager.email_formatter, EmailFormatter)

    def test_file_manager_with_custom_email_formatter(self):
        """FileManager should use the provided custom EmailFormatter"""
        custom_formatter = EmailFormatter()
        manager = FileManager(output_base="C:/test", email_formatter=custom_formatter)

        result = manager.email_formatter._format_date(None)
        assert result == ""

    def test_file_manager_can_be_tested_with_mock_formatter(self):
        """FileManager should work with a mock EmailFormatter for testing"""
        mock_formatter = MagicMock()
        mock_formatter.format_multiple_emails.return_value = "<html>mocked</html>"

        manager = FileManager(output_base="C:/test", email_formatter=mock_formatter)

        emails = [MagicMock()]
        result = manager.email_formatter.format_multiple_emails(emails)

        assert result == "<html>mocked</html>"
        mock_formatter.format_multiple_emails.assert_called_once_with(emails)
