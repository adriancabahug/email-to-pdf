"""EmailSearcher - Python-side filtering with pluggable folder strategy."""

import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Any, Callable, List, Optional, Protocol

from src.outlook_session_manager import OutlookSessionManager
from src.processed_directors_store import ProcessedDirectorsStore
from src.config_manager import ConfigManager

logger = logging.getLogger(__name__)


@dataclass
class SearchEvent:
    type: str  # 'account', 'folder', 'match', 'complete'
    account: Optional[str] = None
    folder: Optional[str] = None
    subject: Optional[str] = None
    sender: Optional[str] = None
    date: Optional[str] = None
    current: Optional[int] = None
    total: Optional[int] = None
    message: Optional[str] = None


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
        on_event: Optional[Callable[[SearchEvent], None]] = None,
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
            return self._search(search_terms, start_date, end_date, _DeepFolderStrategy(), on_event)
        return self._search(search_terms, start_date, end_date, _FastFolderStrategy(), on_event)

    def _search(
        self,
        search_terms: List[str],
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        strategy: FolderStrategy,
        on_event: Optional[Callable[[SearchEvent], None]] = None,
    ) -> List[Any]:
        if not self._session:
            raise RuntimeError("No session manager provided")

        results: List[Any] = []
        seen_ids = set()
        search_terms_lower = [t.lower() for t in search_terms]

        if on_event:
            try:
                accounts = self._session.get_all_accounts()
                for account in accounts:
                    name = getattr(account, "Name", "Unknown")
                    total = 0
                    try:
                        for f in account.Folders:
                            try:
                                total += f.Items.Count
                            except:
                                pass
                    except:
                        pass
                    on_event(SearchEvent(type='account', account=name, total=total))
            except Exception as exc:
                logger.debug("Account enumeration failed: %s", exc)

        current_account = "Unknown"

        for folder in self._iter_folders(strategy):
            try:
                folder_name = getattr(folder, "Name", "Unknown")

                try:
                    parent = getattr(folder, 'Parent', None)
                    if parent:
                        current_account = getattr(parent, 'Name', current_account)
                except:
                    pass

                items = folder.Items

                if start_date or end_date:
                    date_conditions = []
                    if start_date:
                        start_str = start_date.strftime("%m/%d/%Y %I:%M %p")
                        date_conditions.append(f"[ReceivedTime] >= '{start_str}'")
                    if end_date:
                        end_str = end_date.strftime("%m/%d/%Y %I:%M %p")
                        date_conditions.append(f"[ReceivedTime] <= '{end_str}'")
                    if date_conditions:
                        date_query = " AND ".join(date_conditions)
                        try:
                            items = items.Restrict(date_query)
                        except Exception as exc:
                            logger.debug("Date restrict failed: %s", exc)

                items.Sort("[ReceivedTime]", True)
                total_items = getattr(items, "Count", 0)

                if on_event:
                    on_event(SearchEvent(
                        type='folder',
                        account=current_account,
                        folder=folder_name,
                        total=total_items,
                    ))

                for i, msg in enumerate(items, 1):
                    if start_date or end_date:
                        received = getattr(msg, "ReceivedTime", None)
                        if received:
                            if start_date and received < start_date:
                                continue
                            if end_date and received > end_date:
                                continue

                    text_to_search = " ".join([
                        str(getattr(msg, "SenderEmailAddress", "") or ""),
                        str(getattr(msg, "SenderName", "") or ""),
                        str(getattr(msg, "To", "") or ""),
                        str(getattr(msg, "CC", "") or ""),
                        str(getattr(msg, "BCC", "") or ""),
                        str(getattr(msg, "Subject", "") or ""),
                        str(getattr(msg, "Body", "") or ""),
                    ]).lower()

                    if not any(term in text_to_search for term in search_terms_lower):
                        continue

                    entry_id = getattr(msg, "EntryID", None)
                    if entry_id and entry_id not in seen_ids:
                        seen_ids.add(entry_id)
                        results.append(msg)

                        if on_event:
                            on_event(SearchEvent(
                                type='match',
                                account=current_account,
                                folder=folder_name,
                                subject=str(getattr(msg, 'Subject', '')),
                                sender=str(getattr(msg, 'SenderName', '')),
                                date=str(getattr(msg, 'ReceivedTime', '')),
                            ))

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