"""
Cross-Mailbox Deduplication - Prevents duplicate emails across Outlook accounts.
"""

import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional


class CrossMailboxDeduplicator:
    def deduplicate(self, emails: List[Any]) -> List[Any]:
        if not emails:
            return []

        seen_keys: Dict[str, Any] = {}
        result: List[Any] = []

        for email in emails:
            key = self.get_deduplication_key(email)
            if key not in seen_keys:
                seen_keys[key] = email
                result.append(email)

        return result

    def get_deduplication_key(self, email: Any) -> str:
        msg_id = self._get_internet_message_id(email)
        if msg_id:
            return f"msgid:{msg_id}"

        return self._get_fallback_key(email)

    def _get_internet_message_id(self, email: Any) -> Optional[str]:
        prop = getattr(email, "InternetMessageID", None)
        if prop:
            return str(prop).strip().strip("<>")
        return None

    def _get_fallback_key(self, email: Any) -> str:
        parts = []

        sender = getattr(email, "SenderEmailAddress", None)
        if sender:
            parts.append(f"sender:{str(sender).lower()}")

        subject = getattr(email, "Subject", None)
        if subject:
            normalized = self._normalize_subject(str(subject))
            parts.append(f"subject:{normalized}")

        body = getattr(email, "Body", None)
        if body:
            body_hash = hashlib.md5(str(body).encode('utf-8')).hexdigest()
            parts.append(f"body:{body_hash}")

        sent_on = getattr(email, "SentOn", None)
        if sent_on:
            if isinstance(sent_on, datetime):
                ts = sent_on.replace(second=0, microsecond=0)
                parts.append(f"time:{ts.isoformat()}")

        if not parts:
            entry_id = getattr(email, "EntryID", None)
            if entry_id:
                return f"entry:{entry_id}"
            return f"unknown:{id(email)}"

        return "|".join(parts)

    def _normalize_subject(self, subject: str) -> str:
        import re
        normalized = subject.lower().strip()
        re_prefixes = [
            r"^re:\s*",
            r"^fw:\s*",
            r"^fwd:\s*",
        ]
        for prefix in re_prefixes:
            normalized = re.sub(prefix, "", normalized, flags=re.IGNORECASE)
        normalized = " ".join(normalized.split())
        return normalized