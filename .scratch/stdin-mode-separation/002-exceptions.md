---
labels: [ready-for-agent]
---

# Slice 1 — Exceptions Infrastructure

## Parent

.scratch/stdin-mode-separation/001-prd.md

## What to build

Create src/exceptions.py containing two custom exception types that serve as the foundational error vocabulary for the execution mode system.

### StdinUnavailableError(RuntimeError)

Raised by stdin_guard.require_stdin() when an interactive operation is attempted outside a terminal. This is the architectural guardrail — any module that violates stdin boundaries will surface this error.

### LicenseInputUnavailableError(RuntimeError)

Raised by LicenseValidator when the license key cannot be obtained in batch mode. Unlike the stdin guard, this is not a programming error — it is a terminal licensing failure. The orchestrator handles this by exiting cleanly with a message. This exception explicitly prohibits the "silent fallback" pattern (no eturn None in batch mode).

Both exceptions inherit from RuntimeError for natural upward propagation through the call stack.

## Acceptance criteria

- [ ] StdinUnavailableError inherits from RuntimeError
- [ ] StdinUnavailableError is importable from src.exceptions
- [ ] LicenseInputUnavailableError inherits from RuntimeError
- [ ] LicenseInputUnavailableError is importable from src.exceptions
- [ ] src/exceptions.py has zero dependencies on other application modules
- [ ] Both exceptions can be instantiated with a message: StdinUnavailableError("prompt")

## Blocked by

None — can start immediately.
