"""
Advisor Domain Matcher - Maps advisor email domains to canonical organization names.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any


INTERNAL_DOMAIN = "eastcoastinc.com.au"

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
    "earlypay.com.au": "Earlypay"
}


@dataclass(frozen=True)
class Organization:
    name: str
    canonical_domain: str


class AdvisorDomainMatcher:
    def __init__(
        self,
        custom_domain_mappings: Optional[Dict[str, str]] = None,
    ):
        self._domain_to_org: Dict[str, str] = DEFAULT_DOMAIN_MAPPINGS.copy()
        if custom_domain_mappings:
            self._domain_to_org.update(custom_domain_mappings)

    def match(self, email_address: str) -> Optional[Organization]:
        if not email_address:
            return None

        email_lower = email_address.lower().strip()

        if "@" not in email_lower:
            return None

        domain = email_lower.split("@")[1]

        if self._is_internal_domain(domain):
            return None

        canonical_domain = self.get_canonical_domain(domain)
        if not canonical_domain:
            return None

        org_name = self._domain_to_org.get(canonical_domain)
        if org_name:
            return Organization(name=org_name, canonical_domain=canonical_domain)

        return None

    def _is_internal_domain(self, domain: str) -> bool:
        return domain == INTERNAL_DOMAIN or domain.endswith(f".{INTERNAL_DOMAIN}")

    def get_canonical_domain(self, domain: str) -> str:
        domain_lower = domain.lower()

        if domain_lower in self._domain_to_org:
            return domain_lower

        parts = domain_lower.split(".")
        for i in range(len(parts) - 1, 0, -1):
            suffix = ".".join(parts[i:])
            if suffix in self._domain_to_org:
                return suffix

        return domain_lower

    def group_by_organization(
        self,
        emails: List[Any],
        get_sender: str = "sender_email",
        get_to: str = "to_recipients",
        get_cc: str = "cc_recipients",
    ) -> Dict[Organization, List[Any]]:
        groups: Dict[Organization, List[Any]] = {}

        for email in emails:
            sender = getattr(email, get_sender, "")
            to = getattr(email, get_to, "")
            cc = getattr(email, get_cc, "")

            all_addresses = f"{sender} {to} {cc}"
            matched_orgs = set()

            for addr in all_addresses.split():
                if "@" in addr:
                    org = self.match(addr)
                    if org:
                        matched_orgs.add(org)

            for org in matched_orgs:
                if org not in groups:
                    groups[org] = []
                groups[org].append(email)

        return groups
