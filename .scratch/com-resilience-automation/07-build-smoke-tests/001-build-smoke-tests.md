# Build Pipeline Early Validation: PyInstaller, Playwright, Chromium, Startup

## What to build

Early smoke tests that run alongside slice 5 development, not after everything is done. Packaging issues surface early so they don't block final optimization.

**Build smoke tests to implement:**

1. **PyInstaller smoke test:**
   - Run `pyinstaller --onedir` on the current codebase
   - Verify the EXE starts without immediate crash
   - Verify COM registration works in the packaged environment
   - Verify AppData paths are created on first run

2. **Playwright runtime check:**
   - Verify browser binaries are present after installation
   - Run `playwright install chromium` as part of build
   - Verify Playwright can launch chromium in headless mode

3. **Chromium packaging check:**
   - Verify playwright's chromium is included or referenced in the bundle
   - Verify browser can navigate to a local file and render HTML

4. **Startup verification:**
   - EXE starts and connects to Outlook
   - ConfigManager loads defaults
   - No missing DLL errors
   - No pywin32 registration failures

5. **ConfigManager smoke test:**
   - Verify AppData directory creation
   - Verify config.json loading and defaults merge
   - Verify config validation fallbacks

**Build scripts to create:**
- `build.ps1` — reproducible PyInstaller build command
- `requirements-lock.txt` — pinned dependency versions (Playwright, rich, psutil, etc.)

**Interface contract:**
- Input: source code at current slice state
- Output: working .exe via --onedir, playwright browser present, no startup errors
- Depends on: ConfigManager (must pass smoke test)

**This runs alongside slice 5 development.** Do not wait until all slices are complete.

## Acceptance criteria

- [ ] `build.ps1` produces a working --onedir EXE
- [ ] EXE starts without immediate crash
- [ ] Playwright chromium launches in headless mode from the package
- [ ] ConfigManager smoke test passes (AppData paths, config loading)
- [ ] No missing DLL or pywin32 registration errors at startup
- [ ] `requirements-lock.txt` exists with pinned versions

## Blocked by

- 001-config-manager.md