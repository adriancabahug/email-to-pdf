"""EmailSearcher - Hybrid Outlook + Python filtering (optimized)."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, List, Optional, Protocol

from src.config_manager import ConfigManager
from src.outlook_session_manager import OutlookSessionManager
from src.processed_directors_store import ProcessedDirectorsStore

logger = logging.getLogger(__name__)


@dataclass
class SearchEvent:
    type: str
    account: Optional[str] = None
    folder: Optional[str] = None
    subject: Optional[str] = None
    sender: Optional[str] = None
    date: Optional[str] = None
    total: Optional[int] = None


class FolderStrategy(Protocol):
    def __call__(self, folder_name: str) -> bool: ...


class _FastFolderStrategy:
    SKIP = frozenset(
        [
            "rss feeds",
            "sync issues",
            "junk email",
            "deleted items",
            "public folders",
            "archive",
            "drafts",

            # Huge enterprise slowdown folders
            "conversation history",
            "contacts",
            "calendar",
            "tasks",
            "notes",
            "journal",
            "outbox",
        ]
    )

    PRIORITY = frozenset(["inbox", "sent items"])

    def __call__(self, folder_name: str) -> bool:
        name = folder_name.lower().strip()
        return name in self.PRIORITY and name not in self.SKIP


class _DeepFolderStrategy:
    SKIP = frozenset(["rss feeds", "sync issues"])

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

    # -------------------------
    # PUBLIC SEARCH ENTRY
    # -------------------------
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

        if self._processed_store and self._processed_store.is_processed(
            "|".join(search_terms)
        ):
            return []

        if not self._session:
            raise RuntimeError("No session manager provided")

        mode = mode or (
            self._config.get("search.default_mode", "fast") if self._config else "fast"
        )

        # Default safe range handling
        start_date = start_date or datetime(1970, 1, 1)
        end_date = end_date or datetime(9999, 12, 31, 23, 59, 59)

        strategy = _DeepFolderStrategy() if mode == "deep" else _FastFolderStrategy()

        return self._search(
            search_terms,
            start_date,
            end_date,
            strategy,
            on_event,
        )

    # -------------------------
    # CORE SEARCH LOGIC
    # -------------------------
    def _search(
        self,
        search_terms: List[str],
        start_date: datetime,
        end_date: datetime,
        strategy: FolderStrategy,
        on_event: Optional[Callable[[SearchEvent], None]] = None,
    ) -> List[Any]:

        results = []
        seen_ids = set()

        terms = tuple(
            t.lower().strip()
            for t in search_terms
            if t.strip()
        )

        if not terms:
            return []

        current_account = "Unknown"

        for folder in self._iter_folders(strategy):

            try:
                folder_name = getattr(folder, "Name", "Unknown")

                parent = getattr(folder, "Parent", None)

                if parent:
                    current_account = getattr(
                        parent,
                        "Name",
                        current_account,
                    )

                items = folder.Items

                # ---------------------------------------------
                # DATE FILTER (OUTLOOK NATIVE)
                # ---------------------------------------------
                date_query = (
                    f"[ReceivedTime] >= '{start_date.strftime('%m/%d/%Y %I:%M %p')}' "
                    f"AND [ReceivedTime] <= '{end_date.strftime('%m/%d/%Y %I:%M %p')}'"
                )

                try:
                    items = items.Restrict(date_query)

                except Exception as exc:
                    logger.debug(
                        "Date restrict failed: %s",
                        exc,
                    )

                # ---------------------------------------------
                # SORT
                # ---------------------------------------------
                try:
                    items.Sort("[ReceivedTime]", True)

                except Exception:
                    pass

                # ---------------------------------------------
                # PRELOAD LIGHTWEIGHT FIELDS ONLY
                # ---------------------------------------------
                try:
                    items.SetColumns(
                        "Subject,"
                        "SenderName,"
                        "SenderEmailAddress,"
                        "To,"
                        "CC,"
                        "ReceivedTime,"
                        "EntryID"
                    )

                except Exception:
                    pass

                total = getattr(items, "Count", 0)

                if on_event:
                    on_event(
                        SearchEvent(
                            type="folder",
                            account=current_account,
                            folder=folder_name,
                            total=total,
                        )
                    )

                # ---------------------------------------------
                # ITERATE
                # ---------------------------------------------
                for i in range(1, total + 1):

                    try:
                        msg = items.Item(i)

                    except Exception:
                        continue

                    try:

                        # MailItem only
                        if getattr(msg, "Class", None) != 43:
                            continue

                        entry_id = getattr(
                            msg,
                            "EntryID",
                            None,
                        )

                        if not entry_id:
                            continue

                        if entry_id in seen_ids:
                            continue

                        # ---------------------------------
                        # LIGHTWEIGHT FIELDS ONLY
                        # ---------------------------------
                        subject = str(
                            getattr(msg, "Subject", "") or ""
                        )

                        sender = str(
                            getattr(msg, "SenderName", "") or ""
                        )

                        sender_email = str(
                            getattr(msg, "SenderEmailAddress", "") or ""
                        )

                        to_field = str(
                            getattr(msg, "To", "") or ""
                        )

                        cc_field = str(
                            getattr(msg, "CC", "") or ""
                        )

                        text_blob = " ".join([
                            subject,
                            sender,
                            sender_email,
                            to_field,
                            cc_field,
                        ]).lower()

                        matched = any(
                            term in text_blob
                            for term in terms
                        )

                        # ---------------------------------
                        # BODY FALLBACK
                        # ONLY IF NEEDED
                        # ---------------------------------
                        if not matched:

                            # Skip expensive body scan
                            # for short/common terms
                            should_check_body = any(
                                len(term) >= 5
                                for term in terms
                            )

                            if should_check_body:

                                try:
                                    body = str(
                                        getattr(msg, "Body", "") or ""
                                    ).lower()

                                    matched = any(
                                        term in body
                                        for term in terms
                                    )

                                except Exception:
                                    pass

                        if not matched:
                            continue

                        seen_ids.add(entry_id)

                        results.append(msg)

                        if on_event:
                            on_event(
                                SearchEvent(
                                    type="match",
                                    account=current_account,
                                    folder=folder_name,
                                    subject=subject,
                                    sender=sender,
                                    date=str(
                                        getattr(
                                            msg,
                                            "ReceivedTime",
                                            "",
                                        )
                                    ),
                                )
                            )

                    except Exception as exc:
                        logger.debug(
                            "Message processing failed: %s",
                            exc,
                        )

            except Exception as exc:
                logger.debug(
                    "Folder search failed: %s",
                    exc,
                )

        results.sort(
            key=lambda m: getattr(
                m,
                "ReceivedTime",
                datetime.min,
            )
        )

        return results

    # -------------------------
    # FOLDER WALK
    # -------------------------
    def _iter_folders(self, strategy: FolderStrategy):

        accounts = self._session.get_all_accounts()

        for account in accounts:
            name = getattr(account, "Name", "") or ""

            if strategy(name):
                yield account

            try:
                yield from self._walk_folders(account.Folders, strategy)
            except Exception:
                continue

    def _walk_folders(self, parent, strategy: FolderStrategy):

        try:
            for folder in parent:
                name = getattr(folder, "Name", "") or ""

                if strategy(name):
                    yield folder

                try:
                    yield from self._walk_folders(folder.Folders, strategy)
                except Exception:
                    continue

        except Exception:
            return
