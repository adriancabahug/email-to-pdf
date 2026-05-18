"""
Tests for unified FolderResolver recursion.
"""

import pytest

from src.folder_resolver import (
    FolderResolver,
    _DeepPredicate,
    _FastPredicate,
)


class FakeFolder:
    def __init__(self, name: str, children=None):
        self.Name = name
        self.Folders = children or []


class TestFastFolders:
    def test_includes_inbox(self):
        root = FakeFolder("Root", [FakeFolder("Inbox"), FakeFolder("Deleted Items")])
        result = FolderResolver.get_fast_folders(root)
        names = [f.Name for f in result]
        assert "Inbox" in names
        assert "Deleted Items" not in names

    def test_recursive_fast(self):
        root = FakeFolder("Root", [
            FakeFolder("Inbox", [FakeFolder("Subfolder")]),
            FakeFolder("Junk Email"),
        ])
        result = FolderResolver.get_fast_folders(root)
        names = [f.Name for f in result]
        assert "Subfolder" in names
        assert "Junk Email" not in names


class TestDeepFolders:
    def test_includes_deleted(self):
        root = FakeFolder("Root", [FakeFolder("Inbox"), FakeFolder("Deleted Items")])
        result = FolderResolver.get_deep_folders(root)
        names = [f.Name for f in result]
        assert "Deleted Items" in names

    def test_skips_rss(self):
        root = FakeFolder("Root", [FakeFolder("RSS Feeds")])
        result = FolderResolver.get_deep_folders(root)
        names = [f.Name for f in result]
        assert "RSS Feeds" not in names


class TestShouldSkipFolder:
    def test_fast_skip(self):
        assert FolderResolver.should_skip_folder("RSS Feeds") is True
        assert FolderResolver.should_skip_folder("Inbox") is False