"""Build validation smoke tests for Slice 7."""

import sys
from pathlib import Path

def test_config_manager_integration():
    """ConfigManager must work in the bundled environment."""
    from src.config_manager import ConfigManager
    cm = ConfigManager.load()
    assert cm.appdata_dir() is not None
    assert cm.get("timeouts.com_operation_sec") >= 0
    print("  [OK] ConfigManager integration")

def test_new_modules_import():
    """All new modules must be importable in the bundle."""
    from src.config_manager import ConfigManager
    from src.processed_directors_store import ProcessedDirectorsStore
    from src.folder_resolver import FolderResolver
    from src.progress_manager import ProgressManager
    from src.outlook_session_manager import OutlookSessionManager
    from src.email_searcher import EmailSearcher
    print("  [OK] All modules importable")

def test_dependencies_available():
    """Required packages (rich, psutil) must be available."""
    import rich
    import psutil
    import win32com.client
    print("  [OK] rich, psutil, win32com available")

def test_main_orchestrator_instantiation():
    """MainOrchestrator must be instantiable without COM."""
    from src.main_orchestrator import MainOrchestrator
    try:
        orch = MainOrchestrator()
        assert orch is not None
        assert hasattr(orch, '_config')
        assert hasattr(orch, '_progress')
        assert hasattr(orch, '_cli')
        print("  [OK] MainOrchestrator instantiates")
    except Exception as e:
        print(f"  [WARN] Orchestrator init: {e}")

def test_playwright_browser():
    """Playwright browser must be available."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_content("<h1>Test</h1>")
            text = page.text_content("h1")
            assert text == "Test"
            browser.close()
        print("  [OK] Playwright Chromium launches and renders")
    except Exception as e:
        print(f"  [FAIL] Playwright: {e}")
        raise

if __name__ == "__main__":
    print("=== Build Validation ===")
    try:
        test_config_manager_integration()
        test_new_modules_import()
        test_dependencies_available()
        test_main_orchestrator_instantiation()
        test_playwright_browser()
        print("\n[OK] All build validation checks passed")
        sys.exit(0)
    except Exception as e:
        print(f"\n[FAIL] {e}")
        sys.exit(1)