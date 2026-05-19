---
labels: [ready-for-agent]
---

# Slice 4: SMSF-Centric PDF Output

## Parent

(Standalone feature - no parent issue)

## What to build

One PDF per SMSF with per-email page breaks and header banners.

### Files to Touch

- `src/file_manager.py` — `generate_filename()` returns `f"{smsf} - Email Export.pdf"`
- `src/email_formatter.py` — `format_multiple_emails()` wraps each email in a page-break div + header banner
- `src/email_formatter.py` — Header banner HTML:
  ```html
  <div style="border-bottom: 2px solid #333; padding: 10px 0; margin-bottom: 20px; page-break-before: always;">
    <strong>Email {index} of {total}</strong> |
    <strong>From:</strong> {sender} |
    <strong>To:</strong> {to} |
    <strong>Date:</strong> {date} |
    <strong>Subject:</strong> {subject}
  </div>
  ```
- `src/email_formatter.py` — First email has `page-break-before: auto`, rest have `page-break-before: always`

## Acceptance criteria

- [ ] Filename: `{SMSF} - Email Export.pdf`
- [ ] Path: `%USERPROFILE%\Documents\EmailPDFs\{SMSF}\`
- [ ] Each email starts on new page with header banner
- [ ] Full HTML body rendered
- [ ] Tests verify filename and HTML structure

## Blocked by

- Slice 3 (003-email-deduplication-and-chronological-sort.md) — needs emails to format