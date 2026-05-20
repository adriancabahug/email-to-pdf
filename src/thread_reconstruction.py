"""
Thread Reconstruction Engine - Reconstruct conversation threads from emails.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Thread:
    thread_id: str
    emails: List[Any]
    root_email: Any


class ThreadReconstructionEngine:
    def reconstruct_threads(self, emails: List[Any]) -> List[Thread]:
        if not emails:
            return []

        threads_by_id: Dict[str, List[Any]] = {}

        for email in emails:
            thread_id = self.get_thread_id(email)
            if thread_id not in threads_by_id:
                threads_by_id[thread_id] = []
            threads_by_id[thread_id].append(email)

        result = []
        for thread_id, thread_emails in threads_by_id.items():
            sorted_emails = self._sort_by_date(thread_emails)
            root = sorted_emails[0] if sorted_emails else None
            result.append(Thread(
                thread_id=thread_id,
                emails=sorted_emails,
                root_email=root,
            ))

        return result

    def get_thread_id(self, email: Any) -> str:
        conv_id = getattr(email, "ConversationID", None)
        if conv_id:
            return str(conv_id)

        subject = getattr(email, "Subject", "")
        if subject:
            return self._normalize_subject(subject)

        return "unknown-thread"

    def get_thread_emails(self, emails: List[Any], thread_id: str) -> List[Any]:
        thread_emails = [e for e in emails if self.get_thread_id(e) == thread_id]
        return self._sort_by_date(thread_emails)

    def _normalize_subject(self, subject: str) -> str:
        normalized = subject.lower().strip()

        re_prefixes = [
            r"^re:\s*",
            r"^fw:\s*",
            r"^fwd:\s*",
            r"^re\[?\d*\]?:\s*",
        ]
        for prefix in re_prefixes:
            normalized = re.sub(prefix, "", normalized, flags=re.IGNORECASE)

        normalized = re.sub(r"\s+", " ", normalized)
        normalized = re.sub(r"[^\w\s]", "", normalized)

        return normalized.strip()

    def _sort_by_date(self, emails: List[Any]) -> List[Any]:
        def get_date(email: Any) -> datetime:
            sent_on = getattr(email, "SentOn", None)
            if sent_on:
                if isinstance(sent_on, datetime):
                    return sent_on
                if hasattr(sent_on, "year"):
                    return sent_on
            return datetime.min

        return sorted(emails, key=get_date)