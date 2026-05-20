# Advisor Domain Matcher

## Description

Create a module that encapsulates all advisor organization matching logic. Maps advisor email domains to canonical organization names for grouping purposes.

## Responsibilities

- Fuzzy domain matching (e.g., `mail.ventasadvisory.com.au` → `Ventas`)
- Alias domain normalization
- Subdomain handling
- Participant email extraction
- Organization name grouping

## Examples

```
Input:  "joel@ventasadvisory.com.au"
Output: Organization("Ventas", domain="ventasadvisory.com.au")

Input:  "admin@mail.exceedia.com.au"
Output: Organization("Exceedia", domain="exceedia.com.au")
```

## Key Interfaces

```python
class AdvisorDomainMatcher:
    def match(self, email_address: str) -> Optional[Organization]: ...
    def get_canonical_domain(self, domain: str) -> str: ...
    def group_by_organization(self, emails: List[Email]) -> Dict[Organization, List[Email]]: ...
```

## Acceptance Criteria

- [ ] Maps base domains to organization names (ventasadvisory.com.au → Ventas)
- [ ] Handles subdomains (mail.ventasadvisory.com.au → Ventas)
- [ ] Returns None for non-advisor domains (gmail, eastcoastinc.com.au)
- [ ] Groups emails by organization for PDF output
- [ ] Supports configuration of domain→organization mappings
- [ ] Unit tests cover subdomain, alias, and malformed domain handling