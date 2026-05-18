"""ConfigManager - Centralized configuration system with AppData persistence."""

import json
import os
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field, asdict


DEFAULT_CONFIG = {
    "timeouts": {
        "com_operation_sec": 30,
        "outlook_startup_sec": 60,
        "pdf_generation_sec": 120,
        "outlook_shutdown_sec": 15,
    },
    "backoff": {
        "initial_sec": 2,
        "max_sec": 30,
        "jitter_sec": 1,
        "multiplier": 2,
    },
    "retry": {
        "max_com_retries": 3,
        "max_outlook_restarts": 2,
    },
    "search": {
        "default_mode": "fast",
        "default_date_range_days": 90,
        "deep_search_enabled": True,
        "skip_system_folders": True,
        "priority_folders": ["Inbox", "Sent Items"],
        "skip_folders": [
            "RSS Feeds",
            "Sync Issues",
            "Junk Email",
            "Deleted Items",
            "Public Folders",
            "Archive",
            "Drafts",
        ],
    },
    "logging": {
        "level": "info",
        "verbose_console": False,
        "file_logging": True,
    },
    "pdf": {
        "max_concurrent_exports": 1,
        "attachments": {
            "max_size_mb": 10,
            "embed_inline_types": [
                "image/jpeg",
                "image/png",
                "image/gif",
                "image/bmp",
                "image/webp",
            ],
            "skip_types": [
                "application/x-msdownload",
                "application/x-executable",
            ],
        },
    },
    "run_mode": "interactive",
    "directors": [],
}


@dataclass
class ConfigManager:
    _config: dict = field(default_factory=lambda: DEFAULT_CONFIG.copy())
    _appdata_dir: Path = field(default_factory=lambda: Path())

    @classmethod
    def load(cls) -> "ConfigManager":
        """Load config with defaults merged with user config.json."""
        instance = cls()
        instance._appdata_dir = cls._get_appdata_dir()
        instance._appdata_dir.mkdir(parents=True, exist_ok=True)

        config_path = instance._appdata_dir / "config.json"
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    user_config = json.load(f)
                instance._config = cls._merge(instance._config, user_config, [])
            except (json.JSONDecodeError, OSError) as e:
                instance._config = cls._deep_copy(DEFAULT_CONFIG)
                cls._log_warning(f"Failed to parse config.json ({e}) — using defaults")
        else:
            instance._config = cls._deep_copy(DEFAULT_CONFIG)
            cls._generate_template(instance._appdata_dir)

        instance._config = cls._validate(instance._config, [])
        return instance

    @staticmethod
    def _get_appdata_dir() -> Path:
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "EmailToPDF"
        temp = Path(os.environ.get("TEMP", ".")) / "EmailToPDF"
        return temp

    @staticmethod
    def _generate_template(appdata_dir: Path) -> None:
        try:
            template_path = appdata_dir / "config.json"
            if not template_path.exists():
                with open(template_path, "w", encoding="utf-8") as f:
                    json.dump(DEFAULT_CONFIG, f, indent=2)
        except OSError:
            pass

    @staticmethod
    def _deep_copy(d: dict) -> dict:
        return json.loads(json.dumps(d))

    @classmethod
    def _merge(cls, base: dict, overlay: dict, path: list) -> dict:
        result = cls._deep_copy(base)
        for key, value in overlay.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = cls._merge(result[key], value, path + [key])
            else:
                result[key] = value
        return result

    @classmethod
    def _validate(cls, config: dict, path: list) -> dict:
        result = cls._deep_copy(config)

        if "timeouts" in result:
            for field_name in ["com_operation_sec", "outlook_startup_sec", "pdf_generation_sec", "outlook_shutdown_sec"]:
                if field_name in result["timeouts"]:
                    if not isinstance(result["timeouts"][field_name], (int, float)) or result["timeouts"][field_name] <= 0:
                        cls._log_warning(f"Invalid value for {'.'.join(path + ['timeouts', field_name])} — using default")
                        result["timeouts"][field_name] = DEFAULT_CONFIG["timeouts"].get(field_name, 30)

        if "backoff" in result:
            for field_name in ["initial_sec", "max_sec", "jitter_sec", "multiplier"]:
                if field_name in result["backoff"]:
                    if not isinstance(result["backoff"][field_name], (int, float)) or result["backoff"][field_name] < 0:
                        cls._log_warning(f"Invalid value for {'.'.join(path + ['backoff', field_name])} — using default")
                        result["backoff"][field_name] = DEFAULT_CONFIG["backoff"].get(field_name, 2)

        if "retry" in result:
            for field_name in ["max_com_retries", "max_outlook_restarts"]:
                if field_name in result["retry"]:
                    val = result["retry"][field_name]
                    if not isinstance(val, int) or val < 0:
                        cls._log_warning(f"Invalid value for {'.'.join(path + ['retry', field_name])} — using default")
                        result["retry"][field_name] = DEFAULT_CONFIG["retry"].get(field_name, 3)

        if "search" in result:
            if "priority_folders" in result["search"] and not isinstance(result["search"]["priority_folders"], list):
                result["search"]["priority_folders"] = DEFAULT_CONFIG["search"]["priority_folders"]
            if "skip_folders" in result["search"] and not isinstance(result["search"]["skip_folders"], list):
                result["search"]["skip_folders"] = DEFAULT_CONFIG["search"]["skip_folders"]
            if "default_mode" in result["search"] and result["search"]["default_mode"] not in ("fast", "deep"):
                result["search"]["default_mode"] = "fast"
            if "default_date_range_days" in result["search"]:
                val = result["search"]["default_date_range_days"]
                if not isinstance(val, int) or val < 0:
                    result["search"]["default_date_range_days"] = 90
                elif val == 0:
                    pass

        if "logging" in result:
            if "level" in result["logging"] and result["logging"]["level"] not in ("info", "verbose"):
                result["logging"]["level"] = "info"

        if "run_mode" in result and result["run_mode"] not in ("interactive", "batch"):
            result["run_mode"] = "interactive"

        return result

    @staticmethod
    def _log_warning(msg: str) -> None:
        print(f"[WARN] {msg}")

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get a config value by dot-path, e.g. 'timeouts.com_operation_sec'."""
        keys = key_path.split(".")
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def appdata_dir(self) -> Path:
        """Return the AppData directory path."""
        return self._appdata_dir

    def ensure_dir(self) -> None:
        """Ensure the AppData directory exists."""
        self._appdata_dir.mkdir(parents=True, exist_ok=True)

    def to_dict(self) -> dict:
        """Return the full config as a dict."""
        return self._deep_copy(self._config)