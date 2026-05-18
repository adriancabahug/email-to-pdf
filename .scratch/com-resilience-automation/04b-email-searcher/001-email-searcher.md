# EmailSearcher: Restrict() Pipeline, Fast/Deep Modes, Phase 1/2 Validation

## What to build

Redesigned search pipeline with two-phase filtering and configurable search modes. Replaces the current iterative full-mailbox traversal.

**Phase 1 — Outlook Restrict (metadata pre-filter):**
- Combine sender + date range into a single `Items.Restrict()` call
- Format: `[SenderEmailAddress] = 'x' AND [ReceivedTime] >= 'MM/DD/YYYY'`
- Sort results descending by ReceivedTime
- Only uses safe metadata fields: SenderEmailAddress, To, CC, ReceivedTime
- Reduces candidate set at COM level before Python processes anything

**Phase 2 — Python metadata validation:**
- Iterate Restrict() result set (already reduced)
- Check if director email appears in To or CC fields (header only)
- Optional subject keyword check if configured
- No body access in Phase 2 — only metadata fields
- Normalized string comparison (case-insensitive)

**Search modes:**
- **Fast**: FolderResolver.get_fast_folders() + Restrict() + date filter. Inbox + Sent only.
- **Deep**: FolderResolver.get_deep_folders() + Restrict(). Fall back to manual iteration if Restrict fails on a folder. No auto-escalation.

**Performance rules:**
- Body/HTMLBody never accessed during Phase 1 or Phase 2
- Body only loaded in Phase 3 (PDF generation)
- Sort by ReceivedTime descending; early-exit when oldest message exceeds date cutoff
- Date range: default 90 days from config, configurable

**Interface contract:**
- `search(director_email, mode: str) → list[email_item]`
- `mode` is "fast" or "deep"
- Output: list of matched email items with full metadata
- Depends on: OutlookSessionManager (for COM access with retry), FolderResolver, ConfigManager (for date range and mode defaults), ProcessedDirectorsStore (skip already-processed)

**Modify `src/email_searcher.py`.** Replace existing iterative traversal with the Restrict() pipeline.

## Acceptance criteria

- [ ] Restrict() query is built with correct date format (MM/DD/YYYY)
- [ ] Restrict() combines sender and date in a single query
- [ ] Phase 2 validates To/CC metadata without reading body
- [ ] Body/HTMLBody is never accessed during search
- [ ] Fast mode searches only priority folders
- [ ] Deep mode recursively traverses all non-skipped folders
- [ ] Deep mode falls back to manual iteration when Restrict() fails
- [ ] Deep mode is not auto-selected — requires explicit mode parameter
- [ ] Results sorted by ReceivedTime descending
- [ ] Already-processed directors are skipped from search
- [ ] Missing folders are silently skipped

## Blocked by

- 001-config-manager.md
- 002-processed-directors-store.md
- 003-outlook-session-manager.md
- 04a-folder-resolver.md