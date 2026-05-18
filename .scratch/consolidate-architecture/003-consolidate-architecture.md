---
labels: [ready-for-agent]
---

# 003-consolidate-architecture

## Parent

Email Formatting Improvement & Architecture Consolidation

## What to build

Consolidate formatting logic so \EmailFormatter\ is the single canonical source, injected into \FileManager\ as a dependency. Remove all dead code.

**FileManager changes**:
- Remove \ormat_email()\ and \ormat_multiple_emails()\ methods (duplicated from EmailFormatter)
- Remove \save_html()\ method (unused fallback)
- Remove \	emp_html_path\ parameter from \save_pdf()\ (dead code)
- Add \email_formatter: Optional[EmailFormatter] = None\ to \__init__\
- Default: instantiate \EmailFormatter()\ internally if none provided

**MainOrchestrator changes**:
- Pass \email_formatter=self.email_formatter\ when constructing \FileManager\
- Remove \save_html\ fallback block in \_process_single_director()\

**Test changes**:
- Delete \	est_email_formatter_consolidation.py\
- Add \	est_email_formatter_injection.py\ (4 tests, patterned after \	est_pdf_generator_injection.py\)
- Update \	est_file_manager.py\ and \	est_main_orchestrator.py\ to reflect new interfaces

## Acceptance criteria

- [ ] \EmailFormatter\ is single source of formatting logic
- [ ] \FileManager\ accepts \email_formatter\ via dependency injection
- [ ] \FileManager\ has no \ormat_email\ or \ormat_multiple_emails\ methods
- [ ] \FileManager\ has no \save_html\ method
- [ ] \save_pdf()\ has no \	emp_html_path\ parameter
- [ ] \MainOrchestrator\ passes \EmailFormatter\ to \FileManager\
- [ ] \	est_email_formatter_consolidation.py\ deleted
- [ ] \	est_email_formatter_injection.py\ created with 4 passing tests
- [ ] All 78+ tests still pass

## Blocked by

- 002-improve-email-formatter

