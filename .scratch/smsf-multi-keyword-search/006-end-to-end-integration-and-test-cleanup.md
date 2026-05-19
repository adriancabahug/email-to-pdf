---
labels: [ready-for-agent]
---

# Slice 6: End-to-End Integration and Test Cleanup

## Parent

(Standalone feature - no parent issue)

## What to build

Wire everything together, remove old code, fix all tests.

### Files to Touch

- `src/main_orchestrator.py` — Remove `DirectorContext`, `discover_email_from_name()`, per-director loop
- `src/main_orchestrator.py` — `_run_interactive()` and `_run_batch()` use `SMSFContext`
- `src/main_orchestrator.py` — Single `_process_smsf()` method replacing `_process_director()`
- `src/dependencies.py` — Update `CompositionRoot` if signatures changed
- `tests/` — Update all tests to match new signatures
- `tests/` — Delete or fix stale tests

### Cleanup Checklist

- [ ] Remove `DirectorContext` dataclass
- [ ] Remove `discover_email_from_name()` calls
- [ ] Remove per-director output logic
- [ ] Update `test_main_orchestrator.py` with SMSF mocks
- [ ] Update `test_email_searcher.py` for multi-keyword queries
- [ ] Update `test_file_manager.py` for new filename format
- [ ] Update `test_cli.py` for new prompts
- [ ] Run `pytest tests/ --ignore=tests/test_playwright_pdf.py -q` → 0 failures

## Acceptance criteria

- [ ] All old DirectorContext code removed
- [ ] SMSFContext fully wired in orchestrator
- [ ] All tests pass
- [ ] No `@pytest.mark.skip` remaining

## Blocked by

- Slices 1–5 (001-multi-keyword-search-input.md, 002-multi-keyword-dasl-query-builder.md, 003-email-deduplication-and-chronological-sort.md, 004-smsf-centric-pdf-output.md, 005-rich-progress-bar-for-folder-search.md)