import pytest
from unittest.mock import MagicMock

from src.email_searcher import EmailSearcher


class MockEmail:
    def __init__(self, sender_email, to_recipients, cc_recipients):
        self.SenderEmailAddress = sender_email
        self.To = to_recipients
        self.CC = cc_recipients
        self.Subject = "Test"
        self.Body = "Test body"
        self.SentOn = "2025-01-15"


class TestDirectorOnlyMatching:
    """Test that Phase 2 validation matches director in From/To/CC"""

    def test_finds_email_where_director_is_sender(self):
        """Should find email where director is the sender (From)"""
        searcher = EmailSearcher()
        email = MockEmail(
            sender_email="mari@eastcoastinc.com.au",
            to_recipients="onedreyan@outlook.com",
            cc_recipients=""
        )
        result = searcher._phase2_validate(email, "mari@eastcoastinc.com.au")
        assert result is True

    def test_finds_email_where_director_is_recipient(self):
        """Should find email where director is the recipient (To)"""
        searcher = EmailSearcher()
        email = MockEmail(
            sender_email="onedreyan@outlook.com",
            to_recipients="mari@eastcoastinc.com.au",
            cc_recipients=""
        )
        result = searcher._phase2_validate(email, "mari@eastcoastinc.com.au")
        assert result is True

    def test_finds_email_where_director_is_cc(self):
        """Should find email where director is CC'd"""
        searcher = EmailSearcher()
        email = MockEmail(
            sender_email="onedreyan@outlook.com",
            to_recipients="tanesha@accounting.com",
            cc_recipients="mari@eastcoastinc.com.au"
        )
        result = searcher._phase2_validate(email, "mari@eastcoastinc.com.au")
        assert result is True

    def test_does_not_find_email_without_director(self):
        """Should NOT find email where director is not involved"""
        searcher = EmailSearcher()
        email = MockEmail(
            sender_email="other@company.com",
            to_recipients="someone@other.com",
            cc_recipients=""
        )
        result = searcher._phase2_validate(email, "mari@eastcoastinc.com.au")
        assert result is False

    def test_finds_email_case_insensitive(self):
        """Should find director email regardless of case"""
        searcher = EmailSearcher()
        email = MockEmail(
            sender_email="MARI@eastcoastinc.com.au",
            to_recipients="onedreyan@outlook.com",
            cc_recipients=""
        )
        result = searcher._phase2_validate(email, "mari@eastcoastinc.com.au")
        assert result is True