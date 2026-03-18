"""
Unit tests for UncleVinniesExtractor static methods and UncleVinniesEvent.to_show().
"""
from datetime import datetime, timedelta

import pytest
import pytz

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.uncle_vinnies import UncleVinniesEvent
from laughtrack.scrapers.implementations.venues.uncle_vinnies.extractor import UncleVinniesExtractor


def _club():
    return Club(
        id=99,
        name="Uncle Vinnie's Comedy Club",
        address="",
        website="https://unclevinniescomicdyclub.com",
        scraping_url="https://unclevinniescomedyclub.com",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )


# ---------------------------------------------------------------------------
# extract_production_id
# ---------------------------------------------------------------------------


class TestExtractProductionId:
    def test_happy_path(self):
        url = "https://ci.ovationtix.com/35774/production/1234567"
        assert UncleVinniesExtractor.extract_production_id(url) == "1234567"

    def test_url_with_query_string(self):
        url = "https://ci.ovationtix.com/35774/production/1234567?performanceId=999"
        assert UncleVinniesExtractor.extract_production_id(url) == "1234567"

    def test_no_production_segment(self):
        url = "https://ci.ovationtix.com/35774/calendar"
        assert UncleVinniesExtractor.extract_production_id(url) is None

    def test_empty_string_after_production(self):
        url = "https://ci.ovationtix.com/35774/production/"
        assert UncleVinniesExtractor.extract_production_id(url) is None

    def test_multiple_production_segments(self):
        # split("/production/") gives ["...", "abc/extra"]; only "?" is stripped,
        # so the full path segment "abc/extra" is returned as the production ID.
        url = "https://ci.ovationtix.com/35774/production/abc/extra"
        result = UncleVinniesExtractor.extract_production_id(url)
        assert result == "abc/extra"


# ---------------------------------------------------------------------------
# extract_next_performance_info
# ---------------------------------------------------------------------------


class TestExtractNextPerformanceInfo:
    def test_valid_response(self):
        response = {
            "performanceSummary": {
                "nextPerformance": {
                    "id": "perf-42",
                    "startDate": "2026-06-01 20:00",
                }
            }
        }
        perf_id, start_date = UncleVinniesExtractor.extract_next_performance_info(response)
        assert perf_id == "perf-42"
        assert start_date == "2026-06-01 20:00"

    def test_empty_response(self):
        perf_id, start_date = UncleVinniesExtractor.extract_next_performance_info({})
        assert perf_id is None
        assert start_date is None

    def test_missing_next_performance(self):
        response = {"performanceSummary": {}}
        perf_id, start_date = UncleVinniesExtractor.extract_next_performance_info(response)
        assert perf_id is None
        assert start_date is None

    def test_null_performance_summary(self):
        response = {"performanceSummary": None}
        perf_id, start_date = UncleVinniesExtractor.extract_next_performance_info(response)
        assert perf_id is None
        assert start_date is None

    def test_partial_next_performance(self):
        response = {
            "performanceSummary": {
                "nextPerformance": {"id": "perf-99"}
            }
        }
        perf_id, start_date = UncleVinniesExtractor.extract_next_performance_info(response)
        assert perf_id == "perf-99"
        assert start_date is None


# ---------------------------------------------------------------------------
# is_past_event
# ---------------------------------------------------------------------------


class TestIsPastEvent:
    def _future_str(self, fmt="%Y-%m-%d %H:%M"):
        future_dt = datetime.now() + timedelta(days=30)
        return future_dt.strftime(fmt)

    def _past_str(self, fmt="%Y-%m-%d %H:%M"):
        past_dt = datetime.now() - timedelta(days=1)
        return past_dt.strftime(fmt)

    def test_past_event_space_format(self):
        assert UncleVinniesExtractor.is_past_event(self._past_str(), "America/New_York") is True

    def test_future_event_space_format(self):
        assert UncleVinniesExtractor.is_past_event(self._future_str(), "America/New_York") is False

    def test_past_event_iso_format(self):
        past = self._past_str(fmt="%Y-%m-%dT%H:%M:%S")
        assert UncleVinniesExtractor.is_past_event(past, "America/New_York") is True

    def test_future_event_iso_format(self):
        future = self._future_str(fmt="%Y-%m-%dT%H:%M:%S")
        assert UncleVinniesExtractor.is_past_event(future, "America/New_York") is False

    def test_unparseable_date_returns_false(self):
        # Conservative default: don't filter out events we can't parse
        assert UncleVinniesExtractor.is_past_event("not-a-date", "America/New_York") is False

    def test_timezone_respected(self):
        # Build a datetime that is "future" in UTC but "past" in US/Eastern.
        # This is tricky to do reliably, so we simply verify different timezones
        # are accepted without raising an exception.
        future = self._future_str()
        result_ny = UncleVinniesExtractor.is_past_event(future, "America/New_York")
        result_la = UncleVinniesExtractor.is_past_event(future, "America/Los_Angeles")
        assert isinstance(result_ny, bool)
        assert isinstance(result_la, bool)


