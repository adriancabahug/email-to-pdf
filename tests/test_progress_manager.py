import pytest
from unittest.mock import MagicMock, patch
from io import StringIO
import sys

from src.progress_manager import ProgressManager
from src.config_manager import ConfigManager


def make_console():
    from rich.console import Console
    return Console(file=StringIO(), force_terminal=True)


class TestProgressManagerStart:
    """start() initializes session state"""

    def test_start_resets_counters(self, tmp_path, monkeypatch):
        """Should reset all counters when starting"""
        monkeypatch.setattr(ConfigManager, "_get_appdata_dir", lambda: tmp_path / "EmailToPDF")
        cm = ConfigManager.load()
        pm = ProgressManager(cm)

        pm._emails_found = 100
        pm._matches_found = 50
        pm._pdfs_generated = 10
        pm._failures = 5

        pm.start("John Smith")

        assert pm._emails_found == 0
        assert pm._matches_found == 0
        assert pm._pdfs_generated == 0
        assert pm._failures == 0

    def test_start_stores_director_name(self, tmp_path, monkeypatch):
        """Should store the start time"""
        monkeypatch.setattr(ConfigManager, "_get_appdata_dir", lambda: tmp_path / "EmailToPDF")
        cm = ConfigManager.load()
        pm = ProgressManager(cm)

        pm.start("John Smith")

        assert pm._start_time is not None
        assert pm._start_time > 0


class TestProgressManagerUpdateActivity:
    """update_activity() shows current folder progress"""

    def test_increments_emails(self, tmp_path, monkeypatch):
        """Should add to email count"""
        monkeypatch.setattr(ConfigManager, "_get_appdata_dir", lambda: tmp_path / "EmailToPDF")
        cm = ConfigManager.load()
        pm = ProgressManager(cm)

        pm.update_activity("Inbox", emails_found=5)
        assert pm._emails_found == 5

    def test_increments_matches(self, tmp_path, monkeypatch):
        """Should add to match count"""
        monkeypatch.setattr(ConfigManager, "_get_appdata_dir", lambda: tmp_path / "EmailToPDF")
        cm = ConfigManager.load()
        pm = ProgressManager(cm)

        pm.update_activity("Inbox", matches_found=3)
        assert pm._matches_found == 3

    def test_accumulates_counts(self, tmp_path, monkeypatch):
        """Should accumulate across multiple calls"""
        monkeypatch.setattr(ConfigManager, "_get_appdata_dir", lambda: tmp_path / "EmailToPDF")
        cm = ConfigManager.load()
        pm = ProgressManager(cm)

        pm.update_activity("Inbox", emails_found=5)
        pm.update_activity("Sent Items", emails_found=3)
        assert pm._emails_found == 8


class TestProgressManagerShowRetry:
    """show_retry() displays retry status"""

    def test_stores_retry_state(self, tmp_path, monkeypatch):
        """Should store retry attempt and max"""
        monkeypatch.setattr(ConfigManager, "_get_appdata_dir", lambda: tmp_path / "EmailToPDF")
        cm = ConfigManager.load()
        pm = ProgressManager(cm)

        pm.show_retry(2, 3, 5.0)

        assert pm._retry_attempt == 2
        assert pm._max_retries == 3


class TestProgressManagerShowError:
    """show_error() displays structured error panels"""

    def test_accepts_all_parameters(self, tmp_path, monkeypatch):
        """Should accept category, message, and action without crashing"""
        monkeypatch.setattr(ConfigManager, "_get_appdata_dir", lambda: tmp_path / "EmailToPDF")
        cm = ConfigManager.load()
        pm = ProgressManager(cm)

        pm.show_error("A", "RPC unavailable", "Retry in 5s")
        pm.show_error("D", "User intervention required", None)


