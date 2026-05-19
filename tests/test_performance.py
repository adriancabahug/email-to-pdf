"""
Tests for performance instrumentation.
"""

import pytest
import time

from src.performance import PerformanceTimer, PerformanceTracker, get_tracker


class TestPerformanceTimer:
    """Tests for PerformanceTimer context manager."""

    def test_timer_measures_duration(self):
        with PerformanceTimer("test_op") as timer:
            time.sleep(0.01)

        assert timer.duration_ms is not None
        assert timer.duration_ms > 0

    def test_timer_logs_on_exit(self):
        with PerformanceTimer("measured_op") as timer:
            time.sleep(0.001)


class TestPerformanceTracker:
    """Tests for PerformanceTracker."""

    def test_track_single_operation(self):
        tracker = PerformanceTracker()

        with tracker.track("test"):
            time.sleep(0.001)

        stats = tracker.get_stats("test")
        assert stats["count"] == 1
        assert stats["min"] > 0

    def test_track_multiple_operations(self):
        tracker = PerformanceTracker()

        for _ in range(3):
            with tracker.track("test"):
                time.sleep(0.001)

        stats = tracker.get_stats("test")
        assert stats["count"] == 3

    def test_get_stats_empty(self):
        tracker = PerformanceTracker()
        stats = tracker.get_stats("nonexistent")
        assert stats["count"] == 0

    def test_get_all_stats(self):
        tracker = PerformanceTracker()

        with tracker.track("op1"):
            time.sleep(0.001)
        with tracker.track("op2"):
            time.sleep(0.001)

        all_stats = tracker.get_all_stats()
        assert "op1" in all_stats
        assert "op2" in all_stats

    def test_reset_clears_timings(self):
        tracker = PerformanceTracker()

        with tracker.track("test"):
            time.sleep(0.001)

        tracker.reset()
        stats = tracker.get_stats("test")
        assert stats["count"] == 0


class TestGlobalTracker:
    """Tests for the global tracker singleton."""

    def test_get_tracker_returns_same_instance(self):
        t1 = get_tracker()
        t2 = get_tracker()
        assert t1 is t2