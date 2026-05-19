"""EmailSearcher - Restrict()-based search with pluggable folder strategy."""

import logging
from datetime import datetime, timedelta
from typing import Any, List, Optional, Protocol

from src.outlook_session_manager import OutlookSessionManager
from src.processed_directors_store import ProcessedDirectorsStore
from src.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class FolderStrategy(Protocol):
    def __call__(self, folder_name: str) -> bool: ...


class _FastFolderStrategy:
    SKIP: frozenset[str] = frozenset([
        "rss feeds", "sync issues", "junk email",
        "deleted items", "public folders", "archive", "drafts",
    ])
    PRIORITY: frozenset[str] = frozenset(["inbox", "sent items"])

    def __call__(self, folder_name: str) -> bool:
        name = folder_name.lower().strip()
        return name in self.PRIORITY and name not in self.SKIP


class _DeepFolderStrategy:
    SKIP: frozenset[str] = frozenset(["rss feeds", "sync issues"])

    def __call__(self, folder_name: str) -> bool:
        return folder_name.lower().strip() not in self.SKIP


class EmailSearcher:
    def __init__(
        self,
        session_manager: Optional[OutlookSessionManager] = None,
        processed_store: Optional[ProcessedDirectorsStore] = None,
        config_manager: Optional[ConfigManager] = None,
    ):
        self._session = session_manager
        self._processed_store = processed_store
        self._config = config_manager

    def search(self, director_email: str, mode: Optional[str] = None) -> List[Any]:
        normalized_name = director_email.lower().strip()
        if self._processed_store and self._processed_store.is_processed(normalized_name):
            return []

        if not self._session:
            raise RuntimeError("No session manager provided")

        if mode is None:
            mode = self._config.get("search.default_mode", "fast") if self._config else "fast"

        if mode == "deep":
            return self._search(director_email, _DeepFolderStrategy())
        return self._search(director_email, _FastFolderStrategy())

    def _search(self, director_email: str, strategy: FolderStrategy) -> List[Any]:
        if not self._session:
            raise RuntimeError("No session manager provided")

        date_cutoff = self._get_date_cutoff()
        results: List[Any] = []

        for folder in self._iter_folders(strategy):
            try:
                restrict_query = self._build_restrict_query(director_email, date_cutoff)
                items = folder.Items
                restricted = items.Restrict(restrict_query) if restrict_query else items
                restricted.Sort("[ReceivedTime]", True)
                for msg in restricted:
                    if self._phase2_validate(msg, director_email):
                        results.append(msg)
            except Exception as exc:
                logger.debug("Folder search skipped: %s", exc)

        return results

    def _iter_folders(self, strategy: FolderStrategy):
        accounts = self._session.get_all_accounts()
        for account in accounts:
            name = getattr(account, "Name", "") or ""
            if strategy(name):
                yield account
            try:
                yield from self._walk_folders(account.Folders, strategy)
            except Exception as exc:
                logger.debug("Account folder walk skipped: %s", exc)

    def _walk_folders(self, parent, strategy: FolderStrategy):
        try:
            for folder in parent:
                name = getattr(folder, "Name", "") or ""
                if strategy(name):
                    yield folder
                try:
                    yield from self._walk_folders(folder.Folders, strategy)
                except Exception as exc:
                    logger.debug("Subfolder walk skipped: %s", exc)
        except Exception as exc:
            logger.debug("Folder iteration skipped: %s", exc)

    def _build_restrict_query(self, director_email: str, date_cutoff: Optional[datetime]) -> str:
        safe_email = director_email.replace("'", "''")
        parts = [f"[SenderEmailAddress] = '{safe_email}'"]
        if date_cutoff:
            date_str = date_cutoff.strftime("%m/%d/%Y")
            parts.append(f"[ReceivedTime] >= '{date_str}'")
        return " AND ".join(parts)

    def _phase2_validate(self, message: Any, director_email: str) -> bool:
        try:
            email_lower = director_email.lower().strip()
            to_field = str(getattr(message, "To", "") or "").lower()
            cc_field = str(getattr(message, "CC", "") or "").lower()
            sender = str(getattr(message, "SenderEmailAddress", "") or "").lower()
            return email_lower in sender or email_lower in to_field or email_lower in cc_field
        except Exception as exc:
            logger.debug("Phase2 validation skipped: %s", exc)
            return False

    def _get_date_cutoff(self) -> Optional[datetime]:
        if not self._config:
            return None
        days = self._config.get("search.default_date_range_days")
        if not days or days <= 0:
            return None
        return datetime.now() - timedelta(days=int(days))

    def mark_processed(self, director_email: str) -> None:
        if self._processed_store:
            self._processed_store.mark_processed(director_email)