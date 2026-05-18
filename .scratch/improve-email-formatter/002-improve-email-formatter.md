---
labels: [ready-for-agent]
---

# 002-improve-email-formatter

## Parent

Email Formatting Improvement & Architecture Consolidation

## What to build

Replace the email formatting logic in \EmailFormatter\ to produce Outlook-style PDF output:

**Header layout**: Outlook-style typography hierarchy with sender name at 16pt bold, properties (From, Sent, To, CC, Subject) at 11pt Calibri. No borders, no \<hr />\ separators.

**Conditional CC**: Only render CC line if recipients exist. Omit entirely when empty (no "CC: (None)").

**HTMLBody handling**: Strip outer \<html>\, \<head>\, \<body>\ tags from \html_body\ before prepending the header. Preserves inline images and CSS. Falls back to \<pre>\-wrapped plain text when no HTMLBody.

**Page breaks**: Each email container gets \page-break-inside: avoid\.

**Date integration**: Uses the \_format_date()\ helper from slice 001 instead of \str(sent_on)\.

Updates existing 6 formatter tests to match new behavior.

## Acceptance criteria

- [ ] Header uses 16pt sender name, 11pt Calibri properties, no borders
- [ ] CC line omitted when empty
- [ ] Date displayed in verbal format (not raw ISO string)
- [ ] HTMLBody outer tags stripped before embedding
- [ ] Page-break styling present on email containers
- [ ] Plain text fallback uses \<pre>\ with Calibri font
- [ ] All existing formatter tests updated and passing
- [ ] All 78+ tests still pass

## Blocked by

- 001-add-format-date-helper

