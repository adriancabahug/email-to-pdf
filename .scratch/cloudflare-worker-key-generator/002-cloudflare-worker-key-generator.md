---
labels: [ready-for-agent]
---

# 002-cloudflare-worker-key-generator

## Parent

EXE Packaging with Online License Validation

## What to build

Deploy a Cloudflare Worker that serves as the license validation server, and create a key generator script.

**Cloudflare Worker:**
- Endpoint: POST /validate
- Request body: {"key": "XXXXXX-XXXXXX-XXXXXX"}
- Key storage: Worker KV store or embedded JSON config
- Response: {"valid": true} or {"valid": false, "reason": "expired"} or {"valid": false, "reason": "invalid"}
- CORS: Allow all origins
- Keys have fixed expiration dates

**Key Generator Script:**
- Command: python scripts/generate_key.py --days 90
- Output: Prints generated key to stdout
- Key format: Three segments of 6 uppercase alphanumeric characters (e.g., A3F7K2-M9P1X4-R6T8W0)
- Outputs the key + expiration date in the format needed for Cloudflare Worker config
- Uses secrets module for cryptographically random generation

## Acceptance criteria

- [ ] Cloudflare Worker deployed and accessible
- [ ] POST /validate returns correct responses for valid, expired, and invalid keys
- [ ] Key generator script produces keys in XXXXXX-XXXXXX-XXXXXX format
- [ ] Key generator accepts --days flag to control expiration
- [ ] Generated keys can be added to Cloudflare Worker config
- [ ] Manual end-to-end test: generate key, add to Worker, validate via curl

## Blocked by

None - can start immediately (requires human Cloudflare account access)
