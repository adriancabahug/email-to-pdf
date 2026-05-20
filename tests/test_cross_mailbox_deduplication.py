"""
Tests for Cross-Mailbox Deduplication.
"""

import hashlib
from datetime import datetime, timedelta

import pytest

from src.deduplication import CrossMailboxDeduplicator


class MockEmail:
    def __init__(
        self,
        internet_message_id=None,
        sender_email="",
        subject="",
        body="",
        sent_on=None,
        entry_id="",
    ):
        self.internet_message_id = internet_message_id
        self.sender_email = sender_email
        self.subject = subject
        self.body = body
        self.sent_on = sent_on
        self.entry_id = entry_id

    @property
    def InternetMessageID(self):
        return self.internet_message_id

    @property
    def SenderEmailAddress(self):
        return self.sender_email

    @property
    def Subject(self):
        return self.subject

    @property
    def Body(self):
        return self.body

    @property
    def SentOn(self):
        return self.sent_on

    @property
    def EntryID(self):
        return self.entry_id


class TestDeduplicationByInternetMessageID:
    def test_deduplicate_by_internet_message_id(self):
        dedup = CrossMailboxDeduplicator()

        emails = [
            MockEmail(
                internet_message_id="<msg-123@example.com>",
                sender_email="a@test.com",
                subject="Test",
                body="Hello",
                sent_on=datetime(2026, 1, 1),
            ),
            MockEmail(
                internet_message_id="<msg-123@example.com>",
                sender_email="a@test.com",
                subject="Test",
                body="Hello",
                sent_on=datetime(2026, 1, 1),
            ),
        ]

        result = dedup.deduplicate(emails)

        assert len(result) == 1

    def test_different_internet_message_ids_kept(self):
        dedup = CrossMailboxDeduplicator()

        emails = [
            MockEmail(
                internet_message_id="<msg-1@example.com>",
                sender_email="a@test.com",
                subject="Test 1",
                body="Hello 1",
                sent_on=datetime(2026, 1, 1),
            ),
            MockEmail(
                internet_message_id="<msg-2@example.com>",
                sender_email="b@test.com",
                subject="Test 2",
                body="Hello 2",
                sent_on=datetime(2026, 1, 2),
            ),
        ]

        result = dedup.deduplicate(emails)

        assert len(result) == 2


class TestDeduplicationFallback:
    def test_fallback_when_no_internet_message_id(self):
        dedup = CrossMailboxDeduplicator()

        emails = [
            MockEmail(
                internet_message_id=None,
                sender_email="a@test.com",
                subject="Test",
                body="Hello",
                sent_on=datetime(2026, 1, 1),
            ),
            MockEmail(
                internet_message_id=None,
                sender_email="a@test.com",
                subject="Test",
                body="Hello",
                sent_on=datetime(2026, 1, 1),
            ),
        ]

        result = dedup.deduplicate(emails)

        assert len(result) == 1

    def test_different_body_hash_not_deduplicated(self):
        dedup = CrossMailboxDeduplicator()

        emails = [
            MockEmail(
                internet_message_id=None,
                sender_email="a@test.com",
                subject="Test",
                body="Hello",
                sent_on=datetime(2026, 1, 1),
            ),
            MockEmail(
                internet_message_id=None,
                sender_email="a@test.com",
                subject="Test",
                body="Different",
                sent_on=datetime(2026, 1, 1),
            ),
        ]

        result = dedup.deduplicate(emails)

        assert len(result) == 2

    def test_different_timestamp_not_deduplicated(self):
        dedup = CrossMailboxDeduplicator()

        emails = [
            MockEmail(
                internet_message_id=None,
                sender_email="a@test.com",
                subject="Test",
                body="Hello",
                sent_on=datetime(2026, 1, 1),
            ),
            MockEmail(
                internet_message_id=None,
                sender_email="a@test.com",
                subject="Test",
                body="Hello",
                sent_on=datetime(2026, 1, 1, 1, 0, 0),
            ),
        ]

        result = dedup.deduplicate(emails)

        assert len(result) == 2


class TestDeduplicationKey:
    def test_get_key_from_internet_message_id(self):
        dedup = CrossMailboxDeduplicator()

        email = MockEmail(
            internet_message_id="<unique-123@example.com>",
            sender_email="test@example.com",
            subject="Test",
            body="Hello",
        )

        key = dedup.get_deduplication_key(email)

        assert "unique-123" in key

    def test_get_key_fallback_to_heuristics(self):
        dedup = CrossMailboxDeduplicator()

        email = MockEmail(
            internet_message_id=None,
            sender_email="test@example.com",
            subject="Test Subject",
            body="Test body",
            sent_on=datetime(2026, 1, 1),
        )

        key = dedup.get_deduplication_key(email)

        assert key is not None
        assert len(key) > 0


class TestCrossMailboxScenarios:
    def test_same_email_different_accounts(self):
        dedup = CrossMailboxDeduplicator()

        emails = [
            MockEmail(
                internet_message_id="<msg-abc@example.com>",
                sender_email="a@test.com",
                subject="Test",
                body="Hello",
                sent_on=datetime(2026, 1, 1),
                entry_id="entry-1",
            ),
            MockEmail(
                internet_message_id="<msg-abc@example.com>",
                sender_email="a@test.com",
                subject="Test",
                body="Hello",
                sent_on=datetime(2026, 1, 1),
                entry_id="entry-2",
            ),
        ]

        result = dedup.deduplicate(emails)

        assert len(result) == 1

    def test_preserves_original_order_for_unique(self):
        dedup = CrossMailboxDeduplicator()

        emails = [
            MockEmail(
                internet_message_id="<msg-1@example.com>",
                sender_email="a@test.com",
                subject="First",
                body="Body 1",
                sent_on=datetime(2026, 1, 1),
            ),
            MockEmail(
                internet_message_id="<msg-2@example.com>",
                sender_email="b@test.com",
                subject="Second",
                body="Body 2",
                sent_on=datetime(2026, 1, 2),
            ),
            MockEmail(
                internet_message_id="<msg-1@example.com>",
                sender_email="a@test.com",
                subject="First",
                body="Body 1",
                sent_on=datetime(2026, 1, 1),
            ),
        ]

        result = dedup.deduplicate(emails)

        assert len(result) == 2
        assert result[0].subject == "First"
        assert result[1].subject == "Second"