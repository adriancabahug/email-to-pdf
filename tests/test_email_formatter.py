import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime
from src.email_formatter import EmailFormatter


class MockEmail:
    """Mock email for testing - attribute access matches ExtractedEmail fields"""
    def __init__(self, **kwargs):
        self.sender_name = kwargs.get('sender_name') or kwargs.get('SenderName', 'Test Sender')
        self.sender_email = kwargs.get('sender_email') or kwargs.get('SenderEmailAddress', 'test@sender.com')
        self.to_recipients = kwargs.get('to_recipients') or kwargs.get('To', 'recipient@test.com')
        self.cc_recipients = kwargs.get('cc_recipients') or kwargs.get('CC', '')
        self.bcc_recipients = kwargs.get('bcc_recipients') or kwargs.get('BCC', '')
        self.subject = kwargs.get('subject') or kwargs.get('Subject', 'Test Subject')
        self.body = kwargs.get('body') or kwargs.get('Body', 'Test body content')
        self.html_body = kwargs.get('html_body') or kwargs.get('HTMLBody', None)
        self.sent_on = kwargs.get('sent_on') or kwargs.get('SentOn', '2025-01-15 10:30:00')


class TestEmailFormatter:
    """Test EmailFormatter - formats emails into raw Outlook-style HTML"""

    def test_format_email_includes_all_fields(self):
        """Formatted email should include From, Sent, To, CC, Subject, Body"""
        formatter = EmailFormatter()
        mock_email = MockEmail(
            SenderName="John Smith",
            SenderEmailAddress="john@company.com",
            To="tanesha@accounting.com",
            CC="alyssa@accounting.com",
            Subject="Tax Question",
            Body="Please help with tax.",
            SentOn="2025-01-15"
        )

        html = formatter.format_email(mock_email)

        assert "John Smith" in html
        assert "john@company.com" in html
        assert "tanesha@accounting.com" in html
        assert "alyssa@accounting.com" in html
        assert "Tax Question" in html
        assert "Please help with tax." in html
        assert "January 15, 2025" in html

    def test_format_email_adds_page_break_between_emails(self):
        """Should add page break between multiple emails"""
        formatter = EmailFormatter()
        mock_email1 = MockEmail(Subject="First Email", Body="First body")
        mock_email2 = MockEmail(Subject="Second Email", Body="Second body")

        html = formatter.format_email(mock_email1)
        html += formatter.format_email(mock_email2)

        assert "First Email" in html
        assert "Second Email" in html

    def test_format_multiple_emails_combines_all(self):
        """Should combine multiple emails into single HTML"""
        formatter = EmailFormatter()
        emails = [
            MockEmail(Subject="Email 1", Body="Body 1"),
            MockEmail(Subject="Email 2", Body="Body 2"),
            MockEmail(Subject="Email 3", Body="Body 3"),
        ]

        html = formatter.format_multiple_emails(emails)

        assert "Email 1" in html
        assert "Email 2" in html
        assert "Email 3" in html
        assert "Body 1" in html
        assert "Body 2" in html
        assert "Body 3" in html

    def test_format_email_handles_empty_cc(self):
        """Should omit CC line entirely when empty"""
        formatter = EmailFormatter()
        mock_email = MockEmail(CC="")

        html = formatter.format_email(mock_email)

        assert "CC:" not in html

    def test_format_email_includes_cc_when_present(self):
        """Should include CC line when recipients exist"""
        formatter = EmailFormatter()
        mock_email = MockEmail(CC="alyssa@accounting.com")

        html = formatter.format_email(mock_email)

        assert "Cc:" in html
        assert "alyssa@accounting.com" in html

    def test_format_email_outlook_style_header(self):
        """Header should include From, To, Subject fields"""
        formatter = EmailFormatter()
        mock_email = MockEmail(
            SenderName="John Smith",
            SenderEmailAddress="john@company.com",
            To="tanesha@accounting.com",
            CC="",
            Subject="Tax Question",
            Body="Please help with tax.",
            SentOn=datetime(2026, 5, 17, 21, 25, 47)
        )

        html = formatter.format_email(mock_email)

        assert "John Smith" in html
        assert "From:" in html
        assert "To:" in html
        assert "Subject:" in html

    def test_format_email_strips_htmlbody_outer_tags(self):
        """Should strip <html>, <head>, <body> tags from HTMLBody before embedding"""
        formatter = EmailFormatter()
        mock_email = MockEmail(
            HTMLBody="<html><head><style>body{color:red}</style></head><body><p>Hello</p></body></html>"
        )

        html = formatter.format_email(mock_email)

        assert "<html>" not in html
        assert "</html>" not in html
        assert "<head>" not in html
        assert "</head>" not in html
        assert "<body>" not in html
        assert "</body>" not in html
        assert "<p>Hello</p>" in html

    def test_format_email_has_page_break_styling(self):
        """Email container should have owa-email-block class"""
        formatter = EmailFormatter()
        mock_email = MockEmail()

        html = formatter.format_email(mock_email)

        assert 'class="owa-email-block"' in html

    def test_format_email_plain_text_fallback(self):
        """Should wrap plain text in <pre> when no HTMLBody"""
        formatter = EmailFormatter()
        mock_email = MockEmail(
            HTMLBody=None,
            Body="Plain text content"
        )

        html = formatter.format_email(mock_email)

        assert "<pre" in html
        assert "Plain text content" in html

    def test_format_email_preserves_html_body(self):
        """Should preserve HTML formatting in email body"""
        formatter = EmailFormatter()
        mock_email = MockEmail(
            Body="<p>This is <b>bold</b> text</p><ul><li>Item 1</li></ul>"
        )

        html = formatter.format_email(mock_email)

        assert "<p>This is <b>bold</b> text</p>" in html
        assert "<li>Item 1</li>" in html

    def test_format_email_without_subject(self):
        """Should handle emails without subject"""
        formatter = EmailFormatter()
        mock_email = MockEmail(Subject="")

        html = formatter.format_email(mock_email)

        assert "Subject:" in html


