import pytest
from unittest.mock import MagicMock, patch

from src.email_searcher import EmailSearcher
from src.outlook_session_manager import OutlookSessionManager


class TestEmailSearcherInjection:
    """Test that EmailSearcher accepts the constructor parameters"""

    def test_email_searcher_accepts_session_manager(self):
        """EmailSearcher should accept session_manager as optional constructor parameter"""
        mock_session = MagicMock(spec=OutlookSessionManager)
        searcher = EmailSearcher(session_manager=mock_session)
        assert searcher._session is mock_session

    def test_email_searcher_accepts_processed_store(self):
        """EmailSearcher should accept processed_store as optional constructor parameter"""
        mock_store = MagicMock()
        searcher = EmailSearcher(processed_store=mock_store)
        assert searcher._processed_store is mock_store

    def test_email_searcher_accepts_config_manager(self):
        """EmailSearcher should accept config_manager as optional constructor parameter"""
        mock_config = MagicMock()
        searcher = EmailSearcher(config_manager=mock_config)
        assert searcher._config is mock_config

    def test_email_searcher_can_be_instantiated_with_defaults(self):
        """EmailSearcher should be instantiable with no arguments"""
        searcher = EmailSearcher()
        assert searcher._session is None
        assert searcher._processed_store is None
        assert searcher._config is None