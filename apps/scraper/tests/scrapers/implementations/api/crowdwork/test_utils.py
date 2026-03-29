"""
Unit tests for the shared Crowdwork extract_performances utility.
"""

import pytest

from laughtrack.scrapers.implementations.api.crowdwork.utils import (
    RAILS_TO_IANA,
    extract_performances,
)


def _show(**overrides) -> dict:
    base = {
        "name": "Test Show",
        "url": "https://www.crowdwork.com/e/test-show",
        "timezone": "America/Chicago",
        "dates": ["2026-04-01T19:00:00.000-05:00"],
        "next_date": None,
        "cost": {"formatted": "$10.00"},
        "description": {"body": "<p>A show.</p>"},
        "badges": {"spots": None},
    }
    base.update(overrides)
    return base


class TestExtractPerformancesBasic:
    def test_returns_one_performance_per_date(self):
        show = _show(dates=["2026-04-01T19:00:00.000-05:00", "2026-04-02T19:00:00.000-05:00"])
        result = extract_performances(show)
        assert len(result) == 2

    def test_name_and_url_extracted(self):
        show = _show(name="Funny Night", url="https://crowdwork.com/e/funny-night")
        result = extract_performances(show)
        assert result[0].name == "Funny Night"
        assert result[0].url == "https://crowdwork.com/e/funny-night"

    def test_cost_extracted(self):
        show = _show(cost={"formatted": "$15.00 (includes fees)"})
        result = extract_performances(show)
        assert result[0].cost_formatted == "$15.00 (includes fees)"

    def test_description_extracted(self):
        show = _show(description={"body": "<p>Great show.</p>"})
        result = extract_performances(show)
        assert result[0].description == "<p>Great show.</p>"

    def test_empty_dates_returns_empty_list(self):
        show = _show(dates=[], next_date=None)
        result = extract_performances(show)
        assert result == []

    def test_skips_empty_date_strings(self):
        show = _show(dates=["", "2026-04-01T19:00:00.000-05:00"])
        result = extract_performances(show)
        assert len(result) == 1


class TestNextDateFallback:
    def test_uses_next_date_when_dates_empty(self):
        show = _show(dates=[], next_date="2026-05-01T20:00:00.000-05:00")
        result = extract_performances(show)
        assert len(result) == 1
        assert result[0].date_str == "2026-05-01T20:00:00.000-05:00"

    def test_dates_takes_precedence_over_next_date(self):
        show = _show(
            dates=["2026-04-01T19:00:00.000-05:00", "2026-04-02T19:00:00.000-05:00"],
            next_date="2026-05-01T20:00:00.000-05:00",
        )
        result = extract_performances(show)
        assert len(result) == 2


class TestDefaultTimezone:
    def test_uses_show_timezone_when_present(self):
        show = _show(timezone="America/New_York")
        result = extract_performances(show, default_timezone="America/Chicago")
        assert result[0].timezone == "America/New_York"

    def test_uses_default_timezone_when_missing(self):
        show = _show(timezone=None)
        result = extract_performances(show, default_timezone="America/Los_Angeles")
        assert result[0].timezone == "America/Los_Angeles"

    def test_default_timezone_is_chicago(self):
        show = _show(timezone=None)
        result = extract_performances(show)
        assert result[0].timezone == "America/Chicago"


class TestRailsToIana:
    def test_maps_central_time_when_rails_to_iana_provided(self):
        show = _show(timezone="Central Time (US & Canada)")
        result = extract_performances(show, rails_to_iana=RAILS_TO_IANA)
        assert result[0].timezone == "America/Chicago"

    def test_maps_eastern_time(self):
        show = _show(timezone="Eastern Time (US & Canada)")
        result = extract_performances(show, rails_to_iana=RAILS_TO_IANA)
        assert result[0].timezone == "America/New_York"

    def test_maps_pacific_time(self):
        show = _show(timezone="Pacific Time (US & Canada)")
        result = extract_performances(show, rails_to_iana=RAILS_TO_IANA)
        assert result[0].timezone == "America/Los_Angeles"

    def test_maps_mountain_time(self):
        show = _show(timezone="Mountain Time (US & Canada)")
        result = extract_performances(show, rails_to_iana=RAILS_TO_IANA)
        assert result[0].timezone == "America/Denver"

    def test_unknown_rails_name_passed_through(self):
        show = _show(timezone="Bogus Time (US & Canada)")
        result = extract_performances(show, rails_to_iana=RAILS_TO_IANA)
        assert result[0].timezone == "Bogus Time (US & Canada)"

    def test_none_rails_to_iana_passes_iana_through(self):
        show = _show(timezone="America/New_York")
        result = extract_performances(show, rails_to_iana=None)
        assert result[0].timezone == "America/New_York"

    def test_none_rails_to_iana_does_not_map_rails_names(self):
        show = _show(timezone="Central Time (US & Canada)")
        result = extract_performances(show, rails_to_iana=None)
        assert result[0].timezone == "Central Time (US & Canada)"


class TestSoldOut:
    def test_sold_out_when_spots_starts_with_sold_out(self):
        show = _show(badges={"spots": "Sold Out"})
        result = extract_performances(show)
        assert result[0].sold_out is True

    def test_sold_out_case_insensitive(self):
        show = _show(badges={"spots": "sold out"})
        result = extract_performances(show)
        assert result[0].sold_out is True

    def test_not_sold_out_when_spots_shows_remaining(self):
        show = _show(badges={"spots": "Only 2 spots left"})
        result = extract_performances(show)
        assert result[0].sold_out is False

    def test_not_sold_out_when_spots_contains_sold_but_not_starting(self):
        show = _show(badges={"spots": "3 tickets sold"})
        result = extract_performances(show)
        assert result[0].sold_out is False

    def test_not_sold_out_when_spots_none(self):
        show = _show(badges={"spots": None})
        result = extract_performances(show)
        assert result[0].sold_out is False

    def test_not_sold_out_when_badges_missing(self):
        show = _show(badges=None)
        result = extract_performances(show)
        assert result[0].sold_out is False


class TestMissingOrMalformedFields:
    def test_name_defaults_to_comedy_show(self):
        show = _show(name=None)
        result = extract_performances(show)
        assert result[0].name == "Comedy Show"

    def test_url_defaults_to_empty_string(self):
        show = _show(url=None)
        result = extract_performances(show)
        assert result[0].url == ""

    def test_cost_non_dict_treated_as_empty(self):
        show = _show(cost="free")
        result = extract_performances(show)
        assert result[0].cost_formatted == ""

    def test_description_non_dict_treated_as_empty(self):
        show = _show(description="some text")
        result = extract_performances(show)
        assert result[0].description == ""

    def test_badges_non_dict_treated_as_not_sold_out(self):
        show = _show(badges="Sold Out")
        result = extract_performances(show)
        assert result[0].sold_out is False
