"""
Tests for Advisor PDF Grouping Engine.
"""

from datetime import datetime
from pathlib import Path

import pytest

from src.smsf_context import SMSFContext
from src.advisor_domain_matcher import AdvisorDomainMatcher
from src.search_rule_engine import SearchRuleEngine, RelevanceLevel
from src.advisor_pdf_grouping import AdvisorPDFGroupingEngine


class MockEmail:
    def __init__(
        self,
        sender_email="",
        to_recipients="",
        cc_recipients="",
        subject="",
        body="",
        sent_on=None,
    ):
        self.sender_email = sender_email
        self.to_recipients = to_recipients
        self.cc_recipients = cc_recipients
        self.subject = subject
        self.body = body
        self.sent_on = sent_on

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
    def Subject(self):
        return self.subject

    @property
    def Body(self):
        return self.body

    @property
    def SentOn(self):
        return self.sent_on


class TestGroupEmailsByOrganization:
    def test_groups_by_organization_not_individual(self):
        context = SMSFContext(
            smsf_name="Aura Super",
            director_names=["John"],
            director_emails=["john@aura.com"],
            advisor_domains=["ventasadvisory.com.au", "exceedia.com.au"],
        )
        matcher = AdvisorDomainMatcher()
        search_engine = SearchRuleEngine(matcher)
        grouping = AdvisorPDFGroupingEngine(search_engine)

        emails = [
            MockEmail(
                sender_email="joel@ventasadvisory.com.au",
                to_recipients="john@aura.com",
                subject="Question",
                body="Hello",
                sent_on=datetime(2026, 1, 1),
            ),
            MockEmail(
                sender_email="mary@ventasadvisory.com.au",
                to_recipients="john@aura.com",
                subject="Another",
                body="Hi",
                sent_on=datetime(2026, 1, 2),
            ),
            MockEmail(
                sender_email="bob@exceedia.com.au",
                to_recipients="john@aura.com",
                subject="Exceedia matter",
                body="Info",
                sent_on=datetime(2026, 1, 3),
            ),
        ]

        groups = grouping.group_emails(emails, context, matcher)

        org_names = list(groups.keys())
        assert "Ventas - Aura Super" in org_names
        assert "Exceedia - Aura Super" in org_names
        assert len(groups) == 2

    def test_groups_ventas_contains_all_ventas_emails(self):
        context = SMSFContext(
            smsf_name="Aura Super",
            director_names=["John"],
            director_emails=["john@aura.com"],
            advisor_domains=["ventasadvisory.com.au"],
        )
        matcher = AdvisorDomainMatcher()
        search_engine = SearchRuleEngine(matcher)
        grouping = AdvisorPDFGroupingEngine(search_engine)

        emails = [
            MockEmail(
                sender_email="joel@ventasadvisory.com.au",
                to_recipients="john@aura.com",
                subject="Q1",
                body="A",
                sent_on=datetime(2026, 1, 1),
            ),
            MockEmail(
                sender_email="mary@ventasadvisory.com.au",
                to_recipients="john@aura.com",
                subject="Q2",
                body="B",
                sent_on=datetime(2026, 1, 2),
            ),
        ]

        groups = grouping.group_emails(emails, context, matcher)

        assert "Ventas - Aura Super" in groups
        group = groups["Ventas - Aura Super"]
        assert len(group) == 2

    def test_filters_out_irrelevant_emails(self):
        context = SMSFContext(
            smsf_name="Aura Super",
            director_names=["John"],
            director_emails=["john@aura.com"],
            advisor_domains=["ventasadvisory.com.au"],
        )
        matcher = AdvisorDomainMatcher()
        search_engine = SearchRuleEngine(matcher)
        grouping = AdvisorPDFGroupingEngine(search_engine)

        emails = [
            MockEmail(
                sender_email="joel@ventasadvisory.com.au",
                to_recipients="john@aura.com",
                subject="Relevant",
                body="Hello",
                sent_on=datetime(2026, 1, 1),
            ),
            MockEmail(
                sender_email="joel@ventasadvisory.com.au",
                to_recipients="colleague@ventasadvisory.com.au",
                subject="Irrelevant",
                body="Internal",
                sent_on=datetime(2026, 1, 2),
            ),
        ]

        groups = grouping.group_emails(emails, context, matcher)

        assert "Ventas - Aura Super" in groups
        group = groups["Ventas - Aura Super"]
        assert len(group) == 1
        assert group[0].subject == "Relevant"


