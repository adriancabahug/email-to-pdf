"""
Advisor Domain Matcher

Maps advisor email domains to canonical organization names.

Responsibilities:
- Match email addresses to advisor organizations
- Normalize domains
- Exclude internal domains
- Group emails by advisor organization
"""

from __future__ import annotations

import re

from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Set


INTERNAL_DOMAINS = {
    "eastcoastinc.com.au",
}


DEFAULT_DOMAIN_MAPPINGS = {
    "ventasadvisory.com.au": "Ventas",
    "exceedia.com.au": "Exceedia",
    "shapesuper.com.au": "Shape Super",
    "nowinfinity.com.au": "NowInfinity",
    "smartaudit.com.au": "SmartAudit",
    "smsfadviser.com.au": "SMSF Adviser",
    "superannuation.com.au": "Superannuation",
    "taxdept.com.au": "Tax Department",
    "ato.gov.au": "ATO",
    "auspost.com.au": "AusPost",
    "xero.com": "Xero",
    "keypay.com.au": "KeyPay",
    "earlypay.com.au": "EarlyPay",
    "newwavelaw.com.au": "NewWaveLaw",
}


EMAIL_REGEX = re.compile(
    r"[\w\.-]+@[\w\.-]+\.\w+",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Organization:
    name: str
    canonical_domain: str


class AdvisorDomainMatcher:
    """
    Domain-to-organization resolution engine.
    """

    def __init__(
        self,
        custom_domain_mappings: Optional[Dict[str, str]] = None,
    ):
        self._domain_to_org: Dict[str, str] = {
            k.lower(): v
            for k, v in DEFAULT_DOMAIN_MAPPINGS.items()
        }

        if custom_domain_mappings:
            self._domain_to_org.update({
                k.lower(): v
                for k, v in custom_domain_mappings.items()
            })

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def get_domains(self) -> List[str]:
        """
        Return all advisor domains.
        """
        return list(self._domain_to_org.keys())

    def match(self, email_address: str) -> Optional[Organization]:
        """
        Match an email address to a known advisor organization.
        """
        if not email_address:
            return None

        email_lower = email_address.lower().strip()

        if "@" not in email_lower:
            return None

        try:
            domain = email_lower.split("@", 1)[1]
        except Exception:
            return None

        if self._is_internal_domain(domain):
            return None

        canonical_domain = self.get_canonical_domain(domain)

        if not canonical_domain:
            return None

        org_name = self._domain_to_org.get(canonical_domain)

        if not org_name:
            return None

        return Organization(
            name=org_name,
            canonical_domain=canonical_domain,
        )

    def get_canonical_domain(self, domain: str) -> str:
        """
        Normalize subdomains to canonical domains.

        Example:
            mail.ventasadvisory.com.au
                -> ventasadvisory.com.au

        Returns the input domain unchanged if no canonical mapping exists.
        """
        if not domain:
            return domain

        domain_lower = domain.lower().strip()

        if domain_lower in self._domain_to_org:
            return domain_lower

        parts = domain_lower.split(".")

        for i in range(len(parts)):
            candidate = ".".join(parts[i:])

            if candidate in self._domain_to_org:
                return candidate

        return domain_lower

    def group_by_organization(
        self,
        emails: List[Any],
        get_sender: str = "sender_email",
        get_to: str = "to_recipients",
        get_cc: str = "cc_recipients",
    ) -> Dict[Organization, List[Any]]:
        """
        Group emails by advisor organization.
        """

        groups: Dict[Organization, List[Any]] = {}

        for email in emails:
            matched_orgs = self._extract_organizations(
                email,
                get_sender,
                get_to,
                get_cc,
            )

            for org in matched_orgs:
                groups.setdefault(org, []).append(email)

        return groups

    # ------------------------------------------------------------------
    # INTERNALS
    # ------------------------------------------------------------------

    def _extract_organizations(
        self,
        email: Any,
        get_sender: str,
        get_to: str,
        get_cc: str,
    ) -> Set[Organization]:
        matched_orgs: Set[Organization] = set()

        sender = str(getattr(email, get_sender, "") or "")
        to = str(getattr(email, get_to, "") or "")
        cc = str(getattr(email, get_cc, "") or "")

        combined = f"{sender} {to} {cc}"

        addresses = EMAIL_REGEX.findall(combined)

        for addr in addresses:
            org = self.match(addr)

            if org:
                matched_orgs.add(org)

        return matched_orgs

    def _is_internal_domain(self, domain: str) -> bool:
        domain = domain.lower().strip()

        return any(
            domain == internal
            or domain.endswith(f".{internal}")
            for internal in INTERNAL_DOMAINS
        )