class TestFormatDate:
    """Test _format_date helper method"""

    def test_format_date_with_datetime_object(self):
        """Should format Python datetime objects correctly"""
        formatter = EmailFormatter()
        dt = datetime(2026, 5, 17, 21, 25, 47)

        result = formatter._format_date(dt)

        assert "Sunday" in result
        assert "May" in result
        assert "2026" in result
        assert "9:25 PM" in result

    def test_format_date_with_pywintypes_datetime(self):
        """Should handle pywintypes.datetime-like objects via attribute detection"""
        formatter = EmailFormatter()

        class MockPywinDateTime:
            """Simulates pywintypes.datetime which has year/month/day but fails isinstance(dt, datetime)"""
            def __init__(self):
                self.year = 2026
                self.month = 5
                self.day = 17
                self.hour = 21
                self.minute = 25

        mock_dt = MockPywinDateTime()

        result = formatter._format_date(mock_dt)

        assert "Sunday" in result
        assert "May" in result
        assert "2026" in result
        assert "9:25 PM" in result

    def test_format_date_with_iso_string(self):
        """Should parse ISO format strings with timezone offset"""
        formatter = EmailFormatter()
        iso_str = "2026-05-17T21:25:47+10:00"

        result = formatter._format_date(iso_str)

        assert "Sunday" in result
        assert "May" in result
        assert "2026" in result

    def test_format_date_with_none_returns_empty_string(self):
        """Should return empty string for None input"""
        formatter = EmailFormatter()

        result = formatter._format_date(None)

        assert result == ""

    def test_format_date_output_format(self):
        """Should match exact Outlook verbal format: Day, Month DD, YYYY H:MM AM/PM"""
        formatter = EmailFormatter()
        dt = datetime(2026, 5, 17, 9, 25, 0)

        result = formatter._format_date(dt)

        assert result == "Sunday, May 17, 2026 9:25 AM"

    def test_format_email_uses_formatted_date(self):
        """format_email should use _format_date output, not raw str(sent_on)"""
        formatter = EmailFormatter()
        mock_email = MockEmail(
            SenderName="John Smith",
            SenderEmailAddress="john@company.com",
            To="tanesha@accounting.com",
            CC="",
            Subject="Tax Question",
            Body="Please help with tax.",
            SentOn=datetime(2026, 5, 17, 21, 25, 47)
        )

        html = formatter.format_email(mock_email)

        assert "Sunday" in html
        assert "May 17, 2026" in html
        assert "9:25 PM" in html
        assert "2026-05-17" not in html


class TestMultipleEmailsWithHeaderBanners:
    """Test format_multiple_emails with header banners and page breaks"""

    def test_format_multiple_emails_adds_header_banner(self):
        """Each email should have a header with from, to, date, subject"""
        formatter = EmailFormatter()
        emails = [
            MockEmail(Subject="Email 1", SenderEmailAddress="alice@test.com", To="bob@test.com", SentOn="2025-01-15"),
            MockEmail(Subject="Email 2", SenderEmailAddress="charlie@test.com", To="dave@test.com", SentOn="2025-01-16"),
        ]

        html = formatter.format_multiple_emails(emails)

        assert "Email 1" in html
        assert "Email 2" in html
        assert "alice@test.com" in html
        assert "bob@test.com" in html

    def test_format_multiple_emails_has_page_breaks(self):
        """Each email should have a page break after it"""
        formatter = EmailFormatter()
        emails = [
            MockEmail(Subject="Email 1"),
            MockEmail(Subject="Email 2"),
            MockEmail(Subject="Email 3"),
        ]

        html = formatter.format_multiple_emails(emails)

        assert "page-break-after: always" in html

    def test_format_multiple_emails_chronological_order(self):
        """Emails should appear in chronological order (oldest first)"""
        formatter = EmailFormatter()
        emails = [
            MockEmail(Subject="Third", SentOn="2025-03-01"),
            MockEmail(Subject="First", SentOn="2025-01-01"),
            MockEmail(Subject="Second", SentOn="2025-02-01"),
        ]

        html = formatter.format_multiple_emails(emails)

        first_pos = html.find("First")
        second_pos = html.find("Second")
        third_pos = html.find("Third")
        assert first_pos < second_pos < third_pos