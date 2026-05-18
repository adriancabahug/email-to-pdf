# OutlookSessionManager: COM Retry, Backoff, and Crash Recovery

## What to build

Centralized Outlook COM lifecycle manager with two-tier error recovery. All COM operations go through this module — no direct COM calls in business logic.

**COM lifecycle:**
- `connect()` → establishes pythoncom + Dispatch + MAPI namespace
- `disconnect()` → cleanup on normal exit
- `is_healthy()` → lightweight health check (e.g., Namespace.Folders.Count)

**Two-tier recovery:**

**Tier 1 — Transient retry (Category A):**
Any `Exception` during a COM call → exponential backoff retry:
- Attempt 1: wait 2s ± 1s jitter
- Attempt 2: wait 5s ± 1s jitter
- Attempt 3: wait 10s ± 1s jitter
No Outlook restart during Tier 1.

**Tier 2 — Process-level recovery (Categories B/C):**
After 3 Tier-1 failures → escalate via psutil:
- Check if `OUTLOOK.EXE` process is running
- If not running (Category B): launch Outlook, wait for initialization, reconnect
- If running but unhealthy (Category C): terminate process, relaunch, reconnect
- Max 2 restart attempts
- After restart exhaustion: Category D — surface actionable operator message, no further retry

**Category D (user intervention required):**
- Profile prompt, credential popup, OST repair dialog, modal UI
- Fail gracefully with clear message. Never retry indefinitely.

**All old COM references are discarded and recreated after a restart.**

**Interface contract:**
- `connect() → bool`
- `disconnect() → None`
- `is_healthy() → bool` — lightweight COM call to verify session is still valid
- `wrap(com_call: Callable) → Any` — executes a COM operation with full retry/recovery logic
- Depends on: ConfigManager (for timeouts, backoff, retry counts)

**Modify `src/outlook_connection.py` to delegate to OutlookSessionManager, or replace with the new module.** The existing `connect()` / `get_all_accounts()` / `get_all_folders_recursive()` methods should route through the session manager's wrap() method.

## Acceptance criteria

- [ ] Transient COM exception triggers backoff retry without restarting Outlook
- [ ] After 3 retries, psutil checks for OUTLOOK.EXE process
- [ ] If Outlook not running, process is launched and COM reconnects
- [ ] If Outlook running but unhealthy, process is terminated and relaunched
- [ ] Category D failure surfaces a clear operator message with no infinite retry
- [ ] Old COM references are discarded after restart
- [ ] Retry delay follows exponential backoff with jitter as configured
- [ ] Max restart threshold (2) is enforced

## Blocked by

- 001-config-manager.md