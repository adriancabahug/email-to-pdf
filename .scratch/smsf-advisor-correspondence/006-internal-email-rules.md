# Internal Email Rules

## Description

Handle internal East Coast emails according to business rules.

## Rules

**Exclude** (default):
- Emails where all participants are @eastcoastinc.com.au

**Include** (exception):
- Internal emails that are part of a matching external advisor thread
- Internal emails that contain relevant SMSF context and advisor involvement

## Implementation Notes

The search rule "advisor domain in FROM/TO/CC" will naturally include internal emails when there's external advisor involvement. This issue covers the edge case filtering.

## Key Interfaces

```python
class InternalEmailFilter:
    def should_exclude_as_internal_only(self, email: Email) -> bool: ...
    def should_include_despite_internal(self, email: Email, context: SMSFContext) -> bool: ...
```

## Acceptance Criteria

- [ ] Excludes internal-only conversations by default
- [ ] Includes internal emails when part of matching external thread
- [ ] Respects advisor domain presence in FROM/TO/CC
- [ ] Unit tests cover internal-only, mixed, and external scenarios