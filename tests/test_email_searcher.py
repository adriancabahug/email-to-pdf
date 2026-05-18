"""
Tests for EmailSearcher with pluggable FolderStrategy.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from src.email_searcher import (
    EmailSearcher,
    _collect,
    _DeepPredicate,
    _FastPredicate,
    _recurse,
)


class FakeFolder:
    def __init__(self, name: str, children=None):
        self.Name = name
        self.Folders = children or []
        self.Items = MagicMock()


class TestFolderStrategies:
    def test_fast_predicate_skips_junk(self):
        p = _FastPredicate()
        assert p("Inbox") is True
        assert p("Deleted Items") is False
        assert p("Junk Email") is False

    def test_deep_predicate_is_permissive(self):
        p = _DeepPredicate()
        assert p("Inbox") is True
        assert p("RSS Feeds") is False
        assert p("Deleted Items") is True  # deep searches deleted too


class TestCollectRecurse:
    def test_collect_with_fast_strategy(self):
        root = FakeFolder("Root", [
            FakeFolder("Inbox"),
            FakeFolder("Deleted Items"),
            FakeFolder("Junk Email"),
        ])
        result = _collect(root, _FastPredicate())
        names = [f.Name for f in result]
        assert "Inbox" in names
        assert "Deleted Items" not in names

    def test_deep_recursion(self):
        root = FakeFolder("Root", [
            FakeFolder("Level1", [
                FakeFolder("Level2", [
                    FakeFolder("Inbox"),
                ])
            ])
        ])
        result = _collect(root, _DeepPredicate())
        assert len(result) == 4  # Root, Level1, Level2, Inbox


class TestEmailSearcher:
    def test_search_fast_mode(self):
        mock_items = MagicMock()
        mock_items.Restrict.return_value = []
        mock_folder = MagicMock()
        mock_folder.Name = "Inbox"
        mock_folder.Items = mock_items
        mock_folder.Folders = []

        mock_ns = MagicMock()
        mock_ns.Folders = [mock_folder]

        mock_session = MagicMock()
        mock_session.get_namespace.return_value = mock_ns

        searcher = EmailSearcher(mock_session)
        result = searcher.search("alice@example.com", mode="fast")
        assert result == []
        mock_items.Restrict.assert_called_once()

    def test_phase2_validate_matches_sender(self):
        mock_session = MagicMock()
        searcher = EmailSearcher(mock_session)
        mail = MagicMock()
        mail.SenderEmailAddress = "alice@example.com"
        mail.To = ""
        mail.CC = ""
        assert searcher._phase2_validate(mail, "alice@example.com") is True

    def test_phase2_validate_no_match(self):
        mock_session = MagicMock()
        searcher = EmailSearcher(mock_session)
        mail = MagicMock()
        mail.SenderEmailAddress = "bob@example.com"
        mail.To = ""
        mail.CC = ""
        assert searcher._phase2_validate(mail, "alice@example.com") is False

    def test_date_cutoff_applied(self):
        mock_session = MagicMock()
        searcher = EmailSearcher(mock_session)
        assert searcher._date_cutoff < datetime.now()
        assert searcher._date_cutoff > datetime.now() - timedelta(days=366)