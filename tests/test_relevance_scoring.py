"""
Tests for Relevance Scoring Engine.
"""

from datetime import datetime

import pytest

from src.smsf_context import SMSFContext
from src.advisor_domain_matcher import AdvisorDomainMatcher
from src.search_rule_engine import SearchRuleEngine, RelevanceLevel
from src.thread_reconstruction import ThreadReconstructionEngine, Thread
from src.relevance_scoring import RelevanceScoringEngine


class MockEmail:
    def __init__(
        self,
        subject="",
        conversation_id=None,
        sent_on=None,
        sender_email="",
        to_recipients="",
        cc_recipients="",
        body="",
    ):
        self.subject = subject
        self.conversation_id = conversation_id
        self.sent_on = sent_on
        self.sender_email = sender_email
        self.to_recipients = to_recipients
        self.cc_recipients = cc_recipients
        self.body = body

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
    def To(self):
        return self.to_recipients

    @property
    def CC(self):
        return self.cc_recipients

    @property
    def Body(self):
        return self.body


class TestRelevanceScoringEmail:
    def test_score_email_strong_match(self):
        context = SMSFContext(
            smsf_name="Aura Super",
            director_names=["John"],
            director_emails=["john@aura.com"],
            advisor_domains=["ventasadvisory.com.au"],
        )
        matcher = AdvisorDomainMatcher()
        search_engine = SearchRuleEngine(matcher)
        scoring = RelevanceScoringEngine(search_engine)

        email = MockEmail(
            sender_email="joel@ventasadvisory.com.au",
            to_recipients="john@aura.com",
            subject="Re: Aura Super",
            body="Hello",
        )

        result = scoring.score_email(email, context)
        assert result == RelevanceLevel.STRONG

    def test_score_email_weak_match(self):
        context = SMSFContext(
            smsf_name="Aura Super",
            director_names=["John"],
            director_emails=["john@aura.com"],
            advisor_domains=["ventasadvisory.com.au"],
        )
        matcher = AdvisorDomainMatcher()
        search_engine = SearchRuleEngine(matcher)
        scoring = RelevanceScoringEngine(search_engine)

        email = MockEmail(
            sender_email="joel@ventasadvisory.com.au",
            to_recipients="colleague@ventasadvisory.com.au",
            subject="Team meeting",
            body="Hi team",
        )

        result = scoring.score_email(email, context)
        assert result == RelevanceLevel.WEAK

    def test_is_strong_match_returns_bool(self):
        context = SMSFContext(
            smsf_name="Test Fund",
            director_names=["Director"],
            director_emails=["dir@test.com"],
            advisor_domains=["ventasadvisory.com.au"],
        )
        matcher = AdvisorDomainMatcher()
        search_engine = SearchRuleEngine(matcher)
        scoring = RelevanceScoringEngine(search_engine)

        email = MockEmail(
            sender_email="user@ventasadvisory.com.au",
            to_recipients="dir@test.com",
            subject="Test",
            body="Hello",
        )

        assert scoring.is_strong_match(email, context) is True


