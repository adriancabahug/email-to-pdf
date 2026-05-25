"""
Advisor PDF Grouping Engine - Groups emails by advisor organization for PDF output.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from src.smsf_context import SMSFContext
from src.advisor_domain_matcher import AdvisorDomainMatcher
from src.search_rule_engine import SearchRuleEngine, RelevanceLevel


class AdvisorPDFGroupingEngine:
    def __init__(self, search_engine: SearchRuleEngine):
        self._search_engine = search_engine

    def group_emails(
        self,
        emails: List[Any],
        context: SMSFContext,
        matcher: AdvisorDomainMatcher,
    ) -> Dict[str, List[Any]]:
        relevant_emails = [
            e for e in emails
            if self._search_engine.is_relevant(e, context) == RelevanceLevel.STRONG
        ]

        org_groups: Dict[str, List[Any]] = {}

        for email in relevant_emails:
            org = self._get_advisor_organization(email, matcher)
            if org:
                key = f"{org.name} - {context.smsf_name}"
                if key not in org_groups:
                    org_groups[key] = []
                org_groups[key].append(email)

        for key in org_groups:
            org_groups[key] = self._sort_chronologically(org_groups[key])

        return org_groups

    def _get_advisor_organization(self, email: Any, matcher: AdvisorDomainMatcher) -> Any:
        all_addresses = f"{email.sender_email} {email.to_recipients} {email.cc_recipients}"

        for addr in all_addresses.split():
            if "@" in addr:
                org = matcher.match(addr)
                if org:
                    return org

        return None

    def _sort_chronologically(self, emails: List[Any]) -> List[Any]:
        return sorted(emails, key=lambda e: e.sent_on or datetime.min)

    def generate_pdf_path(self, organization: str, smsf_name: str) -> Path:
        filename = f"{organization} - {smsf_name}.pdf"
        return Path(filename)