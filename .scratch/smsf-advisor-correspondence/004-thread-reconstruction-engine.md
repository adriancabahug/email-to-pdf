# Thread Reconstruction Engine

## Description

Reconstruct conversation threads across Outlook mailboxes using ConversationID and fallback subject normalization.

## Responsibilities

- Use Outlook ConversationID to group related emails
- Fallback to subject normalization when ConversationID unavailable
- Analyze reply chains to reconstruct chronology
- Thread relevance propagation (if parent thread is relevant, children are relevant)

## Key Interfaces

```python
class ThreadReconstructionEngine:
    def reconstruct_threads(self, emails: List[Email]) -> List[Thread]: ...
    def get_thread_id(self, email: Email) -> str: ...
    def get_thread_emails(self, thread_id: str) -> List[Email]: ...

@dataclass
class Thread:
    thread_id: str
    emails: List[Email]  # sorted chronologically
    root_email: Email
```

## Acceptance Criteria

- [ ] Groups emails by ConversationID when available
- [ ] Falls back to subject-based thread reconstruction
- [ ] Sorts emails within thread chronologically
- [ ] Handles forwarded emails and forwarded copies
- [ ] Handles missing ConversationID gracefully
- [ ] Unit tests cover fragmented threads, forwarded emails
- [ ] Integration tests verify thread order matches Outlook