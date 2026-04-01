"""Tests for Logger per-thread ERROR counting (reset_error_count / get_error_count)."""

import threading
import pytest

from laughtrack.foundation.infrastructure.logger.logger import Logger


class TestLoggerErrorCount:
    def setup_method(self):
        # Ensure logger is configured before each test
        if not Logger._configured:
            Logger.configure()

    def test_count_increments_on_error(self):
        Logger.reset_error_count()
        Logger.error("first error")
        Logger.error("second error")
        assert Logger.get_error_count() == 2

    def test_warning_not_counted(self):
        Logger.reset_error_count()
        Logger.warning("a warning")
        Logger.info("an info")
        assert Logger.get_error_count() == 0

    def test_get_resets_state(self):
        Logger.reset_error_count()
        Logger.error("test")
        Logger.get_error_count()
        # After get, counter is inactive — new errors should not be counted
        Logger.error("after get")
        assert Logger.get_error_count() == 0

    def test_no_count_before_reset(self):
        # Deactivate any existing count
        Logger.get_error_count()
        Logger.error("should not count")
        assert Logger.get_error_count() == 0

    def test_thread_isolation(self):
        """ERROR logs on thread A do not affect thread B's count."""
        counts = {}

        def thread_fn(name, n_errors):
            Logger.reset_error_count()
            for _ in range(n_errors):
                Logger.error(f"error from {name}")
            counts[name] = Logger.get_error_count()

        t1 = threading.Thread(target=thread_fn, args=("A", 3))
        t2 = threading.Thread(target=thread_fn, args=("B", 7))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert counts["A"] == 3
        assert counts["B"] == 7
