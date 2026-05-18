"""
License validation with separated concerns:
- Pure validation logic (network call)
- Storage I/O (file read/write)
- UI orchestration (prompts) kept in a thin layer
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Protocol

from rich.prompt import Prompt

logger = logging.getLogger(__name__)


class HttpClient(Protocol):
    """Protocol for the HTTP dependency so tests can inject fakes."""
    def post(self, url: str, **kwargs) -> ResponseLike:
        ...


class ResponseLike(Protocol):
    status_code: int
    def json(self) -> Dict[str, Any]: ...
    def raise_for_status(self) -> None: ...


class LicenseValidator:
    """
    Production implementation uses `requests` by default, but any object
    matching the HttpClient protocol can be injected.
    """

    def __init__(
        self,
        api_url: str,
        storage_path: Path,
        http_client: Optional[HttpClient] = None,
    ) -> None:
        self._api_url = api_url
        self._storage_path = storage_path
        self._http = http_client  # late-bound to avoid import-time side effects

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def validate_key(self, key: str) -> Dict[str, Any]:
        """Pure network boundary. Raises on transport or HTTP error."""
        http = self._resolve_http()
        resp = http.post(
            self._api_url,
            json={"key": key.strip()},
            headers={"Content-Type": "application/json"},
            timeout=(5, 10),
        )
        resp.raise_for_status()
        payload = resp.json()
        logger.info("License validation response: valid=%s", payload.get("valid"))
        return payload

    def get_stored_key(self) -> Optional[str]:
        """Idempotent read. Returns None if file missing or malformed."""
        if not self._storage_path.exists():
            return None
        try:
            data = json.loads(self._storage_path.read_text(encoding="utf-8"))
            key = data.get("license_key")
            return key if isinstance(key, str) and key.strip() else None
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to read stored license: %s", exc)
            return None

    def store_key(self, key: str) -> None:
        """Atomic write: temp file + rename to avoid corruption."""
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        temp = self._storage_path.with_suffix(".tmp")
        temp.write_text(
            json.dumps({"license_key": key.strip()}, indent=2),
            encoding="utf-8",
        )
        temp.replace(self._storage_path)

    def prompt_and_validate(self) -> Optional[str]:
        """
        UI orchestration. Tries stored key first, then falls back to
        interactive prompt with retry loop.
        """
        stored = self.get_stored_key()
        if stored:
            result = self.validate_key(stored)
            if result.get("valid"):
                return stored

        while True:
            key = Prompt.ask("Enter license key")
            try:
                result = self.validate_key(key)
            except Exception as exc:
                logger.error("Validation request failed: %s", exc)
                print("Unable to reach license server. Please check your connection.")
                continue

            if result.get("valid"):
                self.store_key(key)
                return key

            print("Invalid license key. Try again or press Ctrl+C to quit.")

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #
    def _resolve_http(self) -> HttpClient:
        if self._http is not None:
            return self._http
        import requests  # late import — keeps CLI startup fast
        self._http = requests
        return self._http