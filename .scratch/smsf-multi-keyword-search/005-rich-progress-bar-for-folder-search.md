---
labels: [ready-for-agent]
---

# Slice 5: Rich Progress Bar for Folder Search

## Parent

(Standalone feature - no parent issue)

## What to build

Replace text-only progress with `rich.progress.Progress` bar.

### Files to Touch

- `src/progress_manager.py` — Add `Progress` instance with `BarColumn`, `TextColumn`, `TimeElapsedColumn`
- `src/progress_manager.py` — `start()` initializes progress with total folder count
- `src/progress_manager.py` — `update_activity()` advances the bar
- `src/email_searcher.py` — Count folders first, pass total to `ProgressManager`

```python
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn

# In ProgressManager
self._progress = Progress(
    BarColumn(),
    TextColumn("[progress.description]{task.description}"),
    TimeElapsedColumn(),
    console=self._console,
)
self._task = self._progress.add_task("Searching...", total=folder_count)

# Advance
self._progress.advance(self._task)
```

## Acceptance criteria

- [ ] Progress bar shows folder completion (e.g., `[████░░░░░░] 40%`)
- [ ] Current folder name displayed
- [ ] Only shown when `sys.stdout.isatty()`
- [ ] Tests verify progress manager integration

## Blocked by

- None — can start immediately (parallel with Slice 1)