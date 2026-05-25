"""EmailSearcher - Hybrid Outlook + Python filtering (optimized)."""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, List, Optional, Protocol

from src.config_manager import ConfigManager
from src.outlook_session_manager import OutlookSessionManager
from src.processed_directors_store import ProcessedDirectorsStore
from src.cache_manager import EmailMetadataCache
from src.folder_strategies import (
    FastFolderStrategy,
    DeepFolderStrategy,
)

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
    message: Optional[str] = None


@dataclass
class ExtractedEmail:
    entry_id: str
    sender_name: str
    sender_email: str
    to_recipients: str
    cc_recipients: str
    bcc_recipients: str
    subject: str
    html_body: str
    body: str
    received_time: datetime
    sent_on: datetime
    internet_message_id: str
    conversation_id: str


class FolderStrategy(Protocol):
    def __call__(self, folder_name: str) -> bool: ...



class EmailSearcher:
    def __init__(
        self,
        session_manager: Optional[OutlookSessionManager] = None,
        processed_store: Optional[ProcessedDirectorsStore] = None,
        config_manager: Optional[ConfigManager] = None,
        cache: Optional[EmailMetadataCache] = None,
    ):
        self._session = session_manager
        self._processed_store = processed_store
        self._config = config_manager
        self._cache = cache

    @staticmethod
    def _extract_com_item(item) -> ExtractedEmail:
        return ExtractedEmail(
            entry_id=str(getattr(item, "EntryID", "") or ""),
            sender_name=str(getattr(item, "SenderName", "") or ""),
            sender_email=str(getattr(item, "SenderEmailAddress", "") or ""),
            to_recipients=str(getattr(item, "To", "") or ""),
            cc_recipients=str(getattr(item, "CC", "") or ""),
            bcc_recipients=str(getattr(item, "BCC", "") or ""),
            subject=str(getattr(item, "Subject", "") or ""),
            html_body=str(getattr(item, "HTMLBody", "") or ""),
            body=str(getattr(item, "Body", "") or ""),
            received_time=getattr(item, "ReceivedTime", datetime.min),
            sent_on=getattr(item, "SentOn", datetime.min),
            internet_message_id=str(getattr(item, "InternetMessageID", "") or ""),
            conversation_id=str(getattr(item, "ConversationID", "") or ""),
        )

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
    ) -> List[ExtractedEmail]:

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

        # ------------------------------------------------------------------
        # FAST PATH: Use cache if available and has data
        # ------------------------------------------------------------------
        if self._cache:
            try:
                stats = self._cache.get_stats()
                if stats["total_emails"] > 0:
                    logger.info("Using cache: %d emails indexed", stats["total_emails"])
                    logger.info("Running cache-backed retrieval mode")
                    return self._search_via_cache(
                        search_terms, start_date, end_date, mode, on_event
                    )
                else:
                    logger.info("Cache empty, building index from Outlook...")
            except Exception as exc:
                logger.warning("Cache check failed: %s", exc)

        # ------------------------------------------------------------------
        # SLOW PATH: Live Outlook search (also populates cache)
        # ------------------------------------------------------------------
        logger.info("Running live Outlook retrieval mode")

        strategy = DeepFolderStrategy() if mode == "deep" else FastFolderStrategy()
        return self._search(
            search_terms, start_date, end_date, strategy, on_event
        )

    # ------------------------------------------------------------------
    # CACHE SEARCH (sub-second)
    # ------------------------------------------------------------------
    def _search_via_cache(
        self,
        search_terms: List[str],
        start_date: datetime,
        end_date: datetime,
        mode: str,
        on_event: Optional[Callable[[SearchEvent], None]] = None,
    ) -> List[ExtractedEmail]:
        """
        Query SQLite cache for EntryIDs, then fetch full emails from Outlook.
        """
        if on_event:
            on_event(SearchEvent(
                type="cache", message="Querying local index..."
            ))

        # Query cache
        entry_ids = self._cache.search(search_terms, start_date, end_date)

        if on_event:
            on_event(SearchEvent(
                type="cache", total=len(entry_ids), message=f"Found {len(entry_ids)} in cache"
            ))

        if not entry_ids:
            return []

        # Fetch full emails from Outlook by EntryID
        namespace = self._session.get_namespace()
        if not namespace:
            raise RuntimeError("No Outlook namespace available")

        results: List[ExtractedEmail] = []
        seen_ids: set[str] = set()

        for entry_id in entry_ids:
            if entry_id in seen_ids:
                continue

            try:
                msg = namespace.GetItemFromID(entry_id)
                if getattr(msg, "Class", None) != 43:
                    continue

                seen_ids.add(entry_id)
                extracted = self._extract_com_item(msg)
                results.append(extracted)

                if on_event:
                    on_event(SearchEvent(
                        type="match",
                        subject=extracted.subject,
                        sender=extracted.sender_name,
                        date=str(extracted.received_time),
                    ))

            except Exception as exc:
                logger.debug("Dead EntryID %s: %s", entry_id, exc)

                try:
                    self._cache.conn.execute(
                        "DELETE FROM email_index WHERE entry_id = ?",
                        (entry_id,),
                    )
                    self._cache.conn.commit()
                except Exception:
                    pass

                continue

        results.sort(key=lambda m: m.received_time or datetime.min)
        return results

    # ------------------------------------------------------------------
    # DASL QUERY BUILDER
    # ------------------------------------------------------------------
    @staticmethod
    def _build_dasl_query(
        terms: tuple[str, ...],
        start_date: datetime,
        end_date: datetime,
    ) -> str:

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
            if len(term) < 3:
                continue

            fields = [
                f"Subject LIKE '%{term}%'",
                f"From LIKE '%{term}%'",
                f"SenderName LIKE '%{term}%'",
                f"To LIKE '%{term}%'",
                f"CC LIKE '%{term}%'",
            ]

            if "@" in term or "." in term:
                fields.append(f"SenderEmailAddress LIKE '%{term}%'")

            term_conditions.append("(" + " OR ".join(fields) + ")")

        if term_conditions:
            conditions.append("(" + " OR ".join(term_conditions) + ")")

        return " AND ".join(conditions)

    # ------------------------------------------------------------------
    # LIVE SEARCH (with DASL + cache sync)
    # ------------------------------------------------------------------
    def _search(
        self,
        search_terms: List[str],
        start_date: datetime,
        end_date: datetime,
        strategy: FolderStrategy,
        on_event: Optional[Callable[[SearchEvent], None]] = None,
    ) -> List[ExtractedEmail]:

        results: list[ExtractedEmail] = []
        seen_ids: set[str] = set()

        terms = tuple(t.lower().strip() for t in search_terms if t.strip())
        if not terms:
            return []

        has_long_terms = any(len(t) >= 5 for t in terms)
        body_scan_limit = 100
        body_scanned = 0

        current_account = "Unknown"

        for folder in self._iter_folders(strategy):
            try:
                folder_name = getattr(folder, "Name", "Unknown")
                parent = getattr(folder, "Parent", None)
                if parent:
                    current_account = getattr(parent, "Name", current_account)

                # Sync to cache if available (background indexing)
                if self._cache:
                    try:
                        self._cache.sync_folder(folder, current_account, folder_name)
                    except Exception as exc:
                        logger.debug("Cache sync failed for %s: %s", folder_name, exc)

                items = folder.Items

                # DASL pre-filter
                dasl_query = self._build_dasl_query(terms, start_date, end_date)
                try:
                    items = items.Restrict(dasl_query)
                except Exception as exc:
                    logger.debug("DASL failed (%s), falling back to date-only", exc)
                    date_query = (
                        f"[ReceivedTime] >= '{start_date.strftime('%m/%d/%Y %I:%M %p')}' "
                        f"AND [ReceivedTime] <= '{end_date.strftime('%m/%d/%Y %I:%M %p')}'"
                    )
                    items = items.Restrict(date_query)

                # Sort & lightweight columns
                try:
                    items.Sort("[ReceivedTime]", True)
                except Exception:
                    pass

                try:
                    items.SetColumns(
                        "Subject,SenderName,SenderEmailAddress,To,CC,"
                        "ReceivedTime,EntryID,ConversationID,InternetMessageID"
                    )
                except Exception:
                    pass

                total = getattr(items, "Count", 0)
                if total == 0:
                    continue
                if total > 50000:
                    logger.warning("Skipping huge folder: %s (%s items)", folder_name, total)
                    continue

                if on_event:
                    on_event(SearchEvent(
                        type="folder", account=current_account,
                        folder=folder_name, total=total,
                    ))

                # Iterate survivors
                for i in range(1, total + 1):
                    try:
                        msg = items.Item(i)
                    except Exception:
                        continue

                    try:
                        if getattr(msg, "Class", None) != 43:
                            continue

                        entry_id = getattr(msg, "EntryID", None)
                        if not entry_id or entry_id in seen_ids:
                            continue

                        subject = str(getattr(msg, "Subject", "") or "")
                        sender = str(getattr(msg, "SenderName", "") or "")
                        sender_email = str(getattr(msg, "SenderEmailAddress", "") or "")
                        to_field = str(getattr(msg, "To", "") or "")
                        cc_field = str(getattr(msg, "CC", "") or "")

                        text_blob = " ".join([
                            subject, sender, sender_email, to_field, cc_field,
                        ]).lower()

                        matched = any(term in text_blob for term in terms)

                        # Body fallback (capped)
                        if not matched and has_long_terms and body_scanned < body_scan_limit:
                            try:
                                body = str(getattr(msg, "HTMLBody", "") or "").lower()
                                body_scanned += 1
                                matched = any(term in body for term in terms)
                            except Exception:
                                pass

                        if not matched:
                            continue

                        seen_ids.add(entry_id)
                        extracted = self._extract_com_item(msg)
                        results.append(extracted)

                        if on_event:
                            on_event(SearchEvent(
                                type="match", account=current_account,
                                folder=folder_name, subject=extracted.subject,
                                sender=extracted.sender_name,
                                date=str(extracted.received_time),
                            ))

                    except Exception as exc:
                        logger.debug("Message processing failed: %s", exc)

            except Exception as exc:
                logger.debug("Folder search failed: %s", exc)

        results.sort(key=lambda m: m.received_time or datetime.min)
        return results


    # ------------------------------------------------------------------
    # FOLDER WALK
    # ------------------------------------------------------------------
    # FOLDER WALK
    # ------------------------------------------------------------------
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
