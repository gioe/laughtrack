"""
Unit tests for NicksEventExtractor.extract_events() and NicksEvent.to_show().

Covers:
  - extract_events() with a minimal JSON fixture (happy path)
  - extract_events() edge cases: empty events list, missing keys, bad data
  - NicksEvent.to_show() UTC → America/New_York date/timezone parsing
  - parse_lineup_from_description() headliner and supporting act extraction
  - lineup propagation through extract_events() → to_show()
"""

import pytest

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.nicks import NicksEvent
from laughtrack.scrapers.implementations.venues.nicks_comedy_stop.extractor import (
    NicksEventExtractor,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _api_response(events: list) -> dict:
    """Build a minimal Wix paginated-events API response."""
    return {"events": events}


def _raw_event(
    id_="evt-001",
    title="Friday Night Comedy",
    description="A great show",
    slug="friday-night-comedy",
    start_date="2026-03-27T02:00:00.000Z",
    timezone="America/New_York",
    amount="25.00",
) -> dict:
    return {
        "id": id_,
        "title": title,
        "description": description,
        "slug": slug,
        "scheduling": {
            "config": {
                "startDate": start_date,
                "timeZoneId": timezone,
            }
        },
        "registration": {
            "ticketing": {
                "lowestTicketPrice": {
                    "amount": amount,
                }
            }
        },
    }


def _club() -> Club:
    return Club(
        id=143,
        name="Nick's Comedy Stop",
        address="100 Warrenton St, Boston, MA",
        website="https://www.nickscomedystop.com",
        scraping_url="https://www.nickscomedystop.com",
        popularity=0,
        zip_code="02116",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )


# ---------------------------------------------------------------------------
# extract_events — happy path
# ---------------------------------------------------------------------------


class TestExtractEvents:
    def test_single_event_extracted(self):
        response = _api_response([_raw_event()])
        events = NicksEventExtractor.extract_events(response)
        assert len(events) == 1
        e = events[0]
        assert e.title == "Friday Night Comedy"
        assert e.id == "evt-001"
        assert e.slug == "friday-night-comedy"

    def test_multiple_events_extracted(self):
        response = _api_response([
            _raw_event(id_="1", title="Friday Show"),
            _raw_event(id_="2", title="Saturday Show"),
        ])
        events = NicksEventExtractor.extract_events(response)
        assert len(events) == 2
        titles = {e.title for e in events}
        assert "Friday Show" in titles
        assert "Saturday Show" in titles

    def test_title_is_stripped(self):
        response = _api_response([_raw_event(title="  Spaced Title  ")])
        events = NicksEventExtractor.extract_events(response)
        assert events[0].title == "Spaced Title"

    def test_description_is_stripped(self):
        response = _api_response([_raw_event(description="  Some desc  ")])
        events = NicksEventExtractor.extract_events(response)
        assert events[0].description == "Some desc"

    def test_scheduling_preserved(self):
        response = _api_response([_raw_event(start_date="2026-04-01T01:00:00.000Z")])
        events = NicksEventExtractor.extract_events(response)
        config = events[0].scheduling.get("config", {})
        assert config.get("startDate") == "2026-04-01T01:00:00.000Z"

    def test_registration_preserved(self):
        response = _api_response([_raw_event(amount="30.00")])
        events = NicksEventExtractor.extract_events(response)
        ticketing = events[0].registration.get("ticketing", {})
        lowest = ticketing.get("lowestTicketPrice", {})
        assert lowest.get("amount") == "30.00"


# ---------------------------------------------------------------------------
# extract_events — edge / error cases
# ---------------------------------------------------------------------------


class TestExtractEventsEdgeCases:
    def test_empty_events_list_returns_empty(self):
        assert NicksEventExtractor.extract_events({"events": []}) == []

    def test_missing_events_key_returns_empty(self):
        assert NicksEventExtractor.extract_events({}) == []

    def test_missing_title_defaults_to_empty_string(self):
        raw = _raw_event()
        del raw["title"]
        response = _api_response([raw])
        events = NicksEventExtractor.extract_events(response)
        assert len(events) == 1
        assert events[0].title == ""

    def test_missing_scheduling_defaults_to_empty_dict(self):
        raw = _raw_event()
        del raw["scheduling"]
        response = _api_response([raw])
        events = NicksEventExtractor.extract_events(response)
        assert len(events) == 1
        assert events[0].scheduling == {}

    def test_bad_event_skipped_gracefully(self):
        """Non-dict items in the events list should be skipped without raising."""
        response = {"events": ["not-a-dict", None, _raw_event(id_="good")]}
        events = NicksEventExtractor.extract_events(response)
        # The bad items may raise AttributeError in _parse_event; only valid ones survive
        assert all(isinstance(e, NicksEvent) for e in events)


# ---------------------------------------------------------------------------
# NicksEvent.to_show() — UTC → America/New_York date parsing
# ---------------------------------------------------------------------------


class TestNicksEventToShow:
    def test_utc_date_converted_to_eastern(self):
        """UTC 2026-03-27T02:00:00Z → 2026-03-26 22:00 EDT (UTC-4)."""
        event = NicksEvent(
            id="evt-tz",
            title="Timezone Test Show",
            description="",
            slug="tz-test",
            scheduling={
                "config": {
                    "startDate": "2026-03-27T02:00:00.000Z",
                    "timeZoneId": "America/New_York",
                }
            },
            registration={},
        )
        show = event.to_show(_club())
        assert show is not None
        # UTC 02:00 = EDT 22:00 previous day (UTC-4 during DST)
        assert show.date.hour == 22
        assert show.date.day == 26

    def test_timezone_from_scheduling_config_used(self):
        """timeZoneId in scheduling.config overrides any default."""
        event = NicksEvent(
            id="evt-tz2",
            title="Show",
            description="",
            slug="show",
            scheduling={
                "config": {
                    "startDate": "2026-06-15T20:00:00.000Z",
                    "timeZoneId": "America/New_York",
                }
            },
            registration={},
        )
        show = event.to_show(_club())
        assert show is not None
        # UTC 20:00 = EDT 16:00 (UTC-4 during DST in June)
        assert show.date.hour == 16

    def test_missing_start_date_returns_none(self):
        event = NicksEvent(
            id="evt-nodate",
            title="No Date Show",
            description="",
            slug="no-date",
            scheduling={"config": {}},
            registration={},
        )
        show = event.to_show(_club())
        assert show is None

    def test_empty_scheduling_returns_none(self):
        event = NicksEvent(
            id="evt-empty",
            title="Empty Scheduling",
            description="",
            slug="empty",
            scheduling={},
            registration={},
        )
        show = event.to_show(_club())
        assert show is None

    def test_show_name_from_title(self):
        event = NicksEvent(
            id="evt-name",
            title="Weekend Special",
            description="",
            slug="weekend-special",
            scheduling={
                "config": {
                    "startDate": "2026-04-10T23:00:00.000Z",
                    "timeZoneId": "America/New_York",
                }
            },
            registration={},
        )
        show = event.to_show(_club())
        assert show is not None
        assert show.name == "Weekend Special"

    def test_show_page_url_uses_slug(self):
        event = NicksEvent(
            id="evt-slug",
            title="Slug Test",
            description="",
            slug="my-event-slug",
            scheduling={
                "config": {
                    "startDate": "2026-04-10T23:00:00.000Z",
                    "timeZoneId": "America/New_York",
                }
            },
            registration={},
        )
        show = event.to_show(_club())
        assert show is not None
        assert any("my-event-slug" in t.purchase_url for t in show.tickets)

    def test_ticket_price_from_registration(self):
        event = NicksEvent(
            id="evt-price",
            title="Priced Show",
            description="",
            slug="priced-show",
            scheduling={
                "config": {
                    "startDate": "2026-04-10T23:00:00.000Z",
                    "timeZoneId": "America/New_York",
                }
            },
            registration={
                "ticketing": {
                    "lowestTicketPrice": {"amount": "20.00"}
                }
            },
        )
        show = event.to_show(_club())
        assert show is not None
        assert len(show.tickets) > 0

    def test_sold_out_flag_propagated_when_ticketing_sold_out(self):
        """to_show() sets sold_out=True on tickets when Wix API reports soldOut=True."""
        event = NicksEvent(
            id="evt-soldout",
            title="Sold Out Show",
            description="",
            slug="sold-out-show",
            scheduling={
                "config": {
                    "startDate": "2026-04-10T23:00:00.000Z",
                    "timeZoneId": "America/New_York",
                }
            },
            registration={
                "ticketing": {
                    "soldOut": True,
                    "lowestTicketPrice": {"amount": "25.00"},
                }
            },
        )
        show = event.to_show(_club())
        assert show is not None
        assert len(show.tickets) == 1
        assert show.tickets[0].sold_out is True

    def test_sold_out_false_when_not_sold_out(self):
        """to_show() sets sold_out=False when soldOut is absent or False."""
        event = NicksEvent(
            id="evt-available",
            title="Available Show",
            description="",
            slug="available-show",
            scheduling={
                "config": {
                    "startDate": "2026-04-10T23:00:00.000Z",
                    "timeZoneId": "America/New_York",
                }
            },
            registration={
                "ticketing": {
                    "lowestTicketPrice": {"amount": "20.00"},
                }
            },
        )
        show = event.to_show(_club())
        assert show is not None
        assert show.tickets[0].sold_out is False


# ---------------------------------------------------------------------------
# parse_lineup_from_description
# ---------------------------------------------------------------------------


class TestParseLineupFromDescription:
    def test_headliner_extracted(self):
        desc = "headliner Jeremy Scippio headlines NICKS COMEDY STOP at 7:30pm"
        lineup = NicksEventExtractor.parse_lineup_from_description(desc)
        assert "Jeremy Scippio" in lineup

    def test_supporting_acts_extracted(self):
        desc = "headliner Jeremy Scippio headlines NICKS COMEDY STOP at 7:30pm with April O'Connor and Jay Delgadillo"
        lineup = NicksEventExtractor.parse_lineup_from_description(desc)
        assert "April O'Connor" in lineup
        assert "Jay Delgadillo" in lineup

    def test_full_description_all_three_performers(self):
        desc = "headliner Jeremy Scippio headlines NICKS COMEDY STOP at 7:30pm with April O'Connor and Jay Delgadillo"
        lineup = NicksEventExtractor.parse_lineup_from_description(desc)
        assert len(lineup) == 3
        assert lineup[0] == "Jeremy Scippio"

    def test_no_parseable_lineup_returns_empty(self):
        desc = "A great Friday night of comedy at Nick's!"
        lineup = NicksEventExtractor.parse_lineup_from_description(desc)
        assert lineup == []

    def test_empty_description_returns_empty(self):
        assert NicksEventExtractor.parse_lineup_from_description("") == []

    def test_case_insensitive_headliner(self):
        desc = "HEADLINER John Smith headlines the show"
        lineup = NicksEventExtractor.parse_lineup_from_description(desc)
        assert "John Smith" in lineup

    def test_headliner_only_no_supporting(self):
        desc = "headliner Jane Doe headlines NICKS COMEDY STOP"
        lineup = NicksEventExtractor.parse_lineup_from_description(desc)
        assert "Jane Doe" in lineup
        assert len(lineup) == 1


# ---------------------------------------------------------------------------
# lineup propagation via extract_events → to_show
# ---------------------------------------------------------------------------


class TestLineupPropagation:
    def test_lineup_in_extracted_event(self):
        desc = "headliner Jeremy Scippio headlines NICKS COMEDY STOP at 7:30pm with April O'Connor and Jay Delgadillo"
        response = _api_response([_raw_event(description=desc)])
        events = NicksEventExtractor.extract_events(response)
        assert events[0].lineup == ["Jeremy Scippio", "April O'Connor", "Jay Delgadillo"]

    def test_no_description_lineup_empty(self):
        response = _api_response([_raw_event(description="Just a show")])
        events = NicksEventExtractor.extract_events(response)
        assert events[0].lineup == []

    def test_to_show_passes_lineup(self):
        desc = "headliner Jeremy Scippio headlines NICKS COMEDY STOP at 7:30pm with April O'Connor and Jay Delgadillo"
        event = NicksEvent(
            id="evt-lineup",
            title="Friday Show",
            description=desc,
            slug="friday-show",
            scheduling={
                "config": {
                    "startDate": "2026-04-10T23:00:00.000Z",
                    "timeZoneId": "America/New_York",
                }
            },
            registration={},
            lineup=["Jeremy Scippio", "April O'Connor", "Jay Delgadillo"],
        )
        show = event.to_show(_club())
        assert show is not None
        lineup_names = [p.name for p in show.lineup]
        assert "Jeremy Scippio" in lineup_names
        assert "April O'Connor" in lineup_names
        assert "Jay Delgadillo" in lineup_names

    def test_to_show_empty_lineup_still_valid(self):
        event = NicksEvent(
            id="evt-nolineup",
            title="Friday Show",
            description="A great show",
            slug="friday-show",
            scheduling={
                "config": {
                    "startDate": "2026-04-10T23:00:00.000Z",
                    "timeZoneId": "America/New_York",
                }
            },
            registration={},
            lineup=[],
        )
        show = event.to_show(_club())
        assert show is not None
        assert show.lineup == []
