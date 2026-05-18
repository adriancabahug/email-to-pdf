"""
Atomic, case-insensitive persistence of processed directors.
Accepts a Path directly instead of a full ConfigManager.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Set

logger = logging.getLogger(__name__)


class ProcessedDirectorsStore:
    def __init__(self, storage_path: Path) -> None:
        self._path = storage_path
        self._cache: Set[str] = set()
        self._load()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def is_processed(self, name: str) -> bool:
        return self._normalize(name) in self._cache

    def mark_processed(self, name: str) -> None:
        normalized = self._normalize(name)
        if normalized in self._cache:
            return
        self._cache.add(normalized)
        self._save()

    def get_all(self) -> Set[str]:
        return set(self._cache)

    def reset(self) -> None:
        self._cache.clear()
        if self._path.exists():
            self._path.unlink()

    # ------------------------------------------------------------------ #
    # Persistence (atomic write)
    # ------------------------------------------------------------------ #
    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                self._cache = {self._normalize(item) for item in data if isinstance(item, str)}
            else:
                logger.warning("Unexpected format in processed store; starting fresh")
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not load processed store: %s", exc)

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temp = self._path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(sorted(self._cache), indent=2),
            encoding="utf-8",
        )
        temp.replace(self._path)

    # ------------------------------------------------------------------ #
    # Normalization
    # ------------------------------------------------------------------ #
    @staticmethod
    def _normalize(name: str) -> str:
        return name.strip().lower()