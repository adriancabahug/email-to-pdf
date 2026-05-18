"""
PDF generation via Playwright. Singleton removed in favor of explicit
instance lifecycle managed by a context manager.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Optional, Any

if getattr(sys, 'frozen', False):
    bundle_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    browser_path = os.path.join(bundle_dir, "playwright-browsers")
    if os.path.exists(browser_path):
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = browser_path

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

logger = logging.getLogger(__name__)


class PDFGenerator:
    """
    Non-singleton instance. Start/stop is explicit. Use PDFSession context
    manager in the orchestrator to ensure cleanup.
    """

    def __init__(self) -> None:
        self._playwright: Optional[Any] = None
        self._browser: Optional[Any] = None

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def start(self) -> bool:
        if not PLAYWRIGHT_AVAILABLE:
            return False
        if self._browser is not None:
            return True
        try:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=True)
            logger.info("Playwright browser launched")
            return True
        except Exception as exc:
            logger.error("Failed to start Playwright: %s", exc)
            return False

    def stop(self) -> None:
        if self._browser:
            try:
                self._browser.close()
            except Exception as exc:
                logger.warning("Browser close warning: %s", exc)
            self._browser = None
        if self._playwright:
            try:
                self._playwright.stop()
            except Exception as exc:
                logger.warning("Playwright stop warning: %s", exc)
            self._playwright = None
        logger.info("Playwright resources released")

    def is_running(self) -> bool:
        return self._browser is not None

    # ------------------------------------------------------------------ #
    # Generation
    # ------------------------------------------------------------------ #
    def generate_pdf(self, html: str, output_path: Path) -> bool:
        if not PLAYWRIGHT_AVAILABLE:
            return False
        if self._browser is None:
            return False
        try:
            os.makedirs(output_path.parent, exist_ok=True)
            page = self._browser.new_page()
            page.set_content(html, wait_until="networkidle")
            page.pdf(
                path=str(output_path),
                format="A4",
                print_background=True,
                margin={
                    "top": "20mm",
                    "bottom": "20mm",
                    "left": "15mm",
                    "right": "15mm",
                },
            )
            page.close()
            logger.info("PDF written: %s", output_path)
            return True
        except Exception as exc:
            logger.error("PDF generation failed: %s", exc)
            return False

    def generate_pdf_from_file(self, html_file_path: str, output_path: str, max_retries: int = 1) -> bool:
        if not PLAYWRIGHT_AVAILABLE:
            return False
        if self._browser is None:
            return False

        last_error = None
        for attempt in range(max_retries + 1):
            if attempt > 0:
                logger.info("Retry %d/%d...", attempt, max_retries)
                if not self._restart_browser():
                    return False

            try:
                os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
                page = self._browser.new_page()
                page.goto(f"file:///{html_file_path}", wait_until='networkidle')
                page.pdf(
                    path=output_path,
                    print_background=True,
                    margin={'top': '0.5in', 'bottom': '0.5in', 'left': '0.5in', 'right': '0.5in'}
                )
                page.close()
                logger.info("PDF generated from file: %s", output_path)
                return True
            except Exception as exc:
                last_error = exc
                logger.warning("PDF generation attempt %d failed: %s", attempt + 1, exc)
                if attempt < max_retries:
                    self._browser = None

        logger.error("PDF generation failed after %d attempts: %s", max_retries + 1, last_error)
        return False

    def _restart_browser(self) -> bool:
        self.stop()
        return self.start()

    def __del__(self) -> None:
        self.stop()


class PDFSession:
    """
    Context manager for the orchestrator. Guarantees that a single
    browser instance is reused across many directors and then cleanly
    shut down.
    """

    def __init__(self, generator: PDFGenerator) -> None:
        self._gen = generator

    def __enter__(self) -> PDFGenerator:
        if not self._gen.start():
            raise RuntimeError("Could not start PDF engine")
        return self._gen

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._gen.stop()