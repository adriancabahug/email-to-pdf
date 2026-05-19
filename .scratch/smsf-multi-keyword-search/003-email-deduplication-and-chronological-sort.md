---
labels: [ready-for-agent]
---

# Slice 3: Email Deduplication and Chronological Sort

## Parent

(Standalone feature - no parent issue)

## What to build

Aggregate search results, deduplicate by `EntryID`, sort by `ReceivedTime`.

### Files to Touch

- `src/email_searcher.py` — `search()` returns `List[Any]` with deduped, sorted results
- `src/email_searcher.py` — Use a `set()` of `message.EntryID` to track seen emails
- `src/main_orchestrator.py` — Single call to `searcher.search()` per SMSF, not per-keyword

```python
# In search()
seen_ids = set()
results = []
for folder in self._iter_folders(strategy):
    # ... query ...
    for msg in restricted:
        entry_id = getattr(msg, "EntryID", None)
        if entry_id and entry_id not in seen_ids:
            seen_ids.add(entry_id)
            results.append(msg)

# Sort
results.sort(key=lambda m: getattr(m, "ReceivedTime", datetime.min))
```

## Acceptance criteria

- [ ] Deduplication by `EntryID` across all keyword matches
- [ ] Chronological sort by `ReceivedTime` (oldest first)
- [ ] Single collection per SMSF
- [ ] Tests verify dedup and sort order

## Blocked by

- Slice 2 (002-multi-keyword-dasl-query-builder.md) — needs query builder in place