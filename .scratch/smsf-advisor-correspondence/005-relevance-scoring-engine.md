# Relevance Scoring Engine

## Description

Determine whether an email or thread belongs in an SMSF evidence pack using a scoring hierarchy.

## Scoring Hierarchy

### STRONG Match
- Advisor domain in FROM/TO/CC
- AND SMSF context (name, director name, director email) in thread/body/participants

### MEDIUM Match
- Connected to already-matching thread (thread relevance propagation)

### WEAK Match
- Advisor-only email without SMSF linkage
- Should normally be excluded from evidence packs

### NONE
- No advisor domain OR no SMSF context

## Key Interfaces

```python
class RelevanceScoringEngine:
    def score_email(self, email: Email, context: SMSFContext) -> RelevanceLevel: ...
    def score_thread(self, thread: Thread, context: SMSFContext) -> RelevanceLevel: ...
    def is_strong_match(self, email: Email, context: SMSFContext) -> bool: ...
```

## Acceptance Criteria

- [ ] Correctly scores STRONG when both advisor domain and SMSF context present
- [ ] Correctly scores MEDIUM for thread propagation
- [ ] Correctly scores WEAK for advisor-only emails
- [ ] Correctly scores NONE when criteria not met
- [ ] Excludes WEAK matches by default (configurable)
- [ ] Unit tests cover all relevance levels
- [ ] Integration tests verify against real email patterns