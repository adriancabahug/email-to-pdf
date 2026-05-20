# Batch Processing (~5 SMSFs per run)

## Description

Support batch processing of approximately 5 SMSFs per run, each generating multiple advisor PDFs.

## Requirements

- Accept batch input via JSON/YAML configuration file
- Process multiple SMSF contexts sequentially
- Generate multiple PDFs per SMSF (one per advisor organization)
- Report progress for entire batch
- Continue processing on individual SMSF failures
- Provide summary at batch completion

## Input Format

```yaml
smsfs:
  - smsf_name: "Aura Super"
    director_names:
      - "John Smith"
      - "Jane Doe"
    director_emails:
      - "john@aura.com.au"
    advisor_domains:
      - "ventasadvisory.com.au"
      - "exceedia.com.au"
    timeframe: "current_year"

  - smsf_name: "Beta Super"
    # ... next SMSF
```

## Key Interfaces

```python
class BatchProcessor:
    def load_batch_input(self, path: Path) -> List[SMSFContext]: ...
    def process_batch(self, contexts: List[SMSFContext]) -> BatchResult: ...

@dataclass
class BatchResult:
    total: int
    succeeded: int
    failed: int
    pdfs_generated: List[Path]
    errors: List[str]
```

## Acceptance Criteria

- [ ] Loads SMSF configurations from JSON/YAML file
- [ ] Processes each SMSF through full pipeline
- [ ] Generates multiple PDFs per SMSF (advisor org level)
- [ ] Reports individual and batch progress
- [ ] Continues on failure (doesn't stop entire batch)
- [ ] Provides summary with success/failure counts
- [ ] Integration tests verify full batch workflow