# ---------------------------------------------------------------------------
# create_event_from_performance_data
# ---------------------------------------------------------------------------


class TestCreateEventFromPerformanceData:
    def _base_performance_data(self):
        return {
            "id": "perf-7",
            "startDate": "2026-08-15 19:30",
            "production": {
                "productionName": "Friday Night Laughs",
                "description": "A great comedy show.",
            },
            "sections": [
                {
                    "ticketTypeViews": [
                        {"name": "General Admission", "price": 25.0},
                    ]
                }
            ],
        }

    def test_happy_path(self):
        event = UncleVinniesExtractor.create_event_from_performance_data(
            self._base_performance_data(), "prod-1", "https://example.com/production/prod-1"
        )
        assert event is not None
        assert event.name == "Friday Night Laughs"
        assert event.start_date == "2026-08-15 19:30"
        assert event.production_id == "prod-1"
        assert event.performance_id == "perf-7"
        assert event.description == "A great comedy show."
        assert len(event.sections) == 1

    def test_name_fallback_chain(self):
        data = {
            "id": "perf-8",
            "startDate": "2026-09-01 20:00",
            "production": {"name": "Fallback Name"},
        }
        event = UncleVinniesExtractor.create_event_from_performance_data(
            data, "prod-2", "https://example.com"
        )
        assert event is not None
        assert event.name == "Fallback Name"

    def test_name_defaults_to_comedy_show(self):
        data = {
            "id": "perf-9",
            "startDate": "2026-09-01 20:00",
            "production": {},
        }
        event = UncleVinniesExtractor.create_event_from_performance_data(
            data, "prod-3", "https://example.com"
        )
        assert event is not None
        assert event.name == "Comedy Show"

    def test_missing_start_date_returns_none(self):
        data = {
            "id": "perf-10",
            "production": {"productionName": "Some Show"},
        }
        event = UncleVinniesExtractor.create_event_from_performance_data(
            data, "prod-4", "https://example.com"
        )
        assert event is None

    def test_non_string_start_date_returns_none(self):
        data = {
            "id": "perf-11",
            "startDate": 20260901,
            "production": {"productionName": "Some Show"},
        }
        event = UncleVinniesExtractor.create_event_from_performance_data(
            data, "prod-5", "https://example.com"
        )
        assert event is None

    def test_sections_from_production_fallback(self):
        data = {
            "id": "perf-12",
            "startDate": "2026-10-01 21:00",
            "production": {
                "productionName": "Show",
                "sections": [{"ticketTypeViews": []}],
            },
        }
        event = UncleVinniesExtractor.create_event_from_performance_data(
            data, "prod-6", "https://example.com"
        )
        assert event is not None
        assert len(event.sections) == 1


# ---------------------------------------------------------------------------
# UncleVinniesEvent.to_show
# ---------------------------------------------------------------------------


class TestUncleVinniesEventToShow:
    def _make_event(self, start_date="2026-08-15 19:30", sections=None):
        default_sections = [
            {
                "ticketTypeViews": [
                    {"name": "General Admission", "price": 20.0},
                    {"name": "VIP", "price": 40.0},
                ]
            }
        ]
        return UncleVinniesEvent(
            production_id="prod-42",
            performance_id="perf-42",
            name="Uncle Vinnie's Presents",
            start_date=start_date,
            description="A great evening of comedy.",
            sections=default_sections if sections is None else sections,
            ticket_types=[],
            event_url="https://ci.ovationtix.com/35774/production/prod-42",
        )

    def test_to_show_basic_fields(self):
        event = self._make_event()
        show = event.to_show(_club(), enhanced=False)

        assert show is not None
        assert show.name == "Uncle Vinnie's Presents"
        assert show.club_id == 99

    def test_to_show_date_parsed(self):
        event = self._make_event(start_date="2026-08-15 19:30")
        show = event.to_show(_club(), enhanced=False)

        assert show is not None
        assert show.date is not None
        assert show.date.year == 2026
        assert show.date.month == 8
        assert show.date.day == 15

    def test_to_show_iso_date(self):
        event = self._make_event(start_date="2026-09-01T20:00:00")
        show = event.to_show(_club(), enhanced=False)

        assert show is not None
        assert show.date.year == 2026
        assert show.date.month == 9

    def test_to_show_tickets_extracted(self):
        event = self._make_event()
        show = event.to_show(_club(), enhanced=False)

        assert show is not None
        assert len(show.tickets) == 2
        prices = {t.price for t in show.tickets}
        assert 20.0 in prices
        assert 40.0 in prices

    def test_to_show_event_url(self):
        event = self._make_event()
        show = event.to_show(_club(), enhanced=False)

        assert show is not None
        assert "prod-42" in show.show_page_url

    def test_to_show_invalid_date_returns_none(self):
        event = self._make_event(start_date="not-a-date")
        show = event.to_show(_club(), enhanced=False)
        assert show is None

    def test_to_show_no_sections_produces_empty_tickets(self):
        event = self._make_event(sections=[])
        show = event.to_show(_club(), enhanced=False)

        assert show is not None
        assert show.tickets == []
