---
labels: [ready-for-agent]
---

# 001-add-format-date-helper

## Parent

Email Formatting Improvement & Architecture Consolidation

## What to build

Add a \_format_date(sent_on)\ helper method to \EmailFormatter\ that converts Outlook \SentOn\ values into human-readable verbal format like "Sunday, May 17, 2026 9:25 PM".

The method must handle three input types:
1. Python \datetime\ objects — format directly
2. \pywintypes.datetime\ objects (from win32com) — detect via \.year\/\.month\/\.day\ attributes, construct standard \datetime\
3. String fallback — parse with \datetime.fromisoformat()\, strip timezone offset, format without timezone conversion

Returns empty string for \None\ or empty input. Output format: \"%A, %B %d, %Y %I:%M %p"\ with leading zero stripped from hour.

No timezone conversion — display time as-is.

## Acceptance criteria

- [ ] \_format_date()\ method exists on \EmailFormatter\
- [ ] Handles Python \datetime\ objects correctly
- [ ] Handles \pywintypes.datetime\-like objects (detected via \.year\/\.month\/\.day\ attributes)
- [ ] Handles ISO format strings with timezone offset
- [ ] Returns empty string for \None\/empty input
- [ ] Output matches format "Sunday, May 17, 2026 9:25 PM"
- [ ] 5 unit tests covering all input types and edge cases
- [ ] All 78 existing tests still pass

## Blocked by

None - can start immediately
