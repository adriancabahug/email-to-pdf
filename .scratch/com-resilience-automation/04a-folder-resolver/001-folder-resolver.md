# FolderResolver: Folder Policy, Priority/Skip Rules, Fast/Deep Folder Sets

## What to build

Centralized folder selection logic, isolated from search execution. Reads priority and skip folder lists from ConfigManager. Provides deterministic folder sets for Fast and Deep search modes.

**Interface:**

`get_fast_folders(root_folders) → list[folder]`
- Returns only the folders matching names in `search.priority_folders`
- Exact string match on folder display name
- Missing folders silently skipped
- Skips everything in hardcoded skip list (RSS Feeds, Sync Issues, Junk Email, Deleted Items, Public Folders, Archive, Drafts)

`get_deep_folders(root_folders) → list[folder]`
- Recursive traversal of all non-skipped folders
- Respects hardcoded skip list
- Includes priority folders plus any other non-skipped folder

**Hardcoded skip list** (always skipped regardless of mode):
- RSS Feeds
- Sync Issues
- Junk Email
- Deleted Items
- Public Folders
- Archive
- Drafts

**Config-driven priority list** (default: `["Inbox", "Sent Items"]`):
- User can override in config.json
- Exact folder names only — no heuristics
- Order is preserved as specified in config

**Interface contract:**
- Input: root Outlook folder objects (from Namespace.Folders)
- Output: filtered folder list for the requested mode
- Depends on: ConfigManager (for priority_folders, skip_folders)

**No existing file to edit — create as new module at `src/folder_resolver.py`.**

## Acceptance criteria

- [ ] Fast mode returns only priority folders from config
- [ ] Deep mode returns all non-skipped folders recursively
- [ ] Hardcoded skip list folders are excluded in both modes
- [ ] Missing priority folders are silently skipped (no error)
- [ ] Folder resolution is deterministic and reproducible
- [ ] No prompts during folder resolution
- [ ] Folder names matched exactly (case-insensitive comparison)

## Blocked by

- 001-config-manager.md