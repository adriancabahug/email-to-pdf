---
labels: [ready-for-agent]
---

# Slice 2: Multi-Keyword DASL Query Builder

## Parent

(Standalone feature - no parent issue)

## What to build

Refactor `EmailSearcher._build_restrict_query()` to accept multiple keywords and a date range.

### Query Structure

```python
# Build OR conditions for all keywords across all fields
keyword_conditions = []
for kw in search_terms:
    safe = kw.replace("'", "''")
    keyword_conditions.append(f"[SenderEmailAddress] LIKE '%{safe}%'")
    keyword_conditions.append(f"[To] LIKE '%{safe}%'")
    keyword_conditions.append(f"[CC] LIKE '%{safe}%'")
    keyword_conditions.append(f"[BCC] LIKE '%{safe}%'")
    keyword_conditions.append(f"[Subject] LIKE '%{safe}%'")

# Date range in DASL format
start_str = start_date.strftime("%m/%d/%Y %I:%M %p")
end_str = end_date.strftime("%m/%d/%Y %I:%M %p")

query = f"({' OR '.join(keyword_conditions)}) AND ([ReceivedTime] >= '{start_str}') AND ([ReceivedTime] <= '{end_str}')"
```

### Files to Touch

- `src/email_searcher.py` — `_build_restrict_query()` signature: `(search_terms: List[str], start_date: datetime, end_date: datetime)`
- `src/email_searcher.py` — Remove single-email parameter from search flow
- `src/email_searcher.py` — Update `_search()` to pass the new query

## Acceptance criteria

- [ ] Single DASL query with OR across all keywords and all fields
- [ ] Date bounds appended in `%m/%d/%Y %I:%M %p` format
- [ ] Default date range is current calendar year
- [ ] Tests verify query string construction

## Blocked by

- Slice 1 (001-multi-keyword-search-input.md) — needs search_terms input structure