class TestRelevanceScoringThread:
    def test_thread_with_strong_email_is_strong(self):
        context = SMSFContext(
            smsf_name="Aura Super",
            director_names=["John"],
            director_emails=["john@aura.com"],
            advisor_domains=["ventasadvisory.com.au"],
        )
        matcher = AdvisorDomainMatcher()
        search_engine = SearchRuleEngine(matcher)
        scoring = RelevanceScoringEngine(search_engine)

        emails = [
            MockEmail(
                sender_email="joel@ventasadvisory.com.au",
                to_recipients="colleague@ventasadvisory.com.au",
                conversation_id="thread-1",
                subject="Team meeting",
                body="Hi team",
                sent_on=datetime(2026, 1, 2),
            ),
            MockEmail(
                sender_email="joel@ventasadvisory.com.au",
                to_recipients="john@aura.com",
                conversation_id="thread-1",
                subject="Re: Team meeting",
                body="Hello John",
                sent_on=datetime(2026, 1, 3),
            ),
        ]

        thread = Thread(
            thread_id="thread-1",
            emails=emails,
            root_email=emails[0],
        )

        result = scoring.score_thread(thread, context)
        assert result == RelevanceLevel.STRONG

    def test_thread_with_weak_only_is_weak(self):
        context = SMSFContext(
            smsf_name="Aura Super",
            director_names=["John"],
            director_emails=["john@aura.com"],
            advisor_domains=["ventasadvisory.com.au"],
        )
        matcher = AdvisorDomainMatcher()
        search_engine = SearchRuleEngine(matcher)
        scoring = RelevanceScoringEngine(search_engine)

        emails = [
            MockEmail(
                sender_email="joel@ventasadvisory.com.au",
                to_recipients="colleague@ventasadvisory.com.au",
                conversation_id="thread-1",
                subject="Internal",
                body="Team update",
                sent_on=datetime(2026, 1, 2),
            ),
            MockEmail(
                sender_email="staff@ventasadvisory.com.au",
                to_recipients="other@ventasadvisory.com.au",
                conversation_id="thread-1",
                subject="Re: Internal",
                body="Got it",
                sent_on=datetime(2026, 1, 3),
            ),
        ]

        thread = Thread(
            thread_id="thread-1",
            emails=emails,
            root_email=emails[0],
        )

        result = scoring.score_thread(thread, context)
        assert result == RelevanceLevel.WEAK

    def test_thread_with_different_relevances_takes_max(self):
        context = SMSFContext(
            smsf_name="Aura Super",
            director_names=["John"],
            director_emails=["john@aura.com"],
            advisor_domains=["ventasadvisory.com.au"],
        )
        matcher = AdvisorDomainMatcher()
        search_engine = SearchRuleEngine(matcher)
        scoring = RelevanceScoringEngine(search_engine)

        emails = [
            MockEmail(
                sender_email="joel@ventasadvisory.com.au",
                to_recipients="colleague@ventasadvisory.com.au",
                conversation_id="thread-1",
                subject="Internal",
                body="Team update",
                sent_on=datetime(2026, 1, 2),
            ),
            MockEmail(
                sender_email="joel@ventasadvisory.com.au",
                to_recipients="john@aura.com",
                conversation_id="thread-1",
                subject="Re: Internal",
                body="Also need info",
                sent_on=datetime(2026, 1, 3),
            ),
        ]

        thread = Thread(
            thread_id="thread-1",
            emails=emails,
            root_email=emails[0],
        )

        result = scoring.score_thread(thread, context)
        assert result == RelevanceLevel.STRONG


class TestRelevanceFiltering:
    def test_exclude_weak_by_default(self):
        context = SMSFContext(
            smsf_name="Test Fund",
            director_names=["Director"],
            director_emails=["dir@test.com"],
            advisor_domains=["advisor.com"],
        )
        matcher = AdvisorDomainMatcher()
        search_engine = SearchRuleEngine(matcher)
        scoring = RelevanceScoringEngine(search_engine)

        email = MockEmail(
            sender_email="user@advisor.com",
            to_recipients="colleague@advisor.com",
            subject="Internal",
            body="Team update",
        )

        assert scoring.should_exclude(email, context) is True

    def test_include_strong_by_default(self):
        context = SMSFContext(
            smsf_name="Test Fund",
            director_names=["Director"],
            director_emails=["dir@test.com"],
            advisor_domains=["ventasadvisory.com.au"],
        )
        matcher = AdvisorDomainMatcher()
        search_engine = SearchRuleEngine(matcher)
        scoring = RelevanceScoringEngine(search_engine)

        email = MockEmail(
            sender_email="user@ventasadvisory.com.au",
            to_recipients="dir@test.com",
            subject="Question",
            body="Hello",
        )

        assert scoring.should_exclude(email, context) is False