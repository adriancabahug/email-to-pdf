"""
Tests for Search Rule Engine.
"""

import enum
from dataclasses import dataclass
from datetime import datetime

import pytest

from src.smsf_context import SMSFContext
from src.advisor_domain_matcher import AdvisorDomainMatcher
from src.search_rule_engine import SearchRuleEngine, RelevanceLevel


class FakeEmail:
    def __init__(
        self,
        sender_email="",
        to_recipients="",
        cc_recipients="",
        subject="",
        body="",
        sender_name="",
    ):
        self.sender_email = sender_email
        self.to_recipients = to_recipients
        self.cc_recipients = cc_recipients
        self.subject = subject
        self.body = body
        self.sender_name = sender_name


class TestSearchRuleEngine:
    def test_strong_match_when_advisor_domain_and_smsf_context_present(self):
        context = SMSFContext(
            smsf_name="Aura Super",
            director_names=["John Smith"],
            director_emails=["john@aura.com.au"],
            advisor_domains=["ventasadvisory.com.au"],
        )
        matcher = AdvisorDomainMatcher()
        engine = SearchRuleEngine(matcher)

        email = FakeEmail(
            sender_email="joel@ventasadvisory.com.au",
            to_recipients="client@aura.com.au",
            cc_recipients="",
            subject="Re: Aura Super contributions",
            body="Hi John, regarding the SMSF...",
        )

        result = engine.is_relevant(email, context)
        assert result == RelevanceLevel.STRONG

    def test_returns_none_when_no_advisor_domain(self):
        context = SMSFContext(
            smsf_name="Aura Super",
            director_names=["John Smith"],
            director_emails=["john@aura.com.au"],
            advisor_domains=["ventasadvisory.com.au"],
        )
        matcher = AdvisorDomainMatcher()
        engine = SearchRuleEngine(matcher)

        email = FakeEmail(
            sender_email="friend@gmail.com",
            to_recipients="client@aura.com.au",
            subject="Aura Super",
            body="Hello",
        )

        result = engine.is_relevant(email, context)
        assert result == RelevanceLevel.NONE

    def test_returns_weak_when_advisor_present_but_no_smsf_context(self):
        context = SMSFContext(
            smsf_name="Aura Super",
            director_names=["John Smith"],
            director_emails=["john@aura.com.au"],
            advisor_domains=["ventasadvisory.com.au"],
        )
        matcher = AdvisorDomainMatcher()
        engine = SearchRuleEngine(matcher)

        email = FakeEmail(
            sender_email="joel@ventasadvisory.com.au",
            to_recipients="colleague@ventasadvisory.com.au",
            subject="Team meeting",
            body="Hi team",
        )

        result = engine.is_relevant(email, context)
        assert result == RelevanceLevel.WEAK

    def test_strong_match_via_to_recipient(self):
        context = SMSFContext(
            smsf_name="Beta Super",
            director_names=["Alice"],
            director_emails=["alice@beta.com"],
            advisor_domains=["exceedia.com.au"],
        )
        matcher = AdvisorDomainMatcher()
        engine = SearchRuleEngine(matcher)

        email = FakeEmail(
            sender_email="bob@beta.com",
            to_recipients="advisor@exceedia.com.au, alice@beta.com",
            subject="Question",
            body="Hello",
        )

        result = engine.is_relevant(email, context)
        assert result == RelevanceLevel.STRONG

    def test_strong_match_via_cc_recipient(self):
        context = SMSFContext(
            smsf_name="Gamma Fund",
            director_names=["Director"],
            director_emails=["dir@gamma.com"],
            advisor_domains=["exceedia.com.au"],
        )
        matcher = AdvisorDomainMatcher()
        engine = SearchRuleEngine(matcher)

        email = FakeEmail(
            sender_email="person@other.com",
            to_recipients="main@exceedia.com.au",
            cc_recipients="dir@gamma.com",
            subject="Gamma Fund Update",
            body="Info about the fund",
        )

        result = engine.is_relevant(email, context)
        assert result == RelevanceLevel.STRONG

    def test_weak_match_advisor_only(self):
        context = SMSFContext(
            smsf_name="Test Fund",
            director_names=["Director"],
            director_emails=["dir@test.com"],
            advisor_domains=["ventasadvisory.com.au"],
        )
        matcher = AdvisorDomainMatcher()
        engine = SearchRuleEngine(matcher)

        email = FakeEmail(
            sender_email="staff@ventasadvisory.com.au",
            to_recipients="colleague@ventasadvisory.com.au",
            subject="Internal",
            body="Team update",
        )

        result = engine.is_relevant(email, context)
        assert result == RelevanceLevel.WEAK

    def test_case_insensitive_matching(self):
        context = SMSFContext(
            smsf_name="Aura Super",
            director_names=["John Doe"],
            director_emails=["john@test.com"],
            advisor_domains=["ventasadvisory.com.au"],
        )
        matcher = AdvisorDomainMatcher()
        engine = SearchRuleEngine(matcher)

        email = FakeEmail(
            sender_email="USER@VENTASADVISORY.COM.AU",
            to_recipients="DIRECTOR@TEST.COM",
            subject="aura super question",
            body="JOHN DOE",
        )

        result = engine.is_relevant(email, context)
        assert result == RelevanceLevel.STRONG

    def test_smsf_name_in_subject_matches(self):
        context = SMSFContext(
            smsf_name="Aura Super",
            director_names=[],
            director_emails=[],
            advisor_domains=["ventasadvisory.com.au"],
        )
        matcher = AdvisorDomainMatcher()
        engine = SearchRuleEngine(matcher)

        email = FakeEmail(
            sender_email="user@ventasadvisory.com.au",
            to_recipients="other@ventasadvisory.com.au",
            subject="Aura Super - Question",
            body="Hello",
        )

        result = engine.is_relevant(email, context)
        assert result == RelevanceLevel.STRONG

    def test_smsf_name_in_body_matches(self):
        context = SMSFContext(
            smsf_name="Beta Fund",
            director_names=[],
            director_emails=[],
            advisor_domains=["exceedia.com.au"],
        )
        matcher = AdvisorDomainMatcher()
        engine = SearchRuleEngine(matcher)

        email = FakeEmail(
            sender_email="user@exceedia.com.au",
            to_recipients="other@exceedia.com.au",
            subject="Question",
            body="Regarding Beta Fund compliance",
        )

        result = engine.is_relevant(email, context)
        assert result == RelevanceLevel.STRONG