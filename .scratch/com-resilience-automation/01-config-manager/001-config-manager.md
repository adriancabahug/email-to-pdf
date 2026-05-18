# ConfigManager + AppData Infrastructure

## What to build

Centralized configuration system and AppData path management. This is the root dependency — every other slice depends on it.

**ConfigManager** loads internal defaults first, then overlays `%APPDATA%/EmailToPDF/config.json` if present. Invalid values fall back to defaults with a warning (never crash on malformed config). Exposes an immutable runtime config object. Also manages the AppData directory (`%APPDATA%/EmailToPDF/`) creation and path resolution for all persistent state files.

**Config schema:**
```json
{
  "timeouts": {
    "com_operation_sec": 30,
    "outlook_startup_sec": 60,
    "pdf_generation_sec": 120,
    "outlook_shutdown_sec": 15
  },
  "backoff": {
    "initial_sec": 2,
    "max_sec": 30,
    "jitter_sec": 1,
    "multiplier": 2
  },
  "retry": {
    "max_com_retries": 3,
    "max_outlook_restarts": 2
  },
  "search": {
    "default_mode": "fast",
    "default_date_range_days": 90,
    "deep_search_enabled": true,
    "skip_system_folders": true,
    "priority_folders": ["Inbox", "Sent Items"],
    "skip_folders": ["RSS Feeds", "Sync Issues", "Junk Email", "Deleted Items", "Public Folders", "Archive", "Drafts"]
  },
  "logging": {
    "level": "info",
    "verbose_console": false,
    "file_logging": true
  },
  "pdf": {
    "max_concurrent_exports": 1
  },
  "run_mode": "interactive",
  "directors": []
}
```

**AppData directory structure:**
- `%APPDATA%/EmailToPDF/` — root for all persistent state
- `config.json` — user configuration
- `processed_directors.json` — state persistence (Slice 2)
- `logs/` — application logs

**Interface contract:**
- `ConfigManager.load()` → `ConfigManager` instance with validated config
- `ConfigManager.get(key_path: str)` → any config value by dot-path (e.g., `timeouts.com_operation_sec`)
- `ConfigManager.appdata_dir()` → `Path` to AppData root
- `ConfigManager.ensure_dir()` → creates AppData root if missing

**No existing file to edit — create as new module at `src/config_manager.py`.**

## Acceptance criteria

- [ ] Startup succeeds with no config.json present (uses defaults)
- [ ] Malformed config.json values fall back to defaults with a warning logged
- [ ] ConfigManager.get() returns correct values by dot-path
- [ ] AppData directory is created on first run if missing
- [ ] All other slices can import ConfigManager and read config values

## Blocked by

None — can start immediately.