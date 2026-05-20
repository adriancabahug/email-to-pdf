"""
Tests for Timeframe Resolver.
"""

from datetime import datetime

import pytest

from src.smsf_context import SMSFContext
from src.timeframe_resolver import TimeframeResolver


class TestTimeframeResolver:
    def test_default_is_current_year(self):
        resolver = TimeframeResolver()
        start, end = resolver.get_timeframe()

        current_year = datetime.now().year
        assert start.year == current_year
        assert start.month == 1
        assert start.day == 1
        assert end.year == current_year
        assert end.month == 12
        assert end.day == 31

    def test_current_year_string(self):
        resolver = TimeframeResolver()
        start, end = resolver.parse_timeframe("current_year")

        current_year = datetime.now().year
        assert start.year == current_year
        assert end.year == current_year

    def test_all_time_returns_none_dates(self):
        resolver = TimeframeResolver()
        start, end = resolver.parse_timeframe("all_time")

        assert start is None
        assert end is None

    def test_custom_range_with_dates(self):
        resolver = TimeframeResolver()
        start, end = resolver.parse_timeframe("custom", start_date=datetime(2025, 1, 1), end_date=datetime(2025, 12, 31))

        assert start == datetime(2025, 1, 1)
        assert end == datetime(2025, 12, 31)


class TestTimeframeResolverOverrides:
    def test_smsf_context_overrides_default(self):
        resolver = TimeframeResolver()
        resolver.set_default_timeframe("current_year")

        context = SMSFContext(
            smsf_name="Test",
            director_names=[],
            director_emails=[],
            advisor_domains=[],
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
        )

        start, end = resolver.get_timeframe(context)

        assert start == datetime(2024, 1, 1)
        assert end == datetime(2024, 12, 31)

    def test_default_when_no_context(self):
        resolver = TimeframeResolver()
        resolver.set_default_timeframe("all_time")

        start, end = resolver.get_timeframe()

        assert start is None
        assert end is None


class TestTimeframeStringParsing:
    def test_case_insensitive(self):
        resolver = TimeframeResolver()

        start1, end1 = resolver.parse_timeframe("current_year")
        start2, end2 = resolver.parse_timeframe("CURRENT_YEAR")
        start3, end3 = resolver.parse_timeframe("Current_Year")

        assert start1 == start2 == start3
        assert end1 == end2 == end3

    def test_invalid_timeframe_raises(self):
        resolver = TimeframeResolver()

        with pytest.raises(ValueError):
            resolver.parse_timeframe("invalid_timeframe")