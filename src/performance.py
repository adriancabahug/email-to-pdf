"""Lightweight performance instrumentation for measuring operation timing."""

import logging
import time
from contextlib import contextmanager
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class PerformanceTimer:
    """Simple performance timer for tracking operation durations."""

    def __init__(self, operation: str) -> None:
        self._operation = operation
        self._start: Optional[float] = None
        self._end: Optional[float] = None

    def __enter__(self) -> "PerformanceTimer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._end = time.perf_counter()
        duration_ms = (self._end - self._start) * 1000
        logger.info("%s took %.2f ms", self._operation, duration_ms)

    @property
    def duration_ms(self) -> Optional[float]:
        if self._start and self._end:
            return (self._end - self._start) * 1000
        return None


class PerformanceTracker:
    """Accumulates timing statistics across multiple operations."""

    def __init__(self) -> None:
        self._timings: Dict[str, list] = {}

    @contextmanager
    def track(self, operation: str):
        """Context manager to track an operation's duration."""
        start = time.perf_counter()
        try:
            yield
        finally:
            end = time.perf_counter()
            duration_ms = (end - start) * 1000
            if operation not in self._timings:
                self._timings[operation] = []
            self._timings[operation].append(duration_ms)
            logger.debug("%s: %.2f ms", operation, duration_ms)

    def get_stats(self, operation: str) -> Dict[str, float]:
        """Get min, max, avg, total for an operation."""
        timings = self._timings.get(operation, [])
        if not timings:
            return {"count": 0, "min": 0, "max": 0, "avg": 0, "total": 0}
        return {
            "count": len(timings),
            "min": min(timings),
            "max": max(timings),
            "avg": sum(timings) / len(timings),
            "total": sum(timings),
        }

    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """Get stats for all tracked operations."""
        return {op: self.get_stats(op) for op in self._timings}

    def reset(self) -> None:
        """Reset all timings."""
        self._timings.clear()


_global_tracker = PerformanceTracker()


def get_tracker() -> PerformanceTracker:
    """Get the global performance tracker instance."""
    return _global_tracker