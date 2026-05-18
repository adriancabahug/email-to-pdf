# Rich CLI + ProgressManager: Structured Output and Progress Visibility

## What to build

Abstraction layer over Rich for all operator-facing output. Not a direct print() replacement — business logic calls ProgressManager methods, which render Rich components.

**ProgressManager provides:**
- `start()` / `stop()` — overall session lifecycle
- `start_search(director_name)` — indicate search phase beginning
- `update_activity(folder_name, emails_found, matches_found)` — live status during traversal
- `increment_emails()` — bump email count
- `show_retry(attempt, max_attempts, delay_remaining)` — retry indicator during backoff
- `show_outlook_restart(event_type)` — visible Outlook restart notification
- `show_error(category, message, action)` — structured error panel (replaces stack traces)
- `show_completion_summary(total_processed, pdfs_generated, failures)` — final stats
- `set_verbose(enabled)` — toggle detailed diagnostics

**Output components:**
- StatusBar: current operation, elapsed time
- SearchProgress: accounts/folders/emails/matches counts
- RetryIndicator: attempt number, delay countdown
- ErrorPanel: category, message, suggested action
- CompletionSummary: final statistics

**Two log levels:**
- `info` (default): clean operator-facing output, no raw traces
- `verbose`: detailed diagnostics for troubleshooting

**Structured error format (normal mode):**
```
[WARN] RPC unavailable — retry 2/3 in 5s
[WARN] Outlook unresponsive — restarting process
[INFO] Reconnected to Outlook session
[ERROR] Category D: Outlook requires user login. Please sign in to Outlook manually.
```

**Interface contract:**
- Input: progress events from business logic (search, PDF, retry, error)
- Output: Rich-rendered terminal output
- Depends on: ConfigManager (for logging level, verbose mode)
- Abstraction boundary: can be replaced with GUI/system tray wrapper without changing business logic

**No existing file to edit — create as new module at `src/progress_manager.py`.** Update `src/main_orchestrator.py` to use ProgressManager instead of print() statements.

## Acceptance criteria

- [ ] Search activity shows current folder, emails found, matches found
- [ ] Retry attempts show attempt number and delay countdown
- [ ] Outlook restart events are clearly visible in output
- [ ] Errors display as structured panels in info mode (no raw stack traces)
- [ ] Verbose mode shows detailed diagnostics when enabled
- [ ] Completion summary shows total processed, PDFs generated, failures
- [ ] All output is Rich-rendered (colors, spinners, progress bars)
- [ ] ProgressManager interface allows UI replacement without business logic changes

## Blocked by

- 001-config-manager.md
- 002-processed-directors-store.md
- 003-outlook-session-manager.md
- 04a-folder-resolver.md
- 04b-email-searcher.md