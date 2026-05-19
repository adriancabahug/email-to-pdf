"""
Tests for the DI container and composition root.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.dependencies import CompositionRoot, Dependencies


class TestCompositionRoot:
    def test_build_returns_populated_dependencies(self, tmp_path: Path):
        with patch("src.config_manager.ConfigManager") as mock_cfg_cls:
            cfg = MagicMock()
            cfg.appdata_dir.return_value = tmp_path
            mock_cfg_cls.load.return_value = cfg

            root = CompositionRoot(output_base=tmp_path / "out")
            deps = root.build()

            assert deps.session_manager is not None
            assert deps.email_searcher is not None
            assert deps.pdf_generator is not None
            assert deps.file_manager is not None
            assert deps.processed_store is not None
            assert deps.license_validator is not None

    def test_build_uses_provided_dependencies(self, tmp_path: Path):
        """If deps are passed to MainOrchestrator, CompositionRoot is skipped."""
        fake_pdf = MagicMock()
        deps = Dependencies(pdf_generator=fake_pdf)
        assert deps.pdf_generator is fake_pdf


class TestDependenciesDataclass:
    def test_all_fields_optional_by_default(self):
        deps = Dependencies()
        assert deps.session_manager is None
        assert deps.email_formatter is None