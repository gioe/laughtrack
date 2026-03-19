"""Unit tests for scripts/utils/scraper_status.py utility functions."""
from __future__ import annotations

import builtins
import io
import unittest.mock as mock
from pathlib import Path

from scripts.utils.scraper_status import find_latest_metrics, format_duration, print_summary


# ---------------------------------------------------------------------------
# find_latest_metrics
# ---------------------------------------------------------------------------

class TestFindLatestMetrics:
    def test_missing_directory_returns_none(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent"
        assert find_latest_metrics(missing) is None

    def test_empty_directory_returns_none(self, tmp_path: Path) -> None:
        assert find_latest_metrics(tmp_path) is None

    def test_single_file_returned(self, tmp_path: Path) -> None:
        f = tmp_path / "metrics_20260101_120000.json"
        f.write_text("{}")
        assert find_latest_metrics(tmp_path) == f

    def test_multiple_files_returns_latest_by_name(self, tmp_path: Path) -> None:
        older = tmp_path / "metrics_20260101_000000.json"
        newer = tmp_path / "metrics_20260102_000000.json"
        oldest = tmp_path / "metrics_20251231_235959.json"
        for f in (older, newer, oldest):
            f.write_text("{}")
        assert find_latest_metrics(tmp_path) == newer

    def test_non_matching_files_ignored(self, tmp_path: Path) -> None:
        (tmp_path / "other_file.json").write_text("{}")
        (tmp_path / "metrics_20260101_000000.json").write_text("{}")
        result = find_latest_metrics(tmp_path)
        assert result is not None
        assert result.name == "metrics_20260101_000000.json"


# ---------------------------------------------------------------------------
# format_duration
# ---------------------------------------------------------------------------

class TestFormatDuration:
    def test_zero_seconds(self) -> None:
        assert format_duration(0) == "0s"

    def test_sub_minute(self) -> None:
        assert format_duration(45) == "45s"

    def test_exactly_60_seconds(self) -> None:
        # 60s → 1m 0s
        assert format_duration(60) == "1m 0s"

    def test_minutes_and_seconds(self) -> None:
        assert format_duration(90) == "1m 30s"

    def test_exactly_one_hour(self) -> None:
        assert format_duration(3600) == "1h 0m"

    def test_hours_and_minutes(self) -> None:
        # 3661s → 1h 1m (seconds are dropped for durations >= 1h)
        assert format_duration(3661) == "1h 1m"

    def test_just_under_one_hour(self) -> None:
        assert format_duration(3599) == "59m 59s"


# ---------------------------------------------------------------------------
# print_summary
# ---------------------------------------------------------------------------

class TestPrintSummary:
    def _capture(self, data: dict) -> str:
        buf = io.StringIO()
        original_print = builtins.print

        def patched_print(*args, **kwargs):
            kwargs.setdefault("file", buf)
            original_print(*args, **kwargs)

        with mock.patch("builtins.print", side_effect=patched_print):
            print_summary(data)
        return buf.getvalue()

    def _minimal_data(self, **overrides) -> dict:
        base: dict = {
            "session": {"exported_at": "2026-01-01T12:00:00", "duration_seconds": 30},
            "shows": {"scraped": 10, "saved": 8},
            "clubs": {"processed": 5, "successful": 4, "failed": 1},
            "error_details": [],
            "success_rate": None,
        }
        base.update(overrides)
        return base

    def test_basic_output_contains_header(self) -> None:
        out = self._capture(self._minimal_data())
        assert "SCRAPER HEALTH SUMMARY" in out

    def test_success_rate_shown_when_present(self) -> None:
        data = self._minimal_data(success_rate=80.0)
        out = self._capture(data)
        assert "80.0%" in out

    def test_success_rate_omitted_when_none(self) -> None:
        out = self._capture(self._minimal_data(success_rate=None))
        assert "Show save rate" not in out

    def test_error_grouping_counts_correctly(self) -> None:
        errors = [
            {"error": "Timeout"},
            {"error": "Timeout"},
            {"error": "404 Not Found"},
        ]
        data = self._minimal_data(error_details=errors)
        out = self._capture(data)
        assert "[2x] Timeout" in out
        assert "[1x] 404 Not Found" in out

    def test_top_errors_section_shows_total(self) -> None:
        errors = [{"error": "err"} for _ in range(7)]
        data = self._minimal_data(error_details=errors)
        out = self._capture(data)
        assert "7 total failures" in out

    def test_no_errors_section_when_empty(self) -> None:
        out = self._capture(self._minimal_data(error_details=[]))
        assert "TOP ERRORS" not in out

    def test_long_error_message_truncated(self) -> None:
        long_msg = "x" * 200
        data = self._minimal_data(error_details=[{"error": long_msg}])
        out = self._capture(data)
        assert "..." in out
        # The truncated message should be at most 123 chars (120 + "...")
        lines = [l for l in out.splitlines() if "xxx" in l]
        assert lines, "Expected truncated error line in output"
        assert len(lines[0]) < 200

    def test_invalid_exported_at_falls_back_gracefully(self) -> None:
        data = self._minimal_data()
        data["session"]["exported_at"] = "not-a-date"
        out = self._capture(data)
        assert "not-a-date" in out

    def test_unknown_exported_at_when_missing(self) -> None:
        data = self._minimal_data()
        del data["session"]["exported_at"]
        out = self._capture(data)
        assert "unknown" in out

    def test_duration_unknown_when_missing(self) -> None:
        data = self._minimal_data()
        del data["session"]["duration_seconds"]
        out = self._capture(data)
        assert "unknown" in out
