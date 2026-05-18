import pytest
from unittest.mock import MagicMock, patch

from src.email_searcher import EmailSearcher
from src.outlook_session_manager import OutlookSessionManager
from src.folder_resolver import FolderResolver


class TestContactRegistryInjection:
    """Test that EmailSearcher accepts the new constructor parameters"""

    def test_email_searcher_accepts_session_manager(self, tmp_path, monkeypatch):
        """EmailSearcher should accept session_manager as optional constructor parameter"""
        from src.config_manager import ConfigManager
        appdata = tmp_path / "EmailToPDF"
        appdata.mkdir()
        monkeypatch.setattr(ConfigManager, "_get_appdata_dir", lambda: appdata)
        cm = ConfigManager.load()

        mock_session = MagicMock(spec=OutlookSessionManager)
        searcher = EmailSearcher(session_manager=mock_session)
        assert searcher._session is mock_session

    def test_email_searcher_accepts_folder_resolver(self, tmp_path, monkeypatch):
        """EmailSearcher should accept folder_resolver as optional constructor parameter"""
        from src.config_manager import ConfigManager
        appdata = tmp_path / "EmailToPDF"
        appdata.mkdir()
        monkeypatch.setattr(ConfigManager, "_get_appdata_dir", lambda: appdata)
        cm = ConfigManager.load()

        mock_session = MagicMock(spec=OutlookSessionManager)
        mock_resolver = MagicMock(spec=FolderResolver)
        searcher = EmailSearcher(session_manager=mock_session, folder_resolver=mock_resolver)
        assert searcher._folder_resolver is mock_resolver

    def test_email_searcher_uses_new_interface(self, tmp_path, monkeypatch):
        """EmailSearcher should use new constructor: session_manager, folder_resolver, processed_store, config_manager"""
        from src.config_manager import ConfigManager
        appdata = tmp_path / "EmailToPDF"
        appdata.mkdir()
        monkeypatch.setattr(ConfigManager, "_get_appdata_dir", lambda: appdata)
        cm = ConfigManager.load()

        mock_session = MagicMock()
        mock_resolver = MagicMock()
        mock_store = MagicMock()
        searcher = EmailSearcher(
            session_manager=mock_session,
            folder_resolver=mock_resolver,
            processed_store=mock_store,
            config_manager=cm
        )
        assert searcher._session is mock_session
        assert searcher._folder_resolver is mock_resolver
        assert searcher._processed_store is mock_store
        assert searcher._config is cm

    def test_email_searcher_can_be_instantiated_with_defaults(self):
        """EmailSearcher should be instantiable with no arguments"""
        searcher = EmailSearcher()
        assert searcher._session is None
        assert searcher._folder_resolver is None