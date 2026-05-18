---
labels: [ready-for-agent]
---

# PRD: EXE Packaging with Online License Validation

## Problem Statement

I need to distribute this email-to-PDF tool to my client as a standalone executable, but I don't want them to have permanent access. I need a licensing system where I generate time-limited keys that the client enters on first launch. When the key expires, the tool stops working until I issue a new one.

## Solution

Package the Python application as a single Windows .exe using PyInstaller, with an online license validation system. The EXE prompts for a key on first launch, validates it against a Cloudflare Worker I control, and stores the key locally. On subsequent launches it re-validates the stored key. If the key is expired or revoked, the tool refuses to run and prompts for a new key. I generate keys with a simple script where I control the expiration duration per key.

## User Stories

1. As the tool developer, I want to generate license keys with a specific expiration duration, so that I control exactly how long the client has access
2. As the tool developer, I want to revoke keys manually, so that I can cut off access immediately if needed
3. As the tool developer, I want a single .exe file to distribute, so that the client doesn't need to install Python or any dependencies
4. As the client, I want to enter my license key once on first launch, so that I don't have to type it every time I use the tool
5. As the client, I want the tool to validate my key automatically on each launch, so that I know immediately if my key has expired
6. As the client, I want a clear error message if my key is invalid or expired, so that I understand why the tool won't run and that I need to contact the developer
7. As the client, I want the tool to work normally after successful key validation, so that the licensing doesn't interfere with the email-to-PDF workflow
8. As the tool developer, I want the Cloudflare Worker to be free or near-zero cost, so that maintaining the licensing system doesn't add ongoing expense
9. As the tool developer, I want the key generator to be a simple script I run locally, so that I don't need a web interface or database admin panel
10. As the client, I want the tool to handle network errors gracefully, so that a temporary internet outage doesn't lock me out
11. As the tool developer, I want the EXE to include all dependencies (Playwright browser, win32com), so that the client has a zero-config experience
12. As the tool developer, I want the license validation to happen before any Outlook connection is attempted, so that invalid keys fail fast without unnecessary operations

## Implementation Decisions

### 1. License Validator Module

A new deep module with a simple interface:

- \alidate_key(key: str) -> dict\ — Sends key to Cloudflare Worker, returns \{"valid": true}\ or \{"valid": false, "reason": "expired" | "invalid"}\
- \get_stored_key() -> str | None\ — Reads key from \%APPDATA%\\EmailToPDF\\config.json\
- \store_key(key: str)\ — Writes key to \%APPDATA%\\EmailToPDF\\config.json\
- \prompt_and_validate() -> str | None\ — Prompts user for key, validates, stores if valid, returns key or None

Network errors: retry once with 3-second timeout. On failure, show "Unable to validate license. Check your internet connection." and exit.

### 2. Cloudflare Worker (License Server)

- Endpoint: \POST /validate\
- Request body: \{"key": "XXXXXX-XXXXXX-XXXXXX"}\
- Key storage: Worker KV store or simple JSON config embedded in the Worker
- Response format: \{"valid": true}\ or \{"valid": false, "reason": "expired"}\ or \{"valid": false, "reason": "invalid"}\
- CORS: Allow all origins (client runs locally)
- Free tier: 100,000 requests/day — more than sufficient

### 3. Key Generator Script

- Command: \python scripts/generate_key.py --days 90\
- Output: Prints the generated key to stdout
- Side effect: Outputs the key + expiration date in the format needed for Cloudflare Worker config
- Key format: Three segments of 6 uppercase alphanumeric characters, separated by hyphens (e.g., \A3F7K2-M9P1X4-R6T8W0\)
- Uses \secrets\ module for cryptographically random generation

### 4. MainOrchestrator Integration

License validation runs at the very start of \un()\, before \_connect_to_outlook()\:

