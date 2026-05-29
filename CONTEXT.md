# Domain Glossary

## SMSF (Self-Managed Super Fund)
The client entity whose email correspondence is being processed. Each SMSF run identifies a set of directors and their advisors.

## Director
A person who is a director or trustee of an SMSF. Directors are the sender/recipient side of the correspondence being exported.

## Advisor
A financial professional or firm that corresponds with SMSF directors. Advisors are identified by their email domain.

## Advisor Domain
An email domain that identifies a particular advisory firm or practice (e.g. `@accounting.com`, `@ventas.com`). Advisor domains are mapped to organization names and used to group emails into per-advisor PDFs.

## Email Extraction
The process of reading emails from Microsoft Outlook. Outlook must be installed and running on the same Windows machine.

## PDF Rendering
Converting formatted email HTML into PDF files using a browser engine to ensure pixel-perfect fidelity of complex HTML email content.

## Pipeline Stage
A discrete processing step in the email-to-PDF workflow: Search → Relevance Filtering → Deduplication → Advisor Grouping → Formatting → PDF Generation.

## Deduplication
Removing emails that appear in multiple Outlook mailboxes (e.g. Inbox + Sent Items, or multiple accounts) so each email appears only once in the final PDF.

## Batch Mode
Processing multiple SMSFs in a single run, with SMSF definitions loaded from a CSV or JSON file.

## Interactive Mode
Processing one SMSF at a time, with SMSF name, search terms, and date range entered via CLI prompts.
