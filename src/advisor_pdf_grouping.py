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
        groups: Dict[str, List[Any]] = {}

        strong_emails = []
        medium_emails = []

        for email in emails:
            level = self._search_engine.is_relevant(email, context)
            if level == RelevanceLevel.STRONG:
                strong_emails.append(email)
            elif level == RelevanceLevel.MEDIUM:
                medium_emails.append(email)

        for email in strong_emails:
            org = self._get_advisor_organization(email, matcher)
            if org:
                key = f"{org.name} - {context.smsf_name}"
                if key not in groups:
                    groups[key] = []
                groups[key].append(email)

        if medium_emails:
            key = f"Director Correspondence - {context.smsf_name}"
            groups[key] = medium_emails

        for key in groups:
            groups[key] = self._sort_chronologically(groups[key])

        return groups

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