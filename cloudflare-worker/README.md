# Cloudflare Worker - License Server

## Deploy

```bash
cd cloudflare-worker
npm install -g wrangler
wrangler login
wrangler deploy
```

The Worker URL will be printed after deployment (e.g., `https://email-to-pdf-license.your-account.workers.dev`).

Update `src/license_validator.py` with this URL in the `LicenseValidator` constructor call in `main_orchestrator.py`.

## Manage Keys

Keys are stored in the `KEYS` object in `index.js`.

### Add a key

Generate one:
```bash
python scripts/generate_key.py --days 90
```

Then paste the output into `index.js`:
```javascript
const KEYS = {
  "ABC123-DEF456-GHI789": { "expires": "2026-08-01" }
};
```

### Remove a key

Delete the entry from `KEYS` and redeploy.

### Redeploy

```bash
wrangler deploy
```

## Test

```bash
curl -X POST https://email-to-pdf-license.your-account.workers.dev/validate \
  -H "Content-Type: application/json" \
  -d '{"key": "ABC123-DEF456-GHI789"}'
```
