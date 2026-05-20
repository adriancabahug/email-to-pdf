"""
Tests for Thread Reconstruction Engine.
"""

from dataclasses import dataclass, field
from datetime import datetime

import pytest

from src.thread_reconstruction import ThreadReconstructionEngine, Thread


class MockEmail:
    def __init__(
        self,
        subject="",
        conversation_id=None,
        sent_on=None,
        sender_email="",
        body="",
        in_reply_to="",
    ):
        self.subject = subject
        self.conversation_id = conversation_id
        self.sent_on = sent_on
        self.sender_email = sender_email
        self.body = body
        self.in_reply_to = in_reply_to

    @property
    def Subject(self):
        return self.subject

    @property
    def ConversationID(self):
        return self.conversation_id

    @property
    def SentOn(self):
        return self.sent_on

    @property
    def SenderEmailAddress(self):
        return self.sender_email

    @property
    def Body(self):
        return self.body


class TestThreadReconstructionByConversationID:
    def test_groups_by_conversation_id(self):
        engine = ThreadReconstructionEngine()

        emails = [
            MockEmail(
                subject="Re: Question",
                conversation_id="conv-123",
                sent_on=datetime(2026, 1, 1),
            ),
            MockEmail(
                subject="Re: Question",
                conversation_id="conv-123",
                sent_on=datetime(2026, 1, 2),
            ),
            MockEmail(
                subject="Different",
                conversation_id="conv-456",
                sent_on=datetime(2026, 1, 3),
            ),
        ]

        threads = engine.reconstruct_threads(emails)

        assert len(threads) == 2
        thread_ids = {t.thread_id for t in threads}
        assert "conv-123" in thread_ids
        assert "conv-456" in thread_ids

    def test_sorts_within_thread_chronologically(self):
        engine = ThreadReconstructionEngine()

        emails = [
            MockEmail(
                subject="Re: Help",
                conversation_id="thread-1",
                sent_on=datetime(2026, 3, 1),
            ),
            MockEmail(
                subject="Re: Help",
                conversation_id="thread-1",
                sent_on=datetime(2026, 1, 1),
            ),
            MockEmail(
                subject="Re: Help",
                conversation_id="thread-1",
                sent_on=datetime(2026, 2, 1),
            ),
        ]

        threads = engine.reconstruct_threads(emails)

        assert len(threads) == 1
        thread = threads[0]
        dates = [e.sent_on for e in thread.emails]
        assert dates == sorted(dates)


class TestThreadReconstructionFallback:
    def test_fallback_to_subject_normalization(self):
        engine = ThreadReconstructionEngine()

        emails = [
            MockEmail(
                subject="Re: Question",
                conversation_id=None,
                sent_on=datetime(2026, 1, 1),
            ),
            MockEmail(
                subject="Question",
                conversation_id=None,
                sent_on=datetime(2026, 1, 2),
            ),
            MockEmail(
                subject="Re: Question",
                conversation_id=None,
                sent_on=datetime(2026, 1, 3),
            ),
        ]

        threads = engine.reconstruct_threads(emails)

        assert len(threads) == 1

    def test_different_subjects_separate_threads(self):
        engine = ThreadReconstructionEngine()

        emails = [
            MockEmail(
                subject="Question A",
                conversation_id=None,
                sent_on=datetime(2026, 1, 1),
            ),
            MockEmail(
                subject="Question B",
                conversation_id=None,
                sent_on=datetime(2026, 1, 2),
            ),
        ]

        threads = engine.reconstruct_threads(emails)

        assert len(threads) == 2


class TestThreadReconstructionEdgeCases:
    def test_handles_missing_conversation_id(self):
        engine = ThreadReconstructionEngine()

        emails = [
            MockEmail(
                subject="Email 1",
                conversation_id=None,
                sent_on=datetime(2026, 1, 1),
            ),
            MockEmail(
                subject="Email 2",
                conversation_id="abc-123",
                sent_on=datetime(2026, 1, 2),
            ),
        ]

        threads = engine.reconstruct_threads(emails)

        assert len(threads) == 2

    def test_forwards_same_subject_grouped(self):
        engine = ThreadReconstructionEngine()

        emails = [
            MockEmail(
                subject="Fw: Question",
                conversation_id=None,
                sent_on=datetime(2026, 1, 1),
            ),
            MockEmail(
                subject="Question",
                conversation_id=None,
                sent_on=datetime(2026, 1, 2),
            ),
        ]

        threads = engine.reconstruct_threads(emails)

        assert len(threads) == 1

    def test_root_email_is_first_chronologically(self):
        engine = ThreadReconstructionEngine()

        emails = [
            MockEmail(
                subject="Re: Help",
                conversation_id="thread-1",
                sent_on=datetime(2026, 3, 1),
            ),
            MockEmail(
                subject="Help",
                conversation_id="thread-1",
                sent_on=datetime(2026, 1, 1),
            ),
            MockEmail(
                subject="Re: Help",
                conversation_id="thread-1",
                sent_on=datetime(2026, 2, 1),
            ),
        ]

        threads = engine.reconstruct_threads(emails)

        assert len(threads) == 1
        assert threads[0].root_email.sent_on == datetime(2026, 1, 1)


class TestThreadIDExtraction:
    def test_get_thread_id_from_conversation(self):
        engine = ThreadReconstructionEngine()
        email = MockEmail(
            subject="Test",
            conversation_id="conv-789",
        )
        thread_id = engine.get_thread_id(email)
        assert thread_id == "conv-789"

    def test_get_thread_id_fallback_to_normalized_subject(self):
        engine = ThreadReconstructionEngine()
        email = MockEmail(
            subject="Re: Test Message",
            conversation_id=None,
        )
        thread_id = engine.get_thread_id(email)
        assert "test message" in thread_id.lower()

    def test_get_thread_emails_returns_ordered_list(self):
        engine = ThreadReconstructionEngine()

        emails = [
            MockEmail(
                subject="Thread",
                conversation_id="thread-1",
                sent_on=datetime(2026, 2, 1),
            ),
            MockEmail(
                subject="Thread",
                conversation_id="thread-1",
                sent_on=datetime(2026, 1, 1),
            ),
        ]

        result = engine.get_thread_emails(emails, "thread-1")

        assert len(result) == 2
        assert result[0].sent_on == datetime(2026, 1, 1)
        assert result[1].sent_on == datetime(2026, 2, 1)