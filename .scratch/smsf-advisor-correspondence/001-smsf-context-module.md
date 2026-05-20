# SMSF Context Module

## Description

Create a new `SMSFContext` module that encapsulates all search-relevant SMSF metadata and becomes the canonical search input object for the application.

This module replaces the current keyword-first search approach with an SMSF-centric model.

## Responsibilities

- SMSF name storage
- Director names storage
- Director emails storage
- Normalized search tokens generation
- Advisor domains storage (domain-level, not individual)
- Timeframe configuration (start date, end date)
- JSON/YAML serialization for batch input

## Data Structure

```python
@dataclass
class SMSFContext:
    smsf_name: str                      # e.g., "Aura Super"
    director_names: List[str]          # e.g., ["John Smith", "Jane Doe"]
    director_emails: List[str]         # e.g., ["john@example.com"]
    advisor_domains: List[str]         # e.g., ["ventasadvisory.com.au", "exceedia.com.au"]
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    normalized_tokens: List[str]       # auto-generated search tokens
```

## Acceptance Criteria

- [ ] Module can be instantiated with SMSF name, directors, and advisor domains
- [ ] Module generates normalized search tokens automatically
- [ ] Module supports serialization to/from JSON for batch processing
- [ ] Module provides search token access for search engine
- [ ] Module is immutable after construction
- [ ] Unit tests verify token generation and serialization