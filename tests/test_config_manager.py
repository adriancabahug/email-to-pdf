import pytest
import json
import os
import tempfile
from pathlib import Path
from src.config_manager import ConfigManager, DEFAULT_CONFIG


class TestConfigManagerLoad:
    """ConfigManager.load()"""

    def test_load_returns_config_manager_instance(self):
        """Should return a ConfigManager instance"""
        cm = ConfigManager.load()
        assert isinstance(cm, ConfigManager)

    def test_missing_config_uses_defaults(self, tmp_path, monkeypatch):
        """Should use defaults when no config.json exists"""
        appdata = tmp_path / "EmailToPDF"
        appdata.mkdir()
        monkeypatch.setattr(ConfigManager, "_get_appdata_dir", lambda: appdata)

        cm = ConfigManager.load()
        assert cm.get("timeouts.com_operation_sec") == 30
        assert cm.get("search.default_mode") == "fast"
        assert cm.get("backoff.initial_sec") == 2

    def test_loaded_config_matches_defaults(self, tmp_path, monkeypatch):
        """Should match DEFAULT_CONFIG values on first load"""
        appdata = tmp_path / "EmailToPDF"
        appdata.mkdir()
        monkeypatch.setattr(ConfigManager, "_get_appdata_dir", lambda: appdata)

        cm = ConfigManager.load()
        assert cm.get("timeouts.com_operation_sec") == DEFAULT_CONFIG["timeouts"]["com_operation_sec"]
        assert cm.get("timeouts.outlook_startup_sec") == DEFAULT_CONFIG["timeouts"]["outlook_startup_sec"]
        assert cm.get("backoff.multiplier") == DEFAULT_CONFIG["backoff"]["multiplier"]
        assert cm.get("retry.max_com_retries") == DEFAULT_CONFIG["retry"]["max_com_retries"]

    def test_generates_template_on_first_run(self, tmp_path, monkeypatch):
        """Should create config.json template on first run"""
        appdata = tmp_path / "EmailToPDF"
        appdata.mkdir()
        monkeypatch.setattr(ConfigManager, "_get_appdata_dir", lambda: appdata)

        ConfigManager.load()
        template_path = appdata / "config.json"
        assert template_path.exists()
        with open(template_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded["timeouts"]["com_operation_sec"] == 30

    def test_existing_config_overrides_defaults(self, tmp_path, monkeypatch):
        """Should merge user config over defaults"""
        appdata = tmp_path / "EmailToPDF"
        appdata.mkdir()
        config_path = appdata / "config.json"
        config_path.write_text(json.dumps({
            "timeouts": {"com_operation_sec": 60},
            "search": {"default_mode": "deep"}
        }), encoding="utf-8")
        monkeypatch.setattr(ConfigManager, "_get_appdata_dir", lambda: appdata)

        cm = ConfigManager.load()
        assert cm.get("timeouts.com_operation_sec") == 60
        assert cm.get("search.default_mode") == "deep"
        assert cm.get("backoff.initial_sec") == 2

    def test_missing_keys_in_user_config_retain_defaults(self, tmp_path, monkeypatch):
        """Should use defaults for keys not in user config"""
        appdata = tmp_path / "EmailToPDF"
        appdata.mkdir()
        config_path = appdata / "config.json"
        config_path.write_text(json.dumps({
            "timeouts": {"com_operation_sec": 45}
        }), encoding="utf-8")
        monkeypatch.setattr(ConfigManager, "_get_appdata_dir", lambda: appdata)

        cm = ConfigManager.load()
        assert cm.get("timeouts.com_operation_sec") == 45
        assert cm.get("timeouts.outlook_startup_sec") == 60


class TestConfigManagerGet:
    """ConfigManager.get() dot-path access"""

    def test_get_top_level_key(self, tmp_path, monkeypatch):
        """Should get top-level key"""
        appdata = tmp_path / "EmailToPDF"
        appdata.mkdir()
        monkeypatch.setattr(ConfigManager, "_get_appdata_dir", lambda: appdata)
        cm = ConfigManager.load()
        assert cm.get("run_mode") == "interactive"

    def test_get_nested_key_single_level(self, tmp_path, monkeypatch):
        """Should get nested key one level deep"""
        appdata = tmp_path / "EmailToPDF"
        appdata.mkdir()
        monkeypatch.setattr(ConfigManager, "_get_appdata_dir", lambda: appdata)
        cm = ConfigManager.load()
        assert cm.get("timeouts.com_operation_sec") == 30

    def test_get_nested_key_deep(self, tmp_path, monkeypatch):
        """Should get deeply nested key"""
        appdata = tmp_path / "EmailToPDF"
        appdata.mkdir()
        monkeypatch.setattr(ConfigManager, "_get_appdata_dir", lambda: appdata)
        cm = ConfigManager.load()
        assert cm.get("search.priority_folders") == ["Inbox", "Sent Items"]

    def test_get_nonexistent_key_returns_default(self, tmp_path, monkeypatch):
        """Should return default when key does not exist"""
        appdata = tmp_path / "EmailToPDF"
        appdata.mkdir()
        monkeypatch.setattr(ConfigManager, "_get_appdata_dir", lambda: appdata)
        cm = ConfigManager.load()
        assert cm.get("nonexistent.key") is None
        assert cm.get("nonexistent.key", "fallback") == "fallback"

    def test_get_partial_path_returns_dict(self, tmp_path, monkeypatch):
        """Should return dict when path points to nested object"""
        appdata = tmp_path / "EmailToPDF"
        appdata.mkdir()
        monkeypatch.setattr(ConfigManager, "_get_appdata_dir", lambda: appdata)
        cm = ConfigManager.load()
        result = cm.get("timeouts")
        assert isinstance(result, dict)
        assert "com_operation_sec" in result


class TestConfigManagerValidation:
    """ConfigManager._validate() fallbacks"""

    def test_invalid_timeout_value_falls_back_to_default(self, tmp_path, monkeypatch):
        """Should fall back to default for negative timeout"""
        appdata = tmp_path / "EmailToPDF"
        appdata.mkdir()
        config_path = appdata / "config.json"
        config_path.write_text(json.dumps({
            "timeouts": {"com_operation_sec": -5}
        }), encoding="utf-8")
        monkeypatch.setattr(ConfigManager, "_get_appdata_dir", lambda: appdata)

        cm = ConfigManager.load()
        assert cm.get("timeouts.com_operation_sec") == 30

    def test_invalid_backoff_value_falls_back_to_default(self, tmp_path, monkeypatch):
        """Should fall back to default for invalid backoff"""
        appdata = tmp_path / "EmailToPDF"
        appdata.mkdir()
        config_path = appdata / "config.json"
        config_path.write_text(json.dumps({
            "backoff": {"initial_sec": "bad"}
        }), encoding="utf-8")
        monkeypatch.setattr(ConfigManager, "_get_appdata_dir", lambda: appdata)

        cm = ConfigManager.load()
        assert cm.get("backoff.initial_sec") == 2

    def test_invalid_search_mode_falls_back_to_fast(self, tmp_path, monkeypatch):
        """Should fall back to 'fast' for invalid search mode"""
        appdata = tmp_path / "EmailToPDF"
        appdata.mkdir()
        config_path = appdata / "config.json"
        config_path.write_text(json.dumps({
            "search": {"default_mode": "ultra"}
        }), encoding="utf-8")
        monkeypatch.setattr(ConfigManager, "_get_appdata_dir", lambda: appdata)

        cm = ConfigManager.load()
        assert cm.get("search.default_mode") == "fast"

    def test_malformed_json_does_not_crash(self, tmp_path, monkeypatch):
        """Should use defaults and not crash on malformed JSON"""
        appdata = tmp_path / "EmailToPDF"
        appdata.mkdir()
        config_path = appdata / "config.json"
        config_path.write_text("not valid json{", encoding="utf-8")
        monkeypatch.setattr(ConfigManager, "_get_appdata_dir", lambda: appdata)

        cm = ConfigManager.load()
        assert cm.get("timeouts.com_operation_sec") == 30


class TestConfigManagerAppData:
    """AppData directory management"""

    def test_appdata_dir_returns_path(self, tmp_path, monkeypatch):
        """Should return AppData path"""
        appdata = tmp_path / "EmailToPDF"
        appdata.mkdir()
        monkeypatch.setattr(ConfigManager, "_get_appdata_dir", lambda: appdata)

        cm = ConfigManager.load()
        assert cm.appdata_dir() == appdata

    def test_ensure_dir_creates_directory(self, tmp_path, monkeypatch):
        """Should create AppData directory if missing"""
        appdata = tmp_path / "EmailToPDF"
        assert not appdata.exists()
        monkeypatch.setattr(ConfigManager, "_get_appdata_dir", lambda: appdata)

        cm = ConfigManager.load()
        cm.ensure_dir()
        assert appdata.exists()

    def test_appdata_dir_is_unique_per_instance(self, tmp_path, monkeypatch):
        """Should return separate instances when AppData differs"""
        appdata1 = tmp_path / "EmailToPDF1"
        appdata2 = tmp_path / "EmailToPDF2"
        monkeypatch.setattr(ConfigManager, "_get_appdata_dir", lambda: appdata1)
        cm1 = ConfigManager.load()
        monkeypatch.setattr(ConfigManager, "_get_appdata_dir", lambda: appdata2)
        cm2 = ConfigManager.load()
        assert cm1.appdata_dir() != cm2.appdata_dir()


class TestConfigManagerToDict:
    """to_dict()"""

    def test_to_dict_returns_full_config_copy(self, tmp_path, monkeypatch):
        """Should return a copy of the full config as dict"""
        appdata = tmp_path / "EmailToPDF"
        appdata.mkdir()
        monkeypatch.setattr(ConfigManager, "_get_appdata_dir", lambda: appdata)

        cm = ConfigManager.load()
        config = cm.to_dict()
        assert isinstance(config, dict)
        assert "timeouts" in config
        assert "search" in config
        assert config["timeouts"]["com_operation_sec"] == 30