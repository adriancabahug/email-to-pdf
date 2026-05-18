"""Startup smoke test - validates basic imports and config loading."""

import sys
from pathlib import Path

def test_imports():
    from src.config_manager import ConfigManager
    from src.processed_directors_store import ProcessedDirectorsStore
    from src.folder_resolver import FolderResolver
    from src.progress_manager import ProgressManager
    from src.outlook_session_manager import OutlookSessionManager
    from src.email_searcher import EmailSearcher
    print("  [OK] All new modules import successfully")

def test_config_load():
    from src.config_manager import ConfigManager
    cm = ConfigManager.load()
    assert cm.get("timeouts.com_operation_sec") == 30
    assert cm.get("search.default_mode") == "fast"
    print("  [OK] ConfigManager loads and defaults work")

def test_progress_manager():
    from src.progress_manager import ProgressManager
    from src.config_manager import ConfigManager
    cm = ConfigManager.load()
    pm = ProgressManager(cm)
    pm.set_verbose(True)
    assert pm._verbose is True
    print("  [OK] ProgressManager initializes")

def test_appdata_paths():
    from src.config_manager import ConfigManager
    cm = ConfigManager.load()
    assert cm.appdata_dir().exists()
    print(f"  [OK] AppData path: {cm.appdata_dir()}")

if __name__ == "__main__":
    print("=== Startup Validation ===")
    try:
        test_imports()
        test_config_load()
        test_progress_manager()
        test_appdata_paths()
        print("\n[OK] All startup checks passed")
        sys.exit(0)
    except Exception as e:
        print(f"\n[FAIL] {e}")
        sys.exit(1)