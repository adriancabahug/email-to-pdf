---
labels: [ready-for-agent]
---

# Slice 4 — InputHandler + LicenseValidator Guards

## Parent

`.scratch/stdin-mode-separation/001-prd.md`

## What to build

Install stdin guards into `InputHandler` and `LicenseValidator`, replacing their implicit stdin assumptions with explicit enforcement.

### InputHandler (`src/input_handler.py`)

- Import `require_stdin` from `src.stdin_guard`
- `get_director_input()` — call `require_stdin("prompt")` at the very top before any `Prompt.ask()`
- `prompt_continue()` — call `require_stdin("continue prompt")` at the very top before any `Confirm.ask()`

If `require_stdin()` raises `StdinUnavailableError`, it propagates up to the orchestrator — the orchestrator does not catch it; this is intentional. `InputHandler` is an interactive-only module and should not silently recover.

### LicenseValidator (`src/license_validator.py`)

- Import `stdin_available` from `src.stdin_guard`
- Import `LicenseInputUnavailableError` from `src.exceptions`
- `prompt_and_validate()` — check `stdin_available()`. If `False`, raise `LicenseInputUnavailableError("License key entry requires a terminal. Configure license key in config.json or run with --interactive from a command line.")`. This is NOT a silent `return None` — it is a hard error.

Note: The orchestrator already guards `_validate_license()` for batch mode. This additional guard in `LicenseValidator` provides defense-in-depth and makes the constraint explicit at the point of stdin usage.

## Acceptance criteria

- [ ] `get_director_input()` raises `StdinUnavailableError` when stdin is unavailable (propagates from `require_stdin`)
- [ ] `prompt_continue()` raises `StdinUnavailableError` when stdin is unavailable
- [ ] `get_director_input()` succeeds when stdin is available (Rich prompts work normally)
- [ ] `prompt_continue()` succeeds when stdin is available
- [ ] `prompt_and_validate()` raises `LicenseInputUnavailableError` when stdin is unavailable
- [ ] `prompt_and_validate()` succeeds when stdin is available (user prompt works normally)
- [ ] `InputHandler` has zero direct `sys.stdin` access — all stdin interaction goes through `require_stdin()`
- [ ] `LicenseValidator` has zero direct `sys.stdin` access in `prompt_and_validate()`

## Blocked by

- Slice 2 (003-stdin-guard.md) — `require_stdin()` and `stdin_available()`
