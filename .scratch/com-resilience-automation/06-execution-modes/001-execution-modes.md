# Batch and Interactive Execution Modes with Controller Architecture

## What to build

First-class support for both interactive and batch modes. Mode is resolved at startup and delegates to the appropriate controller. Core services are mode-agnostic.

**Mode resolution:**
- `run_mode` from ConfigManager (default: "interactive")
- Batch mode: no prompts, directors from config, fully non-interactive, exit codes
- Interactive mode: default, uses Rich prompts for director input

**Controllers:**

`InteractiveController`:
- Prompts for director name via Rich
- Runs in a loop until operator exits
- Progress output via ProgressManager

`BatchController`:
- Reads `directors` list from ConfigManager
- No blocking prompts
- Deterministic output
- Exit codes: 0 = success, 1 = failure, 2 = partial

**Execution flow:**
```
App startup
  → ConfigManager.load()
  → ModeResolver (interactive / batch)
  → InteractiveController OR BatchController
  → WorkflowEngine (mode-agnostic)
  → OutlookSessionManager / EmailSearcher / PDFGenerator
```

Core services (EmailSearcher, PDFGenerator, OutlookSessionManager) receive structured parameters from the controller — they do not call Prompt.ask() or make UI assumptions.

**Interface contract:**
- Input: ConfigManager determines mode; BatchController reads directors list from config
- Output: exit code (0/1/2 for batch), Rich UI for interactive
- Depends on: ConfigManager, ProgressManager, ProcessedDirectorsStore, EmailSearcher

**Modify `src/main_orchestrator.py`.** Extract mode resolution logic, create controller classes. Update `input_handler.py` to use Rich prompts.

## Acceptance criteria

- [ ] Interactive mode prompts for director name using Rich
- [ ] Batch mode reads directors from config and processes without prompts
- [ ] Batch mode returns exit code 0 on full success, 1 on failure, 2 on partial
- [ ] Processed directors are skipped in both modes
- [ ] Core services (search, PDF, session) have no embedded UI/prompt calls
- [ ] Mode switching does not require changes to business logic

## Blocked by

- 001-config-manager.md
- 002-processed-directors-store.md
- 04b-email-searcher.md
- 05-rich-cli-progress.md