"""
Tests for EmailSearcher with pluggable FolderStrategy.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from src.email_searcher import (
    EmailSearcher,
    _FastFolderStrategy,
    _DeepFolderStrategy,
)


class FakeFolder:
    def __init__(self, name: str, children=None):
        self.Name = name
        self.Folders = children or []
        self.Items = MagicMock()


class TestFolderStrategies:
    def test_fast_strategy_prioritizes_inbox(self):
        s = _FastFolderStrategy()
        assert s("Inbox") is True
        assert s("Sent Items") is True
        assert s("Junk Email") is False
        assert s("Deleted Items") is False

    def test_deep_strategy_is_permissive(self):
        s = _DeepFolderStrategy()
        assert s("Inbox") is True
        assert s("RSS Feeds") is False
        assert s("Deleted Items") is True


class TestEmailSearcher:
    def test_search_uses_fast_strategy_by_default(self):
        mock_session = MagicMock()
        mock_session.get_all_accounts.return_value = []
        searcher = EmailSearcher(session_manager=mock_session)
        result = searcher.search("alice@example.com")
        assert result == []

    def test_search_with_deep_mode(self):
        mock_session = MagicMock()
        mock_session.get_all_accounts.return_value = []
        searcher = EmailSearcher(session_manager=mock_session)
        result = searcher.search("alice@example.com", mode="deep")
        assert result == []

    def test_phase2_validate_matches_sender(self):
        mock_session = MagicMock()
        searcher = EmailSearcher(session_manager=mock_session)
        mail = MagicMock()
        mail.SenderEmailAddress = "alice@example.com"
        mail.To = ""
        mail.CC = ""
        assert searcher._phase2_validate(mail, "alice@example.com") is True

    def test_phase2_validate_no_match(self):
        mock_session = MagicMock()
        searcher = EmailSearcher(session_manager=mock_session)
        mail = MagicMock()
        mail.SenderEmailAddress = "bob@example.com"
        mail.To = ""
        mail.CC = ""
        assert searcher._phase2_validate(mail, "alice@example.com") is False

    def test_build_restrict_query_escapes_quotes(self):
        mock_session = MagicMock()
        searcher = EmailSearcher(session_manager=mock_session)
        query = searcher._build_restrict_query("test'email@example.com", None)
        assert "test''email@example.com" in query

    def test_search_raises_if_no_session(self):
        searcher = EmailSearcher()
        with pytest.raises(RuntimeError, match="No session manager"):
            searcher.search("test@example.com")