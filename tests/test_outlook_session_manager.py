import pytest
from unittest.mock import Mock, patch, MagicMock

from src.outlook_session_manager import OutlookSessionManager


class TestOutlookSessionManagerConnect:
    """connect() and disconnect()"""

    @patch("win32com.client.Dispatch")
    def test_connect_establishes_session(self, mock_dispatch):
        """Should connect to Outlook and set _connected=True"""
        mock_app = MagicMock()
        mock_namespace = MagicMock()
        mock_app.GetNamespace.return_value = mock_namespace
        mock_dispatch.return_value = mock_app

        sm = OutlookSessionManager()
        result = sm.connect()

        assert result is True
        assert sm.is_connected() is True

    @patch("win32com.client.Dispatch")
    def test_connect_returns_false_on_failure(self, mock_dispatch):
        """Should return False when Outlook is unavailable"""
        mock_dispatch.side_effect = Exception("RPC unavailable")

        sm = OutlookSessionManager()
        result = sm.connect()

        assert result is False
        assert sm.is_connected() is False

    @patch("win32com.client.Dispatch")
    def test_disconnect_clears_session(self, mock_dispatch):
        """Should clear COM references on disconnect"""
        mock_app = MagicMock()
        mock_namespace = MagicMock()
        mock_app.GetNamespace.return_value = mock_namespace
        mock_dispatch.return_value = mock_app

        sm = OutlookSessionManager()
        sm.connect()
        sm.disconnect()

        assert sm.is_connected() is False


class TestOutlookSessionManagerWrap:
    """wrap() retry and backoff logic"""

    @patch("win32com.client.Dispatch")
    def test_successful_call_returns_immediately(self, mock_dispatch):
        """Should not retry when call succeeds"""
        mock_app = MagicMock()
        mock_namespace = MagicMock()
        mock_app.GetNamespace.return_value = mock_namespace
        mock_dispatch.return_value = mock_app

        sm = OutlookSessionManager()
        sm.connect()

        result = sm.wrap(lambda: 42)
        assert result == 42

    @patch("win32com.client.Dispatch")
    def test_transient_error_triggers_retry(self, mock_dispatch):
        """Should retry on transient exception"""
        mock_app = MagicMock()
        mock_namespace = MagicMock()
        mock_app.GetNamespace.return_value = mock_namespace
        mock_dispatch.return_value = mock_app

        sm = OutlookSessionManager()
        sm.connect()

        call_count = [0]

        def flaky():
            call_count[0] += 1
            if call_count[0] < 3:
                raise Exception("RPC server unavailable")
            return "success"

        with patch("time.sleep"):
            result = sm.wrap(flaky)

        assert result == "success"
        assert call_count[0] == 3

    @patch("win32com.client.Dispatch")
    def test_max_retries_exceeded_raises_error(self, mock_dispatch):
        """Should raise after exhausting retries and escalation fails"""
        mock_app = MagicMock()
        mock_namespace = MagicMock()
        mock_app.GetNamespace.return_value = mock_namespace
        mock_dispatch.return_value = mock_app

        sm = OutlookSessionManager()
        sm.connect()
        sm._restart_count = 2

        with patch("time.sleep"):
            with pytest.raises(RuntimeError, match="user intervention"):
                sm.wrap(lambda: (_ for _ in ()).throw(Exception("RPC")))

    @patch("win32com.client.Dispatch")
    def test_exponential_backoff_delay(self, mock_dispatch):
        """Should use exponential backoff between retries"""
        mock_app = MagicMock()
        mock_namespace = MagicMock()
        mock_app.GetNamespace.return_value = mock_namespace
        mock_dispatch.return_value = mock_app

        sm = OutlookSessionManager()
        sm.connect()

        delays = []

        def record_sleep(delay):
            delays.append(delay)

        call_count = [0]

        def flaky():
            call_count[0] += 1
            if call_count[0] < 3:
                raise Exception("RPC server unavailable")
            return "success"

        with patch("time.sleep", side_effect=record_sleep):
            sm.wrap(flaky)

        assert len(delays) == 2
        assert delays[0] > 0
        assert delays[1] > delays[0]


class TestOutlookSessionManagerEscalation:
    """Category B/C escalation after retry exhaustion"""

    @patch("win32com.client.Dispatch")
    def test_outlook_not_running_launches_outlook(self, mock_dispatch):
        """Should launch Outlook when process is not detected"""
        mock_app = MagicMock()
        mock_namespace = MagicMock()
        mock_app.GetNamespace.return_value = mock_namespace
        mock_dispatch.return_value = mock_app

        sm = OutlookSessionManager()
        sm.connect()

        call_count = [0]

        def flaky():
            call_count[0] += 1
            if call_count[0] <= 3:
                raise Exception("RPC")
            return "success_after_restart"

        with patch.object(sm, "_get_outlook_processes", return_value=[]):
            with patch.object(sm, "_launch_outlook") as mock_launch:
                with patch("time.sleep"):
                    result = sm.wrap(flaky)
                    mock_launch.assert_called()
                    assert result == "success_after_restart"

    @patch("win32com.client.Dispatch")
    def test_outlook_unresponsive_terminates_and_restarts(self, mock_dispatch):
        """Should terminate and relaunch when unresponsive"""
        mock_app = MagicMock()
        mock_namespace = MagicMock()
        mock_app.GetNamespace.return_value = mock_namespace
        mock_dispatch.return_value = mock_app

        sm = OutlookSessionManager()
        sm.connect()

        call_count = [0]

        def flaky():
            call_count[0] += 1
            if call_count[0] <= 3:
                raise Exception("RPC")
            return "success_after_restart"

        with patch.object(sm, "_get_outlook_processes", return_value=[MagicMock()]):
            with patch.object(sm, "_is_unresponsive", return_value=True):
                with patch.object(sm, "_terminate_and_launch") as mock_restart:
                    with patch("time.sleep"):
                        result = sm.wrap(flaky)
                        mock_restart.assert_called()
                        assert result == "success_after_restart"

    @patch("win32com.client.Dispatch")
    def test_max_restarts_enforced(self, mock_dispatch):
        """Should raise Category D after max restart attempts"""
        mock_app = MagicMock()
        mock_namespace = MagicMock()
        mock_app.GetNamespace.return_value = mock_namespace
        mock_dispatch.return_value = mock_app

        sm = OutlookSessionManager()
        sm.connect()

        sm._restart_count = 2

        with pytest.raises(RuntimeError, match="user intervention"):
            sm._escalate(2)


