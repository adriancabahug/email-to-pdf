---
labels: [ready-for-agent]
---

# Slice 6 — Architectural Regression Tests

## Parent

`.scratch/stdin-mode-separation/001-prd.md`

## What to build

Write the architectural guardrail tests that verify batch mode never performs any interactive I/O. This test suite is the regression prevention system — it catches not just Rich-specific regressions but any future stdin leakage.

### Test 1: Batch mode orchestrator — no stdin reads

Integration test in `tests/test_batch_no_stdin.py`:

```python
class TestBatchModeNoStdin:
    def test_batch_mode_orchestrator_no_stdin_access(self):
        """
        Batch mode orchestrator start-up and director processing must never
        access sys.stdin, call Prompt.ask, Confirm.ask, or require_stdin.
        """
```

Implementation approach:
- Patch `sys.stdin` to return a mock with `isatty()` returning `False`
- Create `MainOrchestrator` in batch mode (no `--interactive` flag, no stdin)
- Call `run()`
- Use `unittest.mock.patch` to wrap `Prompt.ask`, `Confirm.ask`, `require_stdin`, and `sys.stdin.read*` with sentinel mocks
- Assert none of the sentinel mocks were called during execution

The invariant: batch mode execution contains **zero interactive I/O operations** of any kind.

### Test 2: stdin_guard module unit tests

In `tests/test_stdin_guard.py`:

- `stdin_available()` returns `True` when stdin is a TTY
- `stdin_available()` returns `False` when stdin is `None`
- `stdin_available()` returns `False` when `isatty()` returns `False`
- `require_stdin()` raises `StdinUnavailableError` when `stdin_available()` is `False`
- `require_stdin()` returns silently when `stdin_available()` is `True`
- Error message contains the operation label

### Test 3: stdin_guard module — isatty attribute missing

- `stdin_available()` returns `False` when `sys.stdin` has no `isatty` attribute

### Test 4: exceptions module unit tests

In `tests/test_exceptions.py`:

- `StdinUnavailableError` inherits from `RuntimeError`
- `StdinUnavailableError` is importable from `src.exceptions`
- `LicenseInputUnavailableError` inherits from `RuntimeError`
- `LicenseInputUnavailableError` is importable from `src.exceptions`

### Test 5: InputHandler guard — RuntimeError on stdin unavailable

In `tests/test_input_handler.py` (update existing):

- `get_director_input()` raises `StdinUnavailableError` when stdin is unavailable
- `prompt_continue()` raises `StdinUnavailableError` when stdin is unavailable

### Test 6: LicenseValidator guard — exception on stdin unavailable

In `tests/test_license_validator.py` (update existing):

- `prompt_and_validate()` raises `LicenseInputUnavailableError` when stdin is unavailable

## Acceptance criteria

- [ ] `test_batch_mode_orchestrator_no_stdin_access` exists and passes — batch execution performs zero Prompt.ask, Confirm.ask, or stdin reads
- [ ] `test_stdin_available_tty` passes — returns True when stdin is a TTY
- [ ] `test_stdin_available_none` passes — returns False when stdin is None
- [ ] `test_stdin_available_not_tty` passes — returns False when isatty() returns False
- [ ] `test_stdin_available_missing_attr` passes — returns False when isatty attribute missing
- [ ] `test_require_stdin_raises_when_unavailable` passes — raises StdinUnavailableError
- [ ] `test_require_stdin_silent_when_available` passes — returns silently
- [ ] `test_require_stdin_message_contains_operation` passes
- [ ] `test_stdin_unavailable_error_inherits` passes
- [ ] `test_license_input_unavailable_error_inherits` passes
- [ ] `test_input_handler_raises_stdin_error` passes — `get_director_input()` raises when stdin unavailable
- [ ] `test_input_handler_prompt_continue_raises_stdin_error` passes
- [ ] `test_license_validator_raises_when_stdin_unavailable` passes — raises `LicenseInputUnavailableError`

## Blocked by

- Slice 3 (004-orchestrator-integration.md) — orchestrator must be wired before regression tests can verify it
- Slice 4 (005-input-license-guards.md) — guards must be in place before testing them
- Slice 5 (006-context-propagation.md) — context propagation must be complete for integration test to be meaningful
