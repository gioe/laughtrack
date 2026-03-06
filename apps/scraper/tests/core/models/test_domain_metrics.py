"""Unit tests for DomainRequestMetrics and ScrapingRunSummary."""

import pytest

from laughtrack.core.models.domain_metrics import DomainRequestMetrics, ScrapingRunSummary


class TestDomainRequestMetrics:
    def test_success_rate_all_ok(self):
        m = DomainRequestMetrics(club_name="A", total=3, ok=3)
        assert m.success_rate == 100.0

    def test_success_rate_partial(self):
        m = DomainRequestMetrics(club_name="A", total=4, ok=2)
        assert m.success_rate == 50.0

    def test_success_rate_all_error(self):
        m = DomainRequestMetrics(club_name="A", total=2, ok=0, error=2)
        assert m.success_rate == 0.0

    def test_success_rate_zero_total_returns_100(self):
        m = DomainRequestMetrics(club_name="A", total=0)
        assert m.success_rate == 100.0

    def test_as_log_dict_contains_expected_keys(self):
        m = DomainRequestMetrics(club_name="Foo", total=1, ok=1)
        d = m.as_log_dict()
        assert d["club"] == "Foo"
        assert d["total"] == 1
        assert d["ok"] == 1
        assert d["none_resp"] == 0
        assert d["error"] == 0
        assert "success_rate_pct" in d


class TestScrapingRunSummary:
    def _make_summary(self):
        s = ScrapingRunSummary()
        s.per_club.append(DomainRequestMetrics("ok_club", total=1, ok=1))
        s.per_club.append(DomainRequestMetrics("empty_club", total=1, none_resp=1))
        s.per_club.append(DomainRequestMetrics("error_club", total=1, error=1))
        return s

    def test_total_clubs(self):
        s = self._make_summary()
        assert s.total_clubs == 3

    def test_clubs_ok(self):
        s = self._make_summary()
        assert s.clubs_ok == 1

    def test_clubs_errored(self):
        s = self._make_summary()
        assert s.clubs_errored == 1

    def test_clubs_empty(self):
        s = self._make_summary()
        assert s.clubs_empty == 1

    def test_below_threshold_returns_failing_clubs(self):
        s = self._make_summary()
        failing = s.below_threshold(70.0)
        names = [m.club_name for m in failing]
        assert "empty_club" in names
        assert "error_club" in names
        assert "ok_club" not in names

    def test_below_threshold_all_pass(self):
        s = ScrapingRunSummary()
        s.per_club.append(DomainRequestMetrics("a", total=1, ok=1))
        s.per_club.append(DomainRequestMetrics("b", total=1, ok=1))
        assert s.below_threshold(70.0) == []

    def test_below_threshold_empty_summary(self):
        s = ScrapingRunSummary()
        assert s.below_threshold(70.0) == []
