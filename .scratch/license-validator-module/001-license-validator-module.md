---
labels: [ready-for-agent]
---

# 001-license-validator-module

## Parent

EXE Packaging with Online License Validation

## What to build

Create a new LicenseValidator module that validates license keys against a Cloudflare Worker endpoint. The module should:

- Send a POST request to the Cloudflare Worker with the key
- Parse the response to determine if the key is valid, expired, or invalid
- Store validated keys locally in %APPDATA%\EmailToPDF\config.json
- Read stored keys on subsequent launches
- Handle network errors gracefully (retry once, 3-second timeout, clear error message)
- Provide a prompt_and_validate() function that prompts the user for a key, validates it, stores it if valid, and returns the key or None

Interface:
- validate_key(key: str) -> dict with {"valid": bool, "reason": str | None}
- get_stored_key() -> str | None
- store_key(key: str) -> None
- prompt_and_validate() -> str | None

## Acceptance criteria

- [ ] LicenseValidator module exists with validate_key, get_stored_key, store_key, prompt_and_validate methods
- [ ] validate_key returns {"valid": true} for valid keys from the server
- [ ] validate_key returns {"valid": false, "reason": "expired"} for expired keys
- [ ] validate_key returns {"valid": false, "reason": "invalid"} for unknown keys
- [ ] Network errors are handled gracefully with retry and timeout
- [ ] store_key writes to %APPDATA%\EmailToPDF\config.json
- [ ] get_stored_key reads from %APPDATA%\EmailToPDF\config.json
- [ ] get_stored_key returns None when no config file exists
- [ ] ~8 unit tests covering all behaviors (mocked HTTP responses and file I/O)
- [ ] All 89 existing tests still pass

## Blocked by

None - can start immediately
