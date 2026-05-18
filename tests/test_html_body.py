import pytest
from unittest.mock import MagicMock
from src.email_formatter import EmailFormatter


class MockEmail:
    def __init__(self, html_body=None, plain_body="", **kwargs):
        self.HTMLBody = html_body
        self.Body = plain_body
        self.SenderName = kwargs.get('SenderName', 'Test Sender')
        self.SenderEmailAddress = kwargs.get('SenderEmailAddress', 'test@sender.com')
        self.To = kwargs.get('To', 'recipient@test.com')
        self.CC = kwargs.get('CC', '')
        self.Subject = kwargs.get('Subject', 'Test Subject')
        self.SentOn = kwargs.get('SentOn', '2025-01-15')


class TestHTMLBodyUsage:
    """Test that EmailFormatter uses HTMLBody when available"""

    def test_uses_htmlbody_when_available(self):
        """Should use HTMLBody content when available"""
        formatter = EmailFormatter()

        html_content = "<p><b>Bold text</b></p><img src='logo.png'>"
        email = MockEmail(
            html_body=html_content,
            plain_body="Plain text version"
        )

        html = formatter.format_email(email)

        assert html_content in html
        assert "Bold text" in html

    def test_falls_back_to_body_when_htmlbody_empty(self):
        """Should fallback to Body when HTMLBody is empty or None"""
        formatter = EmailFormatter()

        email = MockEmail(
            html_body="",
            plain_body="Plain text body content"
        )

        html = formatter.format_email(email)

        assert "Plain text body content" in html

    def test_falls_back_to_body_when_htmlbody_none(self):
        """Should fallback to Body when HTMLBody is None"""
        formatter = EmailFormatter()

        email = MockEmail(
            html_body=None,
            plain_body="Fallback plain text"
        )

        html = formatter.format_email(email)

        assert "Fallback plain text" in html

    def test_preserves_html_formatting(self):
        """Should preserve HTML formatting like signatures, links"""
        formatter = EmailFormatter()

        html_with_signature = """
        <p>Hello,</p>
        <p>Best regards,<br>
        <b>John Smith</b><br>
        CEO | Company Name<br>
        <img src="company_logo.png">
        </p>
        <hr>
        <p style="font-size:12px">Confidentiality Notice</p>
        """

        email = MockEmail(html_body=html_with_signature)

        html = formatter.format_email(email)

        assert "John Smith" in html
        assert "CEO" in html
        assert "company_logo.png" in html

    def test_includes_headers_with_htmlbody(self):
        """Should still include From, Sent, To, Subject headers with HTML body"""
        formatter = EmailFormatter()

        email = MockEmail(
            html_body="<p>Email body</p>",
            SenderName="Jane Doe",
            SenderEmailAddress="jane@company.com",
            To="recipient@email.com",
            Subject="Test Subject",
            SentOn="2025-01-15 10:00:00"
        )

        html = formatter.format_email(email)

        assert "Jane Doe" in html
        assert "jane@company.com" in html
        assert "recipient@email.com" in html
        assert "Test Subject" in html
        assert "January 15, 2025" in html