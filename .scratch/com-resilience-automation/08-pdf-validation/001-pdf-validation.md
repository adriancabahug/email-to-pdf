# PDF Rendering Validation Suite Across Email Sample Types

## What to build

Automated rendering validation before any bundle size optimization is attempted. Ensures headless Chromium produces acceptable output for the email-to-PDF use case.

**Test email samples (representative set):**
1. Plain text email (no HTML)
2. HTML email (basic formatting)
3. HTML email with nested reply chains
4. HTML email with inline images
5. HTML email with tables (aligned columns)
6. Email with long signature and legal disclaimer
7. Long thread (50+ emails, nested quotes)
8. Malformed HTML (malformed tags, unclosed elements)
9. Outlook-generated formatting quirks

**Validation criteria:**
- Text is readable
- Structure is preserved (from/to/subject/body)
- Inline content renders correctly
- Tables remain usable
- PDFs are professional-looking
- Consistent layout behavior across samples

**Not required:**
- Pixel-perfect Outlook rendering parity
- Enterprise-grade email client fidelity
- Exact font matching

**"High-quality operational rendering" is the standard.**

**Interface contract:**
- Input: sample HTML email files, Playwright headless shell
- Output: generated PDFs, pass/fail per sample, overall validation report
- Depends on: Slice 7 (build smoke tests must pass first)

This runs after Slice 7 and before Slice 9.

## Acceptance criteria

- [ ] All 9 sample email types render without crash
- [ ] Text is readable in all generated PDFs
- [ ] Email structure (from/to/subject/body) is preserved in all samples
- [ ] Nested replies render correctly (no content loss)
- [ ] Tables remain usable (columns aligned, content readable)
- [ ] Long signatures/disclaimers render without truncation
- [ ] Malformed HTML does not crash the renderer
- [ ] Validation report summarizes pass/fail per sample
- [ ] Headless Chromium (not full Chrome) is used for all renders

## Blocked by

- 07-build-smoke-tests.md