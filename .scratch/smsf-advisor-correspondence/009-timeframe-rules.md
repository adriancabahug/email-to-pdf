# Timeframe Rules

## Description

Support configurable date ranges for SMSF evidence searches.

## Supported Timeframes

1. **Current year** (default): January 1 - December 31 of current year
2. **All time**: No date restrictions
3. **Custom range**: User-specified start and end dates

## Configuration

Timeframe should be configurable at:
- Application level (default)
- Per-SMSF context level (overrides application default)

## Key Interfaces

```python
class TimeframeResolver:
    def get_timeframe(self, context: Optional[SMSFContext] = None) -> Tuple[datetime, datetime]: ...
    def set_default_timeframe(self, timeframe: str): ...
    def parse_timeframe(self, timeframe_str: str) -> Tuple[datetime, datetime]: ...
```

## Acceptance Criteria

- [ ] Default timeframe is current year (2026)
- [ ] Supports "current_year", "all_time", "custom" timeframe strings
- [ ] Custom timeframe accepts start_date and end_date
- [ ] Per-SMSF timeframe overrides application default
- [ ] Date range applied during search query
- [ ] Unit tests cover all timeframe modes