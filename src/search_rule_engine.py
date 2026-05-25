"""
Search Rule Engine - Determines whether an email belongs in an SMSF evidence pack.
Optimized to avoid double body scanning when email_searcher already checked it.
"""

import enum
from typing import Any, Optional

from src.smsf_context import SMSFContext
from src.advisor_domain_matcher import AdvisorDomainMatcher, Organization


class RelevanceLevel(enum.Enum):
    STRONG = "strong"
    MEDIUM = "medium"
    WEAK = "weak"
    NONE = "none"


class SearchRuleEngine:
    def __init__(self, domain_matcher: AdvisorDomainMatcher):
        self._matcher = domain_matcher

    def is_relevant(
        self,
        email: Any,
        context: SMSFContext,
        body_already_scanned: bool = False,
    ) -> RelevanceLevel:
        """
        Determine if an email is relevant to the SMSF evidence pack.

        Args:
            email: The Outlook email object
            context: SMSF context with names, emails, advisor domains
            body_already_scanned: If True, skip body check (email_searcher did it)

        Returns:
            RelevanceLevel: STRONG, MEDIUM, WEAK, or NONE
        """
        has_advisor = self._has_advisor_domain(email, context)
        has_smsf_context = self._has_smsf_context(
            email, context, skip_body=body_already_scanned
        )

        if has_advisor and has_smsf_context:
            return RelevanceLevel.STRONG
        elif has_advisor and not has_smsf_context:
            return RelevanceLevel.WEAK

        return RelevanceLevel.NONE

    def _has_advisor_domain(self, email: Any, context: SMSFContext) -> bool:
        sender = self._get_sender_email(email)
        to = self._get_to_recipients(email)
        cc = self._get_cc_recipients(email)

        all_addresses = f"{sender} {to} {cc}"

        import re
        addresses = re.findall(r'[\w\.\-]+@[\w\.\-]+', all_addresses.lower())

        for addr in addresses:
            if self._matcher.match(addr):
                return True

        return False

    def _has_smsf_context(
        self,
        email: Any,
        context: SMSFContext,
        skip_body: bool = False,
    ) -> bool:
        """
        Check if email contains SMSF context (name, director names, emails).

        Args:
            skip_body: If True, only check metadata fields (avoids expensive COM call)
        """
        # Check metadata fields first (cheap - no COM body fetch)
        metadata_fields = self._get_metadata_fields(email)
        tokens = self._get_smsf_context_tokens(context)

        for token in tokens:
            token_lower = token.lower()
            for field in metadata_fields:
                if token_lower in field.lower():
                    return True

        # Only check body if not already scanned by email_searcher
        if skip_body:
            return False

        # Body already eagerly extracted into ExtractedEmail
        if email.body:
            body_text = email.body.lower()
            for token in tokens:
                if token.lower() in body_text:
                    return True

        return False

    def _get_metadata_fields(self, email: Any) -> list[str]:
        fields = []
        if email.subject:
            fields.append(email.subject)
        sender = email.sender_email
        if sender:
            fields.append(sender)
        to = email.to_recipients
        if to:
            fields.append(to)
        cc = email.cc_recipients
        if cc:
            fields.append(cc)
        if email.sender_name:
            fields.append(email.sender_name)
        return fields

    def _get_smsf_context_tokens(self, context: SMSFContext) -> list[str]:
        tokens = []
        if context.smsf_name:
            tokens.append(context.smsf_name.lower())
        for name in context.director_names:
            tokens.append(name.lower())
        for email in context.director_emails:
            tokens.append(email.lower())
        return tokens

    def _get_sender_email(self, email: Any) -> str:
        return email.sender_email

    def _get_to_recipients(self, email: Any) -> str:
        return email.to_recipients

    def _get_cc_recipients(self, email: Any) -> str:
        return email.cc_recipients

    def should_exclude(self, email: Any) -> bool:
        """Exclude purely internal East Coast emails unless part of external thread."""
        sender = self._get_sender_email(email)
        to = self._get_to_recipients(email)
        cc = self._get_cc_recipients(email)

        all_addresses = f"{sender} {to} {cc}".lower()

        internal_domains = {
            "eastcoastinc.com.au",
        }
        if internal_domain in all_addresses:
            has_external = False
            for addr in all_addresses.split():
                if "@" not in addr:
                    continue
                if not any(domain in addr for domain in internal_domains):
                    has_external = True
                    break
            return not has_external

        return False
