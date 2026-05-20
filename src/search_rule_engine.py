"""
Search Rule Engine - Determines whether an email belongs in an SMSF evidence pack.
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

    def is_relevant(self, email: Any, context: SMSFContext) -> RelevanceLevel:
        has_advisor = self._has_advisor_domain(email, context)
        has_smsf_context = self._has_smsf_context(email, context)

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

    def _has_smsf_context(self, email: Any, context: SMSFContext) -> bool:
        all_text_fields = self._get_all_text_fields(email)

        tokens = self._get_smsf_context_tokens(context)

        for token in tokens:
            token_lower = token.lower()
            for field in all_text_fields:
                if token_lower in field.lower():
                    return True

        return False

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
        addr = getattr(email, "SenderEmailAddress", None)
        if addr:
            return str(addr)
        return getattr(email, "sender_email", "")

    def _get_to_recipients(self, email: Any) -> str:
        to = getattr(email, "To", None)
        if to:
            return str(to)
        return getattr(email, "to_recipients", "")

    def _get_cc_recipients(self, email: Any) -> str:
        cc = getattr(email, "CC", None)
        if cc:
            return str(cc)
        return getattr(email, "cc_recipients", "")

    def _get_search_fields(self, email: Any) -> list[str]:
        fields = []

        subject = getattr(email, "Subject", None)
        if subject:
            fields.append(str(subject))

        body = getattr(email, "Body", None)
        if body:
            fields.append(str(body))

        sender_name = getattr(email, "SenderName", None)
        if sender_name:
            fields.append(str(sender_name))

        return fields

    def _get_all_text_fields(self, email: Any) -> list[str]:
        fields = []

        subject = getattr(email, "Subject", None)
        if subject:
            fields.append(str(subject))

        body = getattr(email, "Body", None)
        if body:
            fields.append(str(body))

        sender = self._get_sender_email(email)
        to = self._get_to_recipients(email)
        cc = self._get_cc_recipients(email)
        if sender:
            fields.append(sender)
        if to:
            fields.append(to)
        if cc:
            fields.append(cc)

        return fields

    def should_exclude(self, email: Any) -> bool:
        sender = self._get_sender_email(email)
        to = self._get_to_recipients(email)
        cc = self._get_cc_recipients(email)

        all_addresses = f"{sender} {to} {cc}".lower()

        internal_domain = "eastcoastinc.com.au"
        if internal_domain in all_addresses:
            has_external = False
            for addr in all_addresses.split():
                if "@" in addr and internal_domain not in addr:
                    has_external = True
                    break
            return not has_external

        return False