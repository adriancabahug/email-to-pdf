import pytest
from unittest.mock import MagicMock, PropertyMock
from src.email_formatter import EmailFormatter, AttachmentHandler
from src.config_manager import ConfigManager


class TestAttachmentHandler:
    def _make_config(self):
        cfg = ConfigManager()
        cfg._config["pdf"]["attachments"]["skip_types"] = ["application/x-msdownload"]
        cfg._config["pdf"]["attachments"]["embed_inline_types"] = ["image/jpeg", "image/png"]
        cfg._config["pdf"]["attachments"]["max_size_mb"] = 10
        return cfg

    def test_should_embed_image_under_limit(self):
        handler = AttachmentHandler(self._make_config())
        mock_attachment = MagicMock()
        mock_attachment.Size = 1024 * 1024
        mock_attachment.FileName = "photo.jpg"
        prop_accessor = MagicMock()
        prop_accessor.GetProperty = MagicMock(return_value="image/jpeg")
        mock_attachment.PropertyAccessor = prop_accessor

        should_embed, reason = handler._should_embed(mock_attachment)
        assert should_embed is True

    def test_should_skip_executable(self):
        handler = AttachmentHandler(self._make_config())
        mock_attachment = MagicMock()
        mock_attachment.Size = 50000
        mock_attachment.FileName = "file.exe"
        prop_accessor = MagicMock()
        prop_accessor.GetProperty = MagicMock(return_value="application/x-msdownload")
        mock_attachment.PropertyAccessor = prop_accessor

        should_embed, reason = handler._should_embed(mock_attachment)
        assert should_embed is False
        assert "blocked" in reason

    def test_should_skip_large_attachment(self):
        handler = AttachmentHandler(self._make_config())
        mock_attachment = MagicMock()
        mock_attachment.Size = 20 * 1024 * 1024
        mock_attachment.FileName = "big_image.png"
        prop_accessor = MagicMock()
        prop_accessor.GetProperty = MagicMock(return_value="image/png")
        mock_attachment.PropertyAccessor = prop_accessor

        should_embed, reason = handler._should_embed(mock_attachment)
        assert should_embed is False
        assert "exceeds" in reason

    def test_extract_returns_list(self):
        handler = AttachmentHandler()
        mock_email = MagicMock()
        mock_email.Attachments.Count = 0
        result = handler.extract(mock_email)
        assert isinstance(result, list)


class TestEmailFormatter:
    def test_format_email_with_no_attachments(self):
        formatter = EmailFormatter()
        mock_email = MagicMock()
        mock_email.sender_name = "John Doe"
        mock_email.sender_email = "john@example.com"
        mock_email.to_recipients = "jane@example.com"
        mock_email.cc_recipients = ""
        mock_email.subject = "Test Subject"
        mock_email.html_body = "<p>Hello world</p>"
        mock_email.body = "Hello world"
        mock_email.sent_on = MagicMock()
        mock_email.sent_on.year = 2024
        mock_email.sent_on.month = 6
        mock_email.sent_on.day = 15
        mock_email.sent_on.hour = 10
        mock_email.sent_on.minute = 30
        mock_email.Attachments.Count = 0

        result = formatter.format_email(mock_email, include_attachments=True)
        assert "John Doe" in result
        assert "Test Subject" in result
        assert "Hello world" in result

    def test_format_multiple_emails_produces_valid_html(self):
        formatter = EmailFormatter()
        mock_email = MagicMock()
        mock_email.sender_name = "John Doe"
        mock_email.sender_email = "john@example.com"
        mock_email.to_recipients = "jane@example.com"
        mock_email.cc_recipients = ""
        mock_email.subject = "Test"
        mock_email.html_body = "<p>Test</p>"
        mock_email.body = "Test"
        mock_email.sent_on = MagicMock()
        mock_email.sent_on.year = 2024
        mock_email.sent_on.month = 6
        mock_email.sent_on.day = 15
        mock_email.sent_on.hour = 10
        mock_email.sent_on.minute = 30
        mock_email.Attachments.Count = 0

        result = formatter.format_multiple_emails([mock_email, mock_email])
        assert "<!DOCTYPE html>" in result
        assert "</html>" in result
        assert "John Doe" in result
        assert result.count('class="owa-email-block"') == 2