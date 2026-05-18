---
labels: [ready-for-agent]
---

# Slice 5 — ExecutionContext Propagation

## Parent

`.scratch/stdin-mode-separation/001-prd.md`

## What to build

Inject `ExecutionContext` into `InputHandler` and `LicenseValidator` so downstream modules carry runtime policy rather than querying `sys.stdin` directly. This is what transforms the fix from "stdin patches" into "execution model architecture."

### InputHandler

Refactor `InputHandler.__init__()` to accept an optional `ExecutionContext`:

```python
def __init__(self, exec_context: Optional[ExecutionContext] = None):
    self._console = Console()
    self._exec_context = exec_context
```

When `_exec_context` is provided, `get_director_input()` and `prompt_continue()` use it instead of calling `stdin_available()` directly. When `_exec_context` is `None` (backward compatibility for tests), fall back to `require_stdin()`.

### LicenseValidator

Refactor `LicenseValidator.__init__()` to accept an optional `ExecutionContext`:

```python
def __init__(self, validator_url: str, config_path: Optional[str] = None,
             exec_context: Optional[ExecutionContext] = None):
    ...
    self._exec_context = exec_context
```

When `_exec_context` is provided and `mode == BATCH`, `prompt_and_validate()` raises `LicenseInputUnavailableError` immediately (no `stdin_available()` check needed). When `_exec_context` is `None`, fall back to `stdin_available()` check.

### Orchestrator changes

When creating `InputHandler` and `LicenseValidator` in `MainOrchestrator.__init__()`, pass `self._exec_context`:

```python
self._input_handler = InputHandler(exec_context=self._exec_context)
self._license_validator = LicenseValidator(..., exec_context=self._exec_context)
```

### Ownership table enforcement

After this slice, the ownership boundaries are:
- `stdin_guard` — environment capability detection only
- `ExecutionContext` — runtime policy carrier
- `orchestrator` — mode routing (does not check stdin directly after this slice)
- `InputHandler` — interactive-only data collection (uses `ExecutionContext` when available)
- `LicenseValidator` — license policy enforcement (uses `ExecutionContext` when available)

## Acceptance criteria

- [ ] `InputHandler.__init__()` accepts optional `exec_context: Optional[ExecutionContext]` parameter
- [ ] `InputHandler` uses `self._exec_context.interactive_allowed` instead of `stdin_available()` when context is available
- [ ] `InputHandler` falls back to `stdin_available()` when `exec_context` is `None` (backward compatibility)
- [ ] `LicenseValidator.__init__()` accepts optional `exec_context: Optional[ExecutionContext]` parameter
- [ ] `LicenseValidator` raises `LicenseInputUnavailableError` in `BATCH` mode when context is available
- [ ] `LicenseValidator` falls back to `stdin_available()` check when `exec_context` is `None`
- [ ] `MainOrchestrator` creates `InputHandler` and `LicenseValidator` with `exec_context` injection
- [ ] No module in the batch path queries `sys.stdin` directly (verified by test in Slice 6)

## Blocked by

- Slice 4 (005-input-license-guards.md) — guards must be installed before context can be propagated
