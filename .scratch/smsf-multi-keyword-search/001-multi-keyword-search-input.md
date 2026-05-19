---
labels: [ready-for-agent]
---

# Slice 1: Multi-Keyword Search Input

## Parent

(Standalone feature - no parent issue)

## What to build

Replace the current interactive prompts (first name, last name, email, SMSF) with:

```
SMSF name: Aura Super
Emails/keywords (comma-separated or one per line, blank to finish):
> andy.studt74@gmail.com
> annaderdowski@uahoo.com
> ventas
> exceedia
> shapesuper
> earlypay
> newwavelaw
>
Date range: [1] This year (default), [2] Custom range
> 1
```

### Files to Touch

- `src/cli.py` — Replace `get_director_input()` with `get_smsf_input()` returning `smsf: str, search_terms: List[str]`
- `src/cli.py` — Update batch parsing: CSV/JSON `search_terms` column uses semicolon separation
- `src/cli.py` — Add date range prompt: default current year, custom asks for YYYY-MM-DD start/end
- `src/main_orchestrator.py` — Replace `DirectorContext` with `SMSFContext(smsf, search_terms, start_date, end_date)`

## Acceptance criteria

- [ ] Interactive mode accepts comma-separated OR multi-line keywords until blank
- [ ] Batch CSV parses `search_terms` with semicolon separation
- [ ] Date range defaults to current year (Jan 1 — Dec 31)
- [ ] All terms trimmed, lowercased, stored as `List[str]`
- [ ] Tests updated for new CLI signatures

## Blocked by

- None — can start immediately