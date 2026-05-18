---
labels: [ready-for-agent]
---

# 003-mainorchestrator-license-integration

## Parent

EXE Packaging with Online License Validation

## What to build

Integrate license validation into the MainOrchestrator so that the tool validates a license key before running the email-to-PDF workflow.

On launch:
1. Check for stored key in %APPDATA%\EmailToPDF\config.json
2. If stored key exists, validate it against the Cloudflare Worker
3. If valid, proceed with existing workflow (connect to Outlook, search emails, generate PDF)
4. If invalid/expired/missing, prompt user for new key via interactive CLI
5. Validate the entered key; if valid, store it and proceed
6. If validation fails, show appropriate error message and exit

Error messages:
- Invalid key: "Invalid license key. Please contact your administrator for a valid key."
- Expired key: "Your license key has expired. Please contact your administrator for a new key."
- Network error: "Unable to validate license. Check your internet connection and try again."

## Acceptance criteria

- [ ] MainOrchestrator validates license before connecting to Outlook
- [ ] Stored key is validated automatically on subsequent launches
- [ ] User is prompted for key on first launch or when stored key is invalid
- [ ] Valid key is stored and workflow proceeds
- [ ] Invalid/expired key shows clear error message and exits
- [ ] Network error shows appropriate message and exits
- [ ] Existing orchestrator tests updated to mock license validation
- [ ] All 89+ existing tests still pass

## Blocked by

- 001-license-validator-module
