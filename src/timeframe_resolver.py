"""
Timeframe Resolver - Handles date range configuration for SMSF searches.
"""

from datetime import datetime
from typing import Optional, Tuple

from src.smsf_context import SMSFContext


class TimeframeResolver:
    def __init__(self, default_timeframe: str = "current_year"):
        self._default_timeframe = default_timeframe

    def get_timeframe(self, context: Optional[SMSFContext] = None) -> Tuple[Optional[datetime], Optional[datetime]]:
        if context and context.start_date is not None and context.end_date is not None:
            return context.start_date, context.end_date

        return self.parse_timeframe(self._default_timeframe)

    def set_default_timeframe(self, timeframe: str) -> None:
        self._default_timeframe = timeframe

    def parse_timeframe(
        self,
        timeframe_str: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Tuple[Optional[datetime], Optional[datetime]]:
        normalized = timeframe_str.lower().strip()

        if normalized == "current_year":
            return self._get_current_year_range()

        if normalized == "all_time":
            return None, None

        if normalized == "custom":
            return start_date, end_date

        raise ValueError(f"Unknown timeframe: {timeframe_str}")

    def _get_current_year_range(self) -> Tuple[datetime, datetime]:
        current_year = datetime.now().year
        start = datetime(current_year, 1, 1)
        end = datetime(current_year, 12, 31, 23, 59, 59)
        return start, end