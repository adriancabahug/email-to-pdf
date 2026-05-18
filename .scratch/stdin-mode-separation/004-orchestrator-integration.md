---
labels: [ready-for-agent]
---

# Slice 3 — Execution Mode + Orchestrator Integration

## Parent

`.scratch/stdin-mode-separation/001-prd.md`

## What to build

Wire execution mode infrastructure and orchestrator routing together. This is a merged slice (previously slices 3 and 4) — the abstractions and their consumer are built together to avoid dead intermediate states.

### 1. ExecutionMode enum and ExecutionContext dataclass

Create `src/execution_mode.py`:

```python
from enum import Enum
from dataclasses import dataclass

class ExecutionMode(Enum):
    BATCH = "batch"
    INTERACTIVE = "interactive"

@dataclass
class ExecutionContext:
    mode: ExecutionMode
    stdin_allowed: bool
    interactive_allowed: bool

def resolve_mode(args: argparse.Namespace, stdin_ok: bool) -> ExecutionContext:
    """Resolves the execution context from CLI args and stdin availability."""
```

`resolve_mode()` rules:
- If `--interactive` or `--console` passed → `INTERACTIVE` mode, `stdin_allowed=True`, `interactive_allowed=True`
- If `--batch` passed → `BATCH` mode, `stdin_allowed=False`, `interactive_allowed=False`
- If no flags and `stdin_ok` → `INTERACTIVE` mode (legacy fallback)
- If no flags and not `stdin_ok` → `BATCH` mode (force to avoid crash)

### 2. argparse in orchestrator

In `main_orchestrator.py`:
- Add `argparse` with `--batch`, `--interactive`, `--console`, `--help`
- `--batch` is the default (no flag = batch in windowed context)
- `--help` shows usage message listing modes

### 3. Orchestrator mode routing

Refactor `MainOrchestrator.__init__()` to accept an optional `ExecutionContext`.

Refactor `run()`:
- Receive resolved `ExecutionContext` from `main()`
- If mode is `BATCH` → call `_run_batch()` directly
- If mode is `INTERACTIVE` → call `_run_interactive()`

### 4. License validation guards

In `_validate_license()`:
- If `ExecutionContext.mode == BATCH` and no stored key → raise `LicenseInputUnavailableError("No license key stored. Configure license key in config.json or run with --interactive from a terminal.")`
- If `ExecutionContext.mode == INTERACTIVE` → call `prompt_and_validate()` (stdin available by definition)

In `main()`:
- Catch `LicenseInputUnavailableError` → print user-friendly message → `sys.exit(1)`

## Acceptance criteria

- [ ] `ExecutionMode.BATCH` and `ExecutionMode.INTERACTIVE` exist
- [ ] `ExecutionContext` has `mode`, `stdin_allowed`, `interactive_allowed` fields
- [ ] `resolve_mode()` returns `ExecutionContext` with correct mode for `--batch`
- [ ] `resolve_mode()` returns `ExecutionContext` with correct mode for `--interactive`
- [ ] `resolve_mode()` returns `ExecutionContext` with correct mode for `--console`
- [ ] `resolve_mode()` falls back to `BATCH` when no flags and no stdin
- [ ] `resolve_mode()` falls back to `INTERACTIVE` when no flags and stdin available
- [ ] `--help` flag prints usage message
- [ ] `main()` creates `ExecutionContext` via `resolve_mode(args, stdin_available())`
- [ ] `MainOrchestrator` receives `ExecutionContext` in constructor
- [ ] `run()` calls `_run_batch()` when mode is `BATCH`
- [ ] `run()` calls `_run_interactive()` when mode is `INTERACTIVE`
- [ ] `_validate_license()` raises `LicenseInputUnavailableError` in `BATCH` mode with no stored key
- [ ] `_validate_license()` calls `prompt_and_validate()` in `INTERACTIVE` mode
- [ ] `main()` catches `LicenseInputUnavailableError` and exits with code 1 and message

## Blocked by

- Slice 1 (002-exceptions.md) — `LicenseInputUnavailableError`
- Slice 2 (003-stdin-guard.md) — `stdin_available()`, `StdinUnavailableError`