class TestGeneratePDFPath:
    def test_generates_correct_filename_format(self):
        context = SMSFContext(
            smsf_name="Beta Super",
            director_names=[],
            director_emails=[],
            advisor_domains=[],
        )
        matcher = AdvisorDomainMatcher()
        search_engine = SearchRuleEngine(matcher)
        grouping = AdvisorPDFGroupingEngine(search_engine)

        path = grouping.generate_pdf_path("Ventas", "Beta Super")

        assert path.name == "Ventas - Beta Super.pdf"

    def test_generates_with_spaces_in_names(self):
        context = SMSFContext(
            smsf_name="My SMSF Fund",
            director_names=[],
            director_emails=[],
            advisor_domains=[],
        )
        matcher = AdvisorDomainMatcher()
        search_engine = SearchRuleEngine(matcher)
        grouping = AdvisorPDFGroupingEngine(search_engine)

        path = grouping.generate_pdf_path("Consulting Group", "My SMSF Fund")

        assert path.name == "Consulting Group - My SMSF Fund.pdf"


class TestChronologicalOrdering:
    def test_emails_ordered_chronologically(self):
        context = SMSFContext(
            smsf_name="Test Fund",
            director_names=["Director"],
            director_emails=["dir@test.com"],
            advisor_domains=["ventasadvisory.com.au"],
        )
        matcher = AdvisorDomainMatcher()
        search_engine = SearchRuleEngine(matcher)
        grouping = AdvisorPDFGroupingEngine(search_engine)

        emails = [
            MockEmail(
                sender_email="user@ventasadvisory.com.au",
                to_recipients="dir@test.com",
                subject="Third",
                body="C",
                sent_on=datetime(2026, 3, 1),
            ),
            MockEmail(
                sender_email="user@ventasadvisory.com.au",
                to_recipients="dir@test.com",
                subject="First",
                body="A",
                sent_on=datetime(2026, 1, 1),
            ),
            MockEmail(
                sender_email="user@ventasadvisory.com.au",
                to_recipients="dir@test.com",
                subject="Second",
                body="B",
                sent_on=datetime(2026, 2, 1),
            ),
        ]

        groups = grouping.group_emails(emails, context, matcher)

        group = groups["Ventas - Test Fund"]
        dates = [e.sent_on for e in group]
        assert dates == sorted(dates)


class TestEdgeCases:
    def test_empty_email_list_returns_empty_groups(self):
        context = SMSFContext(
            smsf_name="Test",
            director_names=[],
            director_emails=[],
            advisor_domains=[],
        )
        matcher = AdvisorDomainMatcher()
        search_engine = SearchRuleEngine(matcher)
        grouping = AdvisorPDFGroupingEngine(search_engine)

        groups = grouping.group_emails([], context, matcher)

        assert groups == {}

    def test_no_matching_emails_returns_empty(self):
        context = SMSFContext(
            smsf_name="Test",
            director_names=["Dir"],
            director_emails=["dir@test.com"],
            advisor_domains=["advisor.com"],
        )
        matcher = AdvisorDomainMatcher()
        search_engine = SearchRuleEngine(matcher)
        grouping = AdvisorPDFGroupingEngine(search_engine)

        emails = [
            MockEmail(
                sender_email="other@gmail.com",
                to_recipients="someone@other.com",
                subject="Random",
                body="Hi",
                sent_on=datetime(2026, 1, 1),
            ),
        ]

        groups = grouping.group_emails(emails, context, matcher)

        assert groups == {}