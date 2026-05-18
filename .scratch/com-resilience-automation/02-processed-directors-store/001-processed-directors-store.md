# Processed Director Persistence (AppData State Store)

## What to build

State persistence for processed directors, enabling resume after interruption. Persists to `%APPDATA%/EmailToPDF/processed_directors.json`. Uses atomic write (write to temp file, then rename) to avoid corruption on crash.

**ProcessedDirectorsStore** provides:
- `is_processed(director_name) → bool` — check if a director was already processed
- `mark_processed(director_name) → None` — record a successful processing
- `get_all() → set[str]` — return all processed director names
- Auto-creates the state file on first use if missing

**State file format:**
```json
{
  "processed": [
    "John Smith",
    "Mary Jones"
  ]
}
```

**Interface contract:**
- Input: director name as string (exact match, case-insensitive normalized)
- Output: boolean membership check or side-effect-free registration
- Side effects: writes to AppData/processed_directors.json atomically
- Depends on: ConfigManager.appdata_dir()

**No existing file to edit — create as new module at `src/processed_directors_store.py`.**

## Acceptance criteria

- [ ] First run with no state file creates the file at the correct AppData path
- [ ] mark_processed() adds a director name to the set
- [ ] is_processed() returns True for a director that was marked
- [ ] is_processed() returns False for a director never processed
- [ ] Atomic write: crash between write and rename does not corrupt the file
- [ ] Concurrent access (two processes) does not corrupt the file
- [ ] Empty director name is handled gracefully (ignored, not stored)

## Blocked by

- 001-config-manager.md