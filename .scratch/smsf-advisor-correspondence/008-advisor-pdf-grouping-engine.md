# Advisor PDF Grouping Engine

## Description

Group reconstructed threads and emails into advisor-organization-level PDF outputs.

## Output Format

```
{Advisor Organization} - {SMSF Name}.pdf
```

Examples:
```
Ventas - Aura Super.pdf
Exceedia - Aura Super.pdf
Shape Super - Aura Super.pdf
```

**NOT**:
```
Joel Reed - Aura Super.pdf  (individual advisor - WRONG)
```

## Key Interfaces

```python
class AdvisorPDFGroupingEngine:
    def group_emails(
        self,
        emails: List[Email],
        context: SMSFContext,
        matcher: AdvisorDomainMatcher
    ) -> Dict[str, str]:  # {filename: html_content}
    def generate_pdf_path(self, organization: str, smsf_name: str) -> Path: ...
```

## Acceptance Criteria

- [ ] Groups emails by advisor organization, not individual
- [ ] One PDF per advisor organization per SMSF
- [ ] Filename format: "{Org} - {SMSF}.pdf"
- [ ] All relevant emails for an organization included in single PDF
- [ ] Chronological ordering within each PDF
- [ ] Integration tests verify grouping matches business requirements