import pytest
from unittest.mock import MagicMock, patch

from src.outlook_session_manager import OutlookSessionManager
from src.email_searcher import EmailSearcher


class TestGetAllAccounts:
    """Test get_all_accounts() - returns all MAPI folders representing accounts"""

    @patch('win32com.client.Dispatch')
    def test_get_all_accounts_returns_list_of_folders(self, mock_dispatch):
        """Should return a list of account folders from namespace.Folders"""
        mock_app = MagicMock()
        mock_namespace = MagicMock()

        mock_account1 = MagicMock()
        mock_account1.Name = "Work Account"
        mock_account2 = MagicMock()
        mock_account2.Name = "Personal Account"

        mock_namespace.Folders = [mock_account1, mock_account2]
        mock_app.GetNamespace.return_value = mock_namespace
        mock_dispatch.return_value = mock_app

        sm = OutlookSessionManager()
        sm.connect()

        accounts = sm.get_all_accounts()

        assert len(accounts) == 2
        assert accounts[0].Name == "Work Account"
        assert accounts[1].Name == "Personal Account"

    @patch('win32com.client.Dispatch')
    def test_get_all_accounts_returns_empty_list_when_no_accounts(self, mock_dispatch):
        """Should return empty list when no accounts found"""
        mock_app = MagicMock()
        mock_namespace = MagicMock()
        mock_namespace.Folders = []

        mock_app.GetNamespace.return_value = mock_namespace
        mock_dispatch.return_value = mock_app

        sm = OutlookSessionManager()
        sm.connect()

        accounts = sm.get_all_accounts()

        assert accounts == []


class TestGetAllFoldersRecursive:
    """Test get_all_folders_recursive() - recursively traverses all subfolders"""

    def test_get_all_folders_returns_immediate_folders(self):
        """Should return immediate child folders of root folder"""
        mock_folder = MagicMock()
        mock_folder.Name = "Inbox"

        mock_subfolder1 = MagicMock()
        mock_subfolder1.Name = "Subfolder1"
        mock_subfolder1.Folders = []

        mock_subfolder2 = MagicMock()
        mock_subfolder2.Name = "Subfolder2"
        mock_subfolder2_sub = MagicMock()
        mock_subfolder2_sub.Name = "Nested"
        mock_subfolder2_sub.Folders = []
        mock_subfolder2.Folders = [mock_subfolder2_sub]

        mock_folder.Folders = [mock_subfolder1, mock_subfolder2]

        sm = OutlookSessionManager()
        folders = sm.get_all_folders_recursive(mock_folder)

        folder_names = [f.Name for f in folders]
        assert "Subfolder1" in folder_names
        assert "Subfolder2" in folder_names
        assert "Nested" in folder_names


class TestDiscoverEmailAllAccounts:
    """Test discover_email_from_name() searches ALL accounts and folders"""

    @patch('win32com.client.Dispatch')
    def test_discover_searches_all_accounts(self, mock_dispatch):
        """Should search emails in all accounts, not just default"""
        mock_app = MagicMock()
        mock_namespace = MagicMock()

        mock_account1 = MagicMock()
        mock_account1.Name = "Work Account"
        mock_folder1 = MagicMock()
        mock_folder1.Name = "Inbox"

        mock_email1 = MagicMock()
        mock_email1.SenderName = "Mari Acapulco"
        mock_email1.SenderEmailAddress = "mari@eastcoastinc.com.au"
        mock_folder1.Items = [mock_email1]

        mock_account1.Folders = [mock_folder1]

        mock_account2 = MagicMock()
        mock_account2.Name = "Personal"
        mock_folder2 = MagicMock()
        mock_folder2.Name = "Inbox"
        mock_email2 = MagicMock()
        mock_email2.SenderName = "Other Person"
        mock_email2.SenderEmailAddress = "other@email.com"
        mock_folder2.Items = [mock_email2]

        mock_account2.Folders = [mock_folder2]

        mock_namespace.Folders = [mock_account1, mock_account2]
        mock_app.GetNamespace.return_value = mock_namespace
        mock_dispatch.return_value = mock_app

        sm = OutlookSessionManager()
        sm.connect()

        email = sm.discover_email_from_name("Mari", "Acapulco")

        assert email == "mari@eastcoastinc.com.au"

    @patch('win32com.client.Dispatch')
    def test_discover_searches_subfolders(self, mock_dispatch):
        """Should also search subfolders within accounts"""
        mock_app = MagicMock()
        mock_namespace = MagicMock()

        mock_account = MagicMock()
        mock_account.Name = "Work"

        mock_inbox = MagicMock()
        mock_inbox.Name = "Inbox"
        mock_inbox.Items = []

        mock_archived = MagicMock()
        mock_archived.Name = "Archived"
        mock_email = MagicMock()
        mock_email.SenderName = "Mari Acapulco"
        mock_email.SenderEmailAddress = "mari@test.com"
        mock_archived.Items = [mock_email]

        mock_account.Folders = [mock_inbox, mock_archived]
        mock_namespace.Folders = [mock_account]
        mock_app.GetNamespace.return_value = mock_namespace
        mock_dispatch.return_value = mock_app

        sm = OutlookSessionManager()
        sm.connect()

        email = sm.discover_email_from_name("Mari", "Acapulco")

        assert email == "mari@test.com"


class TestEmailSearcherNewInterface:
    """Test EmailSearcher.search() with the new session_manager interface"""

    def test_search_requires_session_manager(self):
        """search() should raise if no session_manager provided"""
        searcher = EmailSearcher()
        with pytest.raises(RuntimeError, match="session manager"):
            searcher.search("test@email.com")

    