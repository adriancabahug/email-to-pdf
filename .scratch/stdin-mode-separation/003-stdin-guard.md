---
labels: [ready-for-agent]
---

# Slice 2 — stdin_guard Module

## Parent

`.scratch/stdin-mode-separation/001-prd.md`

## What to build

Create `src/stdin_guard.py` as the isolated, zero-dependency module responsible for detecting terminal availability and enforcing stdin boundaries across the application.

### API

```python
from src.exceptions import StdinUnavailableError

def stdin_available() -> bool:
    """Returns True only if sys.stdin exists and is a TTY."""

def require_stdin(operation: str) -> None:
    """
    Enforces stdin availability. Raises StdinUnavailableError if stdin is unavailable.
    operation: descriptive label for the operation being guarded (e.g., "prompt", "continue prompt")
    """
```

### Behavior

- `stdin_available()` — returns `True` when `sys.stdin` is not `None`, has `isatty`, and `isatty()` returns `True`. Returns `False` otherwise (including when stdin is `None`, when `isatty()` returns `False`, or when `isatty` attribute doesn't exist).
- `require_stdin(operation)` — calls `stdin_available()`. If `False`, raises `StdinUnavailableError(f"Interactive {operation} called outside terminal. Use --interactive flag from command line.")`. If `True`, returns silently.

This module has zero imports from any other application module. It is the single choke-point for all stdin-related capability detection.

## Acceptance criteria

- [ ] `stdin_available()` returns `True` when `sys.stdin.isatty()` is `True`
- [ ] `stdin_available()` returns `False` when `sys.stdin` is `None`
- [ ] `stdin_available()` returns `False` when `sys.stdin.isatty()` is `False`
- [ ] `require_stdin("test")` raises `StdinUnavailableError` when `stdin_available()` is `False`
- [ ] `require_stdin("test")` returns silently when `stdin_available()` is `True`
- [ ] `StdinUnavailableError` message contains the operation label
- [ ] `src/stdin_guard.py` imports `StdinUnavailableError` from `src.exceptions`
- [ ] `src/stdin_guard.py` has zero imports from any module other than `sys` and `src.exceptions`

## Blocked by

- Slice 1 (002-exceptions.md) — depends on `StdinUnavailableError` from `src.exceptions`
