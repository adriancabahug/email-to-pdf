"""EmailSearcher - Hybrid Outlook + Python filtering (optimized)."""

import logging
from dataclasses import dataclass
from datetime import datetime
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
            "conversation history",
            "contacts",
            "calendar",
            "tasks",
            "notes",
            "journal",
            "outbox",
        ]
    )

    PRIORITY = frozenset(
        [
            "inbox",
            "sent items",
        ]
    )

    def __call__(self, folder_name: str) -> bool:
        name = folder_name.lower().strip()
        return name in self.PRIORITY and name not in self.SKIP


class _DeepFolderStrategy:
    SKIP = frozenset(
        [
            "rss feeds",
            "sync issues",
        ]
    )

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

    # ------------------------------------------------------------------
    # PUBLIC SEARCH ENTRY
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # DASL QUERY BUILDER
    # ------------------------------------------------------------------
    @staticmethod
    def _build_dasl_query(
        terms: tuple[str, ...],
        start_date: datetime,
        end_date: datetime,
    ) -> str:
        """Build Outlook Restrict query."""

        def _escape(val: str) -> str:
            return val.replace("'", "''")

        start_str = start_date.strftime("%m/%d/%Y %I:%M %p")
        end_str = end_date.strftime("%m/%d/%Y %I:%M %p")

        conditions = [
            "[MessageClass] = 'IPM.Note'",
            f"[ReceivedTime] >= '{_escape(start_str)}'",
            f"[ReceivedTime] <= '{_escape(end_str)}'",
        ]

        term_conditions: list[str] = []

        for raw_term in terms:
            term = _escape(raw_term)

            # Ignore tiny terms
            if len(term) < 3:
                continue

            fields = [
                f"Subject LIKE '%{term}%'",
                f"SenderName LIKE '%{term}%'",
                f"To LIKE '%{term}%'",
                f"CC LIKE '%{term}%'",
            ]

            # Email/domain search
            if "@" in term or "." in term:
                fields.append(f"SenderEmailAddress LIKE '%{term}%'")

            term_conditions.append("(" + " OR ".join(fields) + ")")

        if term_conditions:
            conditions.append("(" + " OR ".join(term_conditions) + ")")

        return " AND ".join(conditions)

    # ------------------------------------------------------------------
    # CORE SEARCH LOGIC
    # ------------------------------------------------------------------
    def _search(
        self,
        search_terms: List[str],
        start_date: datetime,
        end_date: datetime,
        strategy: FolderStrategy,
        on_event: Optional[Callable[[SearchEvent], None]] = None,
    ) -> List[Any]:

        results: list[Any] = []
        seen_ids: set[str] = set()

        terms = tuple(t.lower().strip() for t in search_terms if t.strip())

        if not terms:
            return []

        has_long_terms = any(len(t) >= 5 for t in terms)

        current_account = "Unknown"

        # Prevent massive body scanning
        body_scan_limit = 500
        body_scanned = 0

        for folder in self._iter_folders(strategy):
            try:
                folder_name = getattr(
                    folder,
                    "Name",
                    "Unknown",
                )

                parent = getattr(folder, "Parent", None)

                if parent:
                    current_account = getattr(
                        parent,
                        "Name",
                        current_account,
                    )

                items = folder.Items

                # -------------------------------------------------
                # OUTLOOK NATIVE FILTER
                # -------------------------------------------------
                dasl_query = self._build_dasl_query(
                    terms,
                    start_date,
                    end_date,
                )

                try:
                    items = items.Restrict(dasl_query)

                except Exception as exc:
                    logger.debug(
                        "DASL Restrict failed (%s), falling back to date-only",
                        exc,
                    )

                    date_query = (
                        f"[ReceivedTime] >= "
                        f"'{start_date.strftime('%m/%d/%Y %I:%M %p')}' "
                        f"AND [ReceivedTime] <= "
                        f"'{end_date.strftime('%m/%d/%Y %I:%M %p')}'"
                    )

                    items = items.Restrict(date_query)

                # -------------------------------------------------
                # SORT & COLUMNS
                # -------------------------------------------------
                try:
                    items.Sort("[ReceivedTime]", True)
                except Exception:
                    pass

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

                # Skip empty folders
                if total == 0:
                    continue

                # Skip absurd enterprise folders
                if total > 50000:
                    logger.warning(
                        "Skipping huge folder: %s (%s items)",
                        folder_name,
                        total,
                    )
                    continue

                if on_event:
                    on_event(
                        SearchEvent(
                            type="folder",
                            account=current_account,
                            folder=folder_name,
                            total=total,
                        )
                    )

                # -------------------------------------------------
                # ITERATE
                # -------------------------------------------------
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

                        subject = str(getattr(msg, "Subject", "") or "")

                        sender = str(getattr(msg, "SenderName", "") or "")

                        sender_email = str(
                            getattr(
                                msg,
                                "SenderEmailAddress",
                                "",
                            )
                            or ""
                        )

                        to_field = str(getattr(msg, "To", "") or "")

                        cc_field = str(getattr(msg, "CC", "") or "")

                        text_blob = " ".join(
                            [
                                subject,
                                sender,
                                sender_email,
                                to_field,
                                cc_field,
                            ]
                        ).lower()

                        matched = any(term in text_blob for term in terms)

                        # -------------------------------------------------
                        # BODY FALLBACK
                        # -------------------------------------------------
                        if (
                            not matched
                            and has_long_terms
                            and body_scanned < body_scan_limit
                        ):
                            try:
                                body = str(
                                    getattr(
                                        msg,
                                        "HTMLBody",
                                        "",
                                    )
                                    or ""
                                ).lower()

                                body_scanned += 1

                                matched = any(term in body for term in terms)

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

    # ------------------------------------------------------------------
    # FOLDER WALK
    # ------------------------------------------------------------------
    def _iter_folders(
        self,
        strategy: FolderStrategy,
    ):

        accounts = self._session.get_all_accounts()

        for account in accounts:
            name = getattr(account, "Name", "") or ""

            if strategy(name):
                yield account

            try:
                yield from self._walk_folders(
                    account.Folders,
                    strategy,
                )

            except Exception:
                continue

    def _walk_folders(
        self,
        parent,
        strategy: FolderStrategy,
    ):

        try:
            for folder in parent:
                name = getattr(folder, "Name", "") or ""

                if strategy(name):
                    yield folder

                try:
                    yield from self._walk_folders(
                        folder.Folders,
                        strategy,
                    )

                except Exception:
                    continue

        except Exception:
            return
