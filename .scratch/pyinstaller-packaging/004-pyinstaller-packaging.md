---
labels: [ready-for-agent]
---

# 004-pyinstaller-packaging

## Parent

EXE Packaging with Online License Validation

## What to build

Package the entire application as a single Windows .exe file using PyInstaller.

Create:
- requirements.txt with all runtime dependencies (pywin32, playwright)
- build.bat that installs dependencies and runs PyInstaller
- PyInstaller spec or CLI configuration

Configuration:
- Single-file output: --onefile --name email-to-pdf
- Hidden imports: win32com, win32com.client, pythoncom
- Playwright browser binary bundled or downloaded as post-build step
- Output: dist\email-to-pdf.exe

## Acceptance criteria

- [ ] requirements.txt created with all dependencies
- [ ] build.bat installs dependencies and produces single EXE
- [ ] EXE runs successfully on a clean Windows machine with Outlook installed
- [ ] EXE validates license keys correctly
- [ ] EXE generates PDFs correctly
- [ ] EXE file size is reasonable (under 200MB)
- [ ] Playwright browser is bundled or auto-downloaded

## Blocked by

- 003-mainorchestrator-license-integration
