"""SQLite metadata cache for sub-second email searches on subsequent runs."""

import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

logger = logging.getLogger(__name__)


class EmailMetadataCache:
    """
    One-time index build, then sub-second searches forever.
    Only stores metadata - NO email bodies.
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = sqlite3.connect(
            str(db_path),
            check_same_thread=False,
        )
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self._init_tables()

    def _init_tables(self) -> None:
        """Create tables and indexes if they don't exist."""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS email_index (
                entry_id TEXT PRIMARY KEY,
                account TEXT NOT NULL,
                folder TEXT NOT NULL,
                subject TEXT,
                sender_name TEXT,
                sender_email TEXT,
                to_recipients TEXT,
                cc_recipients TEXT,
                received_time TIMESTAMP NOT NULL,
                conversation_id TEXT,
                internet_message_id TEXT,
                message_class TEXT,
                indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_received ON email_index(received_time);
            CREATE INDEX IF NOT EXISTS idx_sender_email ON email_index(sender_email);
            CREATE INDEX IF NOT EXISTS idx_conversation ON email_index(conversation_id);
            CREATE INDEX IF NOT EXISTS idx_account_folder ON email_index(account, folder);
            CREATE INDEX IF NOT EXISTS idx_subject ON email_index(subject);
            CREATE INDEX IF NOT EXISTS idx_combined ON email_index(received_time, sender_email, subject);

            CREATE TABLE IF NOT EXISTS sync_log (
                account TEXT NOT NULL,
                folder TEXT NOT NULL,
                last_sync TIMESTAMP NOT NULL,
                item_count INTEGER,
                PRIMARY KEY (account, folder)
            );
        """)
        self.conn.commit()

    # ------------------------------------------------------------------
    # SEARCH (the fast path)
    # ------------------------------------------------------------------
    def search(
        self,
        terms: List[str],
        start_date: datetime,
        end_date: datetime,
    ) -> List[str]:
        """
        Return EntryIDs matching criteria. Sub-second on indexed data.
        """
        if not terms:
            return []

        conditions = ["received_time >= ? AND received_time <= ?"]
        params: List[Any] = [start_date, end_date]

        term_conditions = []
        for raw_term in terms:
            term = f"%{raw_term.lower()}%"
            term_conditions.append(
                "(subject LIKE ? OR sender_name LIKE ? OR sender_email LIKE ? "
                "OR to_recipients LIKE ? OR cc_recipients LIKE ?)"
            )
            params.extend([term] * 5)

        if term_conditions:
            conditions.append("(" + " OR ".join(term_conditions) + ")")

        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT entry_id, received_time
            FROM email_index
            WHERE {where_clause}
            ORDER BY received_time DESC
        """

        try:
            cursor = self.conn.execute(query, params)
            rows = cursor.fetchall()
            logger.info("Cache query returned %d results", len(rows))
            return [row["entry_id"] for row in rows]
        except Exception as exc:
            logger.error("Cache search failed: %s", exc)
            return []

    # ------------------------------------------------------------------
    # SYNC (the one-time slow path)
    # ------------------------------------------------------------------
    def sync_folder(
        self,
        folder: Any,
        account_name: str,
        folder_name: str,
    ) -> int:
        """
        Incremental sync: only index emails newer than last sync.
        Returns number of new emails indexed.
        """
        last_sync = self._get_last_sync(account_name, folder_name)

        try:
            items = folder.Items
            items.Sort("[ReceivedTime]", True)

            # Only get emails since last sync
            if last_sync and last_sync > datetime(1970, 1, 1):
                date_query = (
                    f"[ReceivedTime] > '{last_sync.strftime('%m/%d/%Y %I:%M %p')}'"
                )
                try:
                    items = items.Restrict(date_query)
                except Exception as exc:
                    logger.debug("Sync date restrict failed: %s", exc)

            # Lightweight columns only
            try:
                items.SetColumns(
                    "Subject,"
                    "SenderName,"
                    "SenderEmailAddress,"
                    "To,"
                    "CC,"
                    "ReceivedTime,"
                    "EntryID,"
                    "ConversationID,"
                    "InternetMessageID,"
                    "MessageClass"
                )
            except Exception:
                pass

            total = getattr(items, "Count", 0)
            if total == 0:
                return 0

            indexed = 0
            newest_time = last_sync if isinstance(last_sync, datetime) else datetime.min

            for i in range(1, min(total + 1, 10001)):  # Cap at 10k per sync
                try:
                    msg = items.Item(i)
                    received = getattr(msg, "ReceivedTime", None)
                    if not received:
                        continue

                    if isinstance(received, datetime) and received > newest_time:
                        newest_time = received

                    self._insert_email(msg, account_name, folder_name)
                    indexed += 1

                except Exception as exc:
                    logger.debug("Sync item failed: %s", exc)
                    continue

            self._update_sync_log(account_name, folder_name, newest_time, indexed)
            self.conn.commit()

            logger.info(
                "Synced %s/%s: %d new emails (total in folder: %d)",
                account_name,
                folder_name,
                indexed,
                total,
            )
            return indexed

        except Exception as exc:
            logger.error("Folder sync failed %s/%s: %s", account_name, folder_name, exc)
            return 0

    def _insert_email(self, msg: Any, account: str, folder: str) -> None:
        """Insert or replace a single email record."""
        try:
            entry_id = getattr(msg, "EntryID", None)
            if not entry_id:
                return

            received = getattr(msg, "ReceivedTime", None)
            if not received:
                return

            if hasattr(received, "year"):
                received_dt = datetime(
                    received.year, received.month, received.day,
                    received.hour, received.minute, received.second
                )
            else:
                received_dt = received

            self.conn.execute(
                """
                INSERT OR REPLACE INTO email_index
                (entry_id, account, folder, subject, sender_name, sender_email,
                 to_recipients, cc_recipients, received_time, conversation_id,
                 internet_message_id, message_class)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry_id,
                    account,
                    folder,
                    str(getattr(msg, "Subject", "") or ""),
                    str(getattr(msg, "SenderName", "") or ""),
                    str(getattr(msg, "SenderEmailAddress", "") or ""),
                    str(getattr(msg, "To", "") or ""),
                    str(getattr(msg, "CC", "") or ""),
                    received_dt,
                    str(getattr(msg, "ConversationID", "") or ""),
                    str(getattr(msg, "InternetMessageID", "") or ""),
                    str(getattr(msg, "MessageClass", "") or ""),
                ),
            )
        except Exception as exc:
            logger.debug("Insert failed: %s", exc)

    def _get_last_sync(self, account: str, folder: str) -> Optional[datetime]:
        cursor = self.conn.execute(
            "SELECT last_sync FROM sync_log WHERE account = ? AND folder = ?",
            (account, folder),
        )
        row = cursor.fetchone()
        if row:
            val = row["last_sync"]
            if isinstance(val, str):
                try:
                    return datetime.fromisoformat(val)
                except (ValueError, TypeError):
                    return None
            return val
        return None

    def _update_sync_log(
        self,
        account: str,
        folder: str,
        last_sync: datetime,
        item_count: int,
    ) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO sync_log (account, folder, last_sync, item_count)
            VALUES (?, ?, ?, ?)
            """,
            (account, folder, last_sync, item_count),
        )

    def close(self) -> None:
        self.conn.close()

    def get_stats(self) -> dict:
        """Return cache statistics."""
        cursor = self.conn.execute("SELECT COUNT(*) as total FROM email_index")
        total = cursor.fetchone()["total"]

        cursor = self.conn.execute(
            "SELECT account, folder, last_sync FROM sync_log ORDER BY account, folder"
        )
        folders = [dict(row) for row in cursor.fetchall()]

        return {"total_emails": total, "folders_synced": len(folders), "folders": folders}