class TestOutlookSessionManagerHealthy:
    """is_healthy()"""

    @patch("win32com.client.Dispatch")
    def test_healthy_returns_true_when_connected(self, mock_dispatch):
        """Should return True when namespace is accessible"""
        mock_app = MagicMock()
        mock_namespace = MagicMock()
        mock_namespace.Folders.Count = 1
        mock_app.GetNamespace.return_value = mock_namespace
        mock_dispatch.return_value = mock_app

        sm = OutlookSessionManager()
        sm.connect()

        assert sm.is_healthy() is True

    @patch("win32com.client.Dispatch")
    def test_healthy_returns_false_when_not_connected(self, mock_dispatch):
        """Should return False when not connected"""
        sm = OutlookSessionManager()

        assert sm.is_healthy() is False


class TestOutlookSessionManagerGetAccounts:
    """get_all_accounts() via wrap"""

    @patch("win32com.client.Dispatch")
    def test_get_all_accounts_returns_folders(self, mock_dispatch):
        """Should return namespace folders as accounts"""
        mock_app = MagicMock()
        mock_namespace = MagicMock()

        folder1 = MagicMock()
        folder1.Name = "Account1"
        folder2 = MagicMock()
        folder2.Name = "Account2"
        mock_namespace.Folders = [folder1, folder2]
        mock_app.GetNamespace.return_value = mock_namespace
        mock_dispatch.return_value = mock_app

        sm = OutlookSessionManager()
        sm.connect()

        accounts = sm.get_all_accounts()
        assert len(accounts) == 2


class TestOutlookSessionManagerIsConnected:
    """is_connected() helper"""

    @patch("win32com.client.Dispatch")
    def test_is_connected_returns_state(self, mock_dispatch):
        """Should return _connected flag value"""
        mock_app = MagicMock()
        mock_namespace = MagicMock()
        mock_app.GetNamespace.return_value = mock_namespace
        mock_dispatch.return_value = mock_app

        sm = OutlookSessionManager()
        assert sm.is_connected() is False

        sm.connect()
        assert sm.is_connected() is True


class TestOutlookSessionManagerGetDefaultFolder:
    """get_inbox_folder() and get_sent_items_folder()"""

    @patch("win32com.client.Dispatch")
    def test_get_inbox_folder_returns_default_inbox(self, mock_dispatch):
        """Should return the default Inbox folder"""
        mock_app = MagicMock()
        mock_namespace = MagicMock()
        mock_inbox = MagicMock()
        mock_namespace.GetDefaultFolder.return_value = mock_inbox
        mock_app.GetNamespace.return_value = mock_namespace
        mock_dispatch.return_value = mock_app

        sm = OutlookSessionManager()
        sm.connect()

        inbox = sm.get_inbox_folder()
        mock_namespace.GetDefaultFolder.assert_called_with(6)
        assert inbox == mock_inbox

    @patch("win32com.client.Dispatch")
    def test_get_sent_items_folder_returns_default_sent(self, mock_dispatch):
        """Should return the default Sent Items folder"""
        mock_app = MagicMock()
        mock_namespace = MagicMock()
        mock_sent = MagicMock()
        mock_namespace.GetDefaultFolder.return_value = mock_sent
        mock_app.GetNamespace.return_value = mock_namespace
        mock_dispatch.return_value = mock_app

        sm = OutlookSessionManager()
        sm.connect()

        sent = sm.get_sent_items_folder()
        mock_namespace.GetDefaultFolder.assert_called_with(5)
        assert sent == mock_sent

    @patch("win32com.client.Dispatch")
    def test_get_inbox_folder_with_account_email(self, mock_dispatch):
        """Should return inbox for specific account when email provided"""
        mock_app = MagicMock()
        mock_namespace = MagicMock()

        store1 = MagicMock()
        store1.Name = "work@example.com"
        store1_folders = MagicMock()
        store1.Folders = store1_folders
        store1_inbox = MagicMock()
        store1_folders.Item.return_value = store1_inbox

        store2 = MagicMock()
        store2.Name = "personal@example.com"

        mock_namespace.Folders = [store1, store2]
        mock_app.GetNamespace.return_value = mock_namespace
        mock_dispatch.return_value = mock_app

        sm = OutlookSessionManager()
        sm.connect()

        inbox = sm.get_inbox_folder("work@example.com")
        store1_folders.Item.assert_called_with(6)
        assert inbox == store1_inbox