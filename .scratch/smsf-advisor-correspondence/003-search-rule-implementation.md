# Search Rule Implementation

## Description

Implement the core search rules that determine whether an email/thread belongs in an SMSF evidence pack.

## Search Rules

**REQUIRED**:
- Advisor domain appears in: FROM, TO, or CC

**AND** (at least one):
- SMSF name appears in thread/body/participants
- Director name appears in thread/body/participants
- Director email appears in thread/body/participants

## Key Interfaces

```python
class SearchRuleEngine:
    def is_relevant(self, email: Email, context: SMSFContext) -> RelevanceLevel: ...
    def should_exclude(self, email: Email) -> bool: ...

class RelevanceLevel(enum):
    STRONG   # advisor domain + SMSF context
    MEDIUM   # connected to matching thread
    WEAK     # advisor-only, no SMSF linkage
    NONE     # not relevant
```

## Acceptance Criteria

- [ ] Returns STRONG when advisor domain in FROM/TO/CC AND SMSF context present
- [ ] Returns NONE when no advisor domain match
- [ ] Returns NONE when advisor domain present but no SMSF context
- [ ] Correctly identifies SMSF name, director name, director email in search fields
- [ ] Uses case-insensitive matching
- [ ] Integration tests verify search against real Outlook data
- [ ] Performance acceptable for ~1000 emails per SMSF