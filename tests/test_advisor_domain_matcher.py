"""
Tests for Advisor Domain Matcher.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional

import pytest

from src.advisor_domain_matcher import AdvisorDomainMatcher, Organization


@dataclass
class MockEmail:
    sender_email: str
    to_recipients: str
    cc_recipients: str


class TestAdvisorDomainMatcher:
    def test_match_returns_organization_for_known_domain(self):
        matcher = AdvisorDomainMatcher()
        result = matcher.match("joel@ventasadvisory.com.au")
        assert result is not None
        assert result.name == "Ventas"
        assert result.canonical_domain == "ventasadvisory.com.au"

    def test_match_returns_none_for_unknown_domain(self):
        matcher = AdvisorDomainMatcher()
        result = matcher.match("someone@gmail.com")
        assert result is None

    def test_match_returns_none_for_internal_domain(self):
        matcher = AdvisorDomainMatcher()
        result = matcher.match("employee@eastcoastinc.com.au")
        assert result is None

    def test_match_handles_subdomain(self):
        matcher = AdvisorDomainMatcher()
        result = matcher.match("admin@mail.ventasadvisory.com.au")
        assert result is not None
        assert result.name == "Ventas"
        assert result.canonical_domain == "ventasadvisory.com.au"

    def test_match_handles_aliased_domain(self):
        matcher = AdvisorDomainMatcher()
        result = matcher.match("support@smtp.ventasadvisory.com.au")
        assert result is not None
        assert result.name == "Ventas"

    def test_match_handles_case_insensitivity(self):
        matcher = AdvisorDomainMatcher()
        result = matcher.match("JOEL@VENTASADVISORY.COM.AU")
        assert result is not None
        assert result.name == "Ventas"

    def test_get_canonical_domain(self):
        matcher = AdvisorDomainMatcher()
        canonical = matcher.get_canonical_domain("mail.ventasadvisory.com.au")
        assert canonical == "ventasadvisory.com.au"

    def test_get_canonical_domain_unknown_returns_original(self):
        matcher = AdvisorDomainMatcher()
        canonical = matcher.get_canonical_domain("unknown.com")
        assert canonical == "unknown.com"


class TestOrganizationGrouping:
    def test_group_by_organization(self):
        matcher = AdvisorDomainMatcher()
        emails = [
            MockEmail(sender_email="joel@ventasadvisory.com.au", to_recipients="", cc_recipients=""),
            MockEmail(sender_email="admin@mail.ventasadvisory.com.au", to_recipients="", cc_recipients=""),
            MockEmail(sender_email="bob@exceedia.com.au", to_recipients="", cc_recipients=""),
        ]
        groups = matcher.group_by_organization(emails)

        assert len(groups) == 2

        org_names = {org.name for org in groups.keys()}
        assert "Ventas" in org_names
        assert "Exceedia" in org_names

        assert len(groups[Organization("Ventas", "ventasadvisory.com.au")]) == 2
        assert len(groups[Organization("Exceedia", "exceedia.com.au")]) == 1


class TestCustomMappings:
    def test_custom_domain_mapping(self):
        custom_mappings = {
            "consulting.example.com": "Consulting LLC"
        }
        matcher = AdvisorDomainMatcher(custom_domain_mappings=custom_mappings)
        result = matcher.match("contact@consulting.example.com")
        assert result is not None
        assert result.name == "Consulting LLC"