# Cross-Mailbox Deduplication

## Description

Prevent duplicate emails from appearing in PDF output when the same email exists across multiple Outlook accounts.

## Implementation

**Primary deduplication key**: `internet_message_id` (globally unique, not mailbox-local)

**Fallback heuristics** (when internet_message_id unavailable):
- Normalized body hash
- Timestamp (within 60 seconds)
- Sender email address
- Normalized subject

## Key Interfaces

```python
class CrossMailboxDeduplicator:
    def deduplicate(self, emails: List[Email]) -> List[Email]: ...
    def get_deduplication_key(self, email: Email) -> str: ...
```

## Important Note

Current implementation uses `EntryID` which is mailbox-local and will NOT work for cross-mailbox deduplication. Must switch to `internet_message_id`.

## Acceptance Criteria

- [ ] Uses internet_message_id as primary deduplication key
- [ ] Falls back to heuristic matching when internet_message_id unavailable
- [ ] Deduplicates across different Outlook accounts
- [ ] Preserves one copy of each unique email
- [ ] Unit tests cover same email across mailboxes, forwarded copies
- [ ] Integration tests verify deduplication with real multi-account data