1. Check for stored key in \%APPDATA%\\EmailToPDF\\config.json\
2. If stored key exists, validate it against Cloudflare Worker
3. If valid, proceed with existing workflow
4. If invalid/expired/missing, prompt user for new key
5. Validate the entered key; if valid, store it and proceed
6. If validation fails, show error message and exit

### 5. PyInstaller Packaging

- Single-file EXE: \pyinstaller --onefile --name email-to-pdf\
- Hidden imports: \win32com\, \win32com.client\, \pythoncom\
- Playwright browser: bundle Chromium using \--add-data\ or set \PLAYWRIGHT_BROWSERS_PATH\ environment variable in the EXE
- Output: \dist\\email-to-pdf.exe\ (single file, ~100-150MB)
- Build script: \uild.bat\ — installs dependencies, runs PyInstaller

### 6. Dependencies Management

Create \equirements.txt\ with all runtime dependencies:
- \pywin32\ (win32com integration)
- \playwright\ (PDF generation)

### 7. Key Storage Location

\%APPDATA%\\EmailToPDF\\config.json\ — standard Windows application data location. Content:
\{"license_key": "XXXXXX-XXXXXX-XXXXXX"}\

### 8. Error Messages

- Invalid key: "Invalid license key. Please contact your administrator for a valid key."
- Expired key: "Your license key has expired. Please contact your administrator for a new key."
- Network error: "Unable to validate license. Check your internet connection and try again."
- No key provided: "A license key is required to use this tool. Please enter your key."

## Testing Decisions

### What Makes a Good Test

Only test external behavior through public interfaces. Tests should verify:
- Key validation succeeds/fails correctly based on server response
- Key storage and retrieval works
- Error handling for network failures
- User prompt flow (mocked input)

### Modules to Test

| Module | Test File | Test Count | Prior Art |
|--------|-----------|------------|-----------|
| LicenseValidator | \	est_license_validator.py\ (new) | ~8 | \	est_pdf_generator_injection.py\ (mocking external services) |

### Test Specifications

**\	est_license_validator.py\** (~8 tests):
1. \	est_validate_key_returns_true_for_valid_key\ — Mock successful server response
2. \	est_validate_key_returns_false_for_invalid_key\ — Mock invalid key response
3. \	est_validate_key_returns_false_for_expired_key\ — Mock expired key response
4. \	est_validate_key_handles_network_error\ — Mock connection failure
5. \	est_validate_key_handles_timeout\ — Mock request timeout
6. \	est_store_key_writes_to_config_file\ — Verify file creation at correct path
7. \	est_get_stored_key_reads_from_config_file\ — Verify file reading
8. \	est_get_stored_key_returns_none_when_no_config\ — Verify missing file handling

### Tests NOT Needed

- Cloudflare Worker logic (tested manually, too simple to warrant unit tests)
- Key generator script (pure random generation, trivial)
- PyInstaller packaging (integration-level, verified by running the EXE)

## Out of Scope

- Web-based admin dashboard for key management
- Usage tracking or analytics
- Offline license validation
- Multi-machine license enforcement (key can be used on multiple machines)
- License key encryption at rest in config file
- Custom branded UI or splash screen
- Auto-update functionality
- Hardware-locked licenses (tied to specific machine)
- Trial mode or free tier

## Further Notes

- The Cloudflare Worker is the single point of control for all license management. The developer can add/remove/modify keys by updating the Worker config and redeploying — takes ~30 seconds.
- The tool already has 89 passing tests across 15 test files. The new license validation tests should follow the same patterns (mocking, behavior-focused).
- Playwright requires a browser binary to be available. PyInstaller needs special configuration to bundle the Chromium browser that Playwright uses, or the build script should download it as a post-build step.
- The client machine must have Outlook installed and configured (existing constraint, unchanged).
- The client machine must have internet access for license validation (new constraint introduced by this feature).
- The Cloudflare Worker free tier allows 100,000 requests per day, which is effectively unlimited for this use case (one client, one validation per launch).