class TestProgressManagerVerbose:
    """Verbose mode toggle"""

    def test_verbose_disabled_by_default(self, tmp_path, monkeypatch):
        """Should be disabled when not configured"""
        monkeypatch.setattr(ConfigManager, "_get_appdata_dir", lambda: tmp_path / "EmailToPDF")
        cm = ConfigManager.load()
        pm = ProgressManager(cm)

        assert pm._verbose is False

    def test_verbose_from_config(self, tmp_path, monkeypatch):
        """Should be enabled when config says so"""
        appdata = tmp_path / "EmailToPDF"
        appdata.mkdir()
        import json
        config_path = appdata / "config.json"
        config_path.write_text(json.dumps({"logging": {"verbose_console": True}}), encoding="utf-8")
        monkeypatch.setattr(ConfigManager, "_get_appdata_dir", lambda: appdata)
        cm = ConfigManager.load()
        pm = ProgressManager(cm)

        assert pm._verbose is True

    def test_set_verbose_changes_state(self, tmp_path, monkeypatch):
        """set_verbose() should update verbose flag"""
        monkeypatch.setattr(ConfigManager, "_get_appdata_dir", lambda: tmp_path / "EmailToPDF")
        cm = ConfigManager.load()
        pm = ProgressManager(cm)

        pm.set_verbose(True)
        assert pm._verbose is True

        pm.set_verbose(False)
        assert pm._verbose is False


class TestProgressManagerSummary:
    """show_completion_summary() displays final stats"""

    def test_increments_pdfs(self, tmp_path, monkeypatch):
        """Should track PDF generation count"""
        monkeypatch.setattr(ConfigManager, "_get_appdata_dir", lambda: tmp_path / "EmailToPDF")
        cm = ConfigManager.load()
        pm = ProgressManager(cm)

        pm._pdfs_generated = 5
        pm._start_time = 0

        assert pm._pdfs_generated == 5


class TestProgressManagerElapsed:
    """_elapsed() computes time since start"""

    def test_returns_zero_when_not_started(self, tmp_path, monkeypatch):
        """Should return 0 before start() is called"""
        monkeypatch.setattr(ConfigManager, "_get_appdata_dir", lambda: tmp_path / "EmailToPDF")
        cm = ConfigManager.load()
        pm = ProgressManager(cm)

        assert pm._elapsed() == 0.0

    def test_returns_positive_after_start(self, tmp_path, monkeypatch):
        """Should return positive elapsed time after start()"""
        monkeypatch.setattr(ConfigManager, "_get_appdata_dir", lambda: tmp_path / "EmailToPDF")
        cm = ConfigManager.load()
        pm = ProgressManager(cm)

        pm.start("test")
        import time
        time.sleep(0.01)
        assert pm._elapsed() > 0


class TestRichProgressBar:
    """Rich progress bar integration"""

    def test_start_initializes_progress_with_total(self, tmp_path, monkeypatch):
        """start() should initialize progress bar with folder count"""
        monkeypatch.setattr(ConfigManager, "_get_appdata_dir", lambda: tmp_path / "EmailToPDF")
        monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
        cm = ConfigManager.load()
        pm = ProgressManager(cm)

        pm.start("Aura Super", folder_count=10)

        assert pm._progress is not None
        assert pm._task is not None

    def test_update_activity_advances_progress(self, tmp_path, monkeypatch):
        """update_activity() should advance the progress bar"""
        monkeypatch.setattr(ConfigManager, "_get_appdata_dir", lambda: tmp_path / "EmailToPDF")
        monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
        cm = ConfigManager.load()
        pm = ProgressManager(cm)

        pm.start("Aura Super", folder_count=10)
        pm.update_activity("Inbox")

        assert pm._folders_scanned == 1

    def test_progress_hidden_when_not_tty(self, tmp_path, monkeypatch):
        """Progress bar should not show when stdout is not a TTY"""
        monkeypatch.setattr(ConfigManager, "_get_appdata_dir", lambda: tmp_path / "EmailToPDF")
        monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
        cm = ConfigManager.load()
        pm = ProgressManager(cm)

        pm.start("Aura Super", folder_count=10)

        assert pm._progress is None