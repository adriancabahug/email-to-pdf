"""
Tests for EmailSearcher with pluggable FolderStrategy.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from src.email_searcher import (
    EmailSearcher,
)
from src.folder_strategies import (
    FastFolderStrategy as _FastFolderStrategy,
    DeepFolderStrategy as _DeepFolderStrategy,
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

    def test_search_raises_if_no_session(self):
        searcher = EmailSearcher()
        with pytest.raises(RuntimeError, match="No session manager"):
            searcher.search(["test@example.com"], datetime(2025, 1, 1), datetime(2025, 12, 31))

    def test_search_accepts_search_terms_and_date_range(self):
        mock_session = MagicMock()
        mock_session.get_all_accounts.return_value = []
        searcher = EmailSearcher(session_manager=mock_session)
        result = searcher.search(
            search_terms=["alice@example.com", "bob@example.com"],
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2025, 12, 31)
        )
        assert result == []

    