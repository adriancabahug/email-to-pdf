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

    def search(
        self,
        search_terms: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        mode: Optional[str] = None,
    ) -> List[Any]:
        if not search_terms:
            return []

        smsf_key = "|".join(search_terms)
        if self._processed_store and self._processed_store.is_processed(smsf_key):
            return []

        if not self._session:
            raise RuntimeError("No session manager provided")

        if mode is None:
            mode = self._config.get("search.default_mode", "fast") if self._config else "fast"

        if mode == "deep":
            return self._search(search_terms, start_date, end_date, _DeepFolderStrategy())
        return self._search(search_terms, start_date, end_date, _FastFolderStrategy())

    def _search(
        self,
        search_terms: List[str],
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        strategy: FolderStrategy,
    ) -> List[Any]:
        if not self._session:
            raise RuntimeError("No session manager provided")

        results: List[Any] = []
        seen_ids = set()

        for folder in self._iter_folders(strategy):
            try:
                restrict_query = self._build_restrict_query(search_terms, start_date, end_date)
                items = folder.Items
                restricted = items.Restrict(restrict_query) if restrict_query else items
                restricted.Sort("[ReceivedTime]", True)
                for msg in restricted:
                    entry_id = getattr(msg, "EntryID", None)
                    if entry_id and entry_id not in seen_ids:
                        seen_ids.add(entry_id)
                        results.append(msg)
            except Exception as exc:
                logger.debug("Folder search skipped: %s", exc)

        results.sort(key=lambda m: getattr(m, "ReceivedTime", datetime.min))
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

    def _build_restrict_query(
        self,
        search_terms: List[str],
        start_date: Optional[datetime],
        end_date: Optional[datetime],
    ) -> str:
        keyword_conditions = []
        for kw in search_terms:
            safe = kw.replace("'", "''")
            keyword_conditions.append(f"[SenderEmailAddress] LIKE '%{safe}%'")
            keyword_conditions.append(f"[To] LIKE '%{safe}%'")
            keyword_conditions.append(f"[CC] LIKE '%{safe}%'")
            keyword_conditions.append(f"[BCC] LIKE '%{safe}%'")
            keyword_conditions.append(f"[Subject] LIKE '%{safe}%'")

        parts = [f"({' OR '.join(keyword_conditions)})"]

        if start_date:
            start_str = start_date.strftime("%m/%d/%Y %I:%M %p")
            parts.append(f"[ReceivedTime] >= '{start_str}'")
        if end_date:
            end_str = end_date.strftime("%m/%d/%Y %I:%M %p")
            parts.append(f"[ReceivedTime] <= '{end_str}'")

        return " AND ".join(parts)

    def _get_date_cutoff(self) -> Optional[datetime]:
        if not self._config:
            return None
        days = self._config.get("search.default_date_range_days")
        if not days or days <= 0:
            return None
        return datetime.now() - timedelta(days=int(days))

    def mark_processed(self, smsf_key: str) -> None:
        """Mark an SMSF as processed to skip in future runs."""
        if self._processed_store:
            self._processed_store.mark_processed(smsf_key)