"""
Unit tests for WestSideExtractor and WestSideShow.to_show().

West Side Comedy Club uses the Punchup platform (Next.js App Router + TanStack Query).
Show data is embedded in React Query hydration state inside self.__next_f.push()
streaming script tags, not as JSON-LD.
"""

import json

import pytest

from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.implementations.venues.west_side.extractor import (
    WestSideExtractor,
    WestSideShow,
)


def _club():
    return Club(
        id=8,
        name="West Side Comedy Club",
        address="",
        website="https://westsidecomedyclub.com",
        scraping_url="westsidecomedyclub.com/calendar",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )


# ---------------------------------------------------------------------------
# Helpers to build fixture HTML
# ---------------------------------------------------------------------------

_SHOW_ITEM = {
    "type": "show",
    "id": "item-uuid-1",
    "order": 1,
    "show": {
        "id": "show-uuid-1",
        "title": "Dan Levin and Friends",
        "datetime": "2026-03-19T21:00:00",
        "location": "New York, NY",
        "venue": "West Side Comedy Club",
        "ticket_link": "https://event.tixologi.com/event/9572/tickets",
        "tixologi_event_id": "9572",
        "is_sold_out": False,
        "metadata_text": "What happens when a comedian moves to the West Coast...",
        "show_comedians": [
            {"id": "c1", "display_name": "Dan Levin", "slug": "danlevin", "ordering": 0},
            {"id": "c2", "display_name": "Allan Fuks", "slug": "allanfuks", "ordering": 1},
        ],
    },
}

_SHOW_ITEM_SOLD_OUT = {
    "type": "show",
    "id": "item-uuid-2",
    "order": 2,
    "show": {
        "id": "show-uuid-2",
        "title": "Sold Out Show",
        "datetime": "2026-03-22T18:00:00",
        "ticket_link": "https://event.tixologi.com/event/9999/tickets",
        "tixologi_event_id": "9999",
        "is_sold_out": True,
        "metadata_text": None,
        "show_comedians": [],
    },
}


def _build_html_with_plain_json(items):
    """Build HTML where venuePageCarousel data appears as plain JSON in a script tag."""
    payload = {
        "queries": [
            {
                "queryKey": ["venuePageCarousel", "386befdb-9075-4a84-8adc-4e5e5c945fbc"],
                "state": {
                    "data": {
                        "mode": "custom",
                        "items": items,
                    },
                    "status": "success",
                },
            }
        ]
    }
    json_str = json.dumps(payload)
    return f"<html><body><script>{json_str}</script></body></html>"


def _build_html_with_next_f_push(items):
    """Build HTML where data is inside a self.__next_f.push([1, "..."]) call (escaped)."""
    inner = json.dumps(
        {
            "queries": [
                {
                    "queryKey": ["venuePageCarousel", "386befdb-9075-4a84-8adc-4e5e5c945fbc"],
                    "state": {
                        "data": {"mode": "custom", "items": items},
                        "status": "success",
                    },
                }
            ]
        }
    )
    # Escape as a JSON string value (double-encode quotes and backslashes)
    escaped = inner.replace("\\", "\\\\").replace('"', '\\"')
    push_call = f'self.__next_f.push([1,"{escaped}"])'
    return f"<html><body><script>{push_call}</script></body></html>"


# ---------------------------------------------------------------------------
# WestSideExtractor.extract_shows — plain JSON embedding
# ---------------------------------------------------------------------------


class TestExtractShowsPlainJson:
    def test_single_show_extracted(self):
        html = _build_html_with_plain_json([_SHOW_ITEM])
        shows = WestSideExtractor.extract_shows(html)
        assert len(shows) == 1
        assert shows[0].title == "Dan Levin and Friends"
        assert shows[0].datetime_str == "2026-03-19T21:00:00"
        assert shows[0].ticket_link == "https://event.tixologi.com/event/9572/tickets"
        assert shows[0].is_sold_out is False
        assert len(shows[0].show_comedians) == 2

    def test_multiple_shows_extracted(self):
        html = _build_html_with_plain_json([_SHOW_ITEM, _SHOW_ITEM_SOLD_OUT])
        shows = WestSideExtractor.extract_shows(html)
        assert len(shows) == 2
        assert shows[1].title == "Sold Out Show"
        assert shows[1].is_sold_out is True

    def test_empty_items_returns_empty(self):
        html = _build_html_with_plain_json([])
        shows = WestSideExtractor.extract_shows(html)
        assert shows == []

    def test_non_show_items_skipped(self):
        non_show = {"type": "link", "id": "link-1", "url": "https://example.com"}
        html = _build_html_with_plain_json([non_show, _SHOW_ITEM])
        shows = WestSideExtractor.extract_shows(html)
        assert len(shows) == 1
        assert shows[0].title == "Dan Levin and Friends"

    def test_no_carousel_key_returns_empty(self):
        html = "<html><body><script>{}</script></body></html>"
        shows = WestSideExtractor.extract_shows(html)
        assert shows == []

    def test_empty_html_returns_empty(self):
        assert WestSideExtractor.extract_shows("") == []

    def test_missing_title_skips_show(self):
        bad_item = {
            "type": "show",
            "show": {"title": "", "datetime": "2026-03-19T21:00:00", "ticket_link": ""},
        }
        html = _build_html_with_plain_json([bad_item])
        shows = WestSideExtractor.extract_shows(html)
        assert shows == []

    def test_missing_datetime_skips_show(self):
        bad_item = {
            "type": "show",
            "show": {"title": "Some Show", "datetime": "", "ticket_link": ""},
        }
        html = _build_html_with_plain_json([bad_item])
        shows = WestSideExtractor.extract_shows(html)
        assert shows == []


# ---------------------------------------------------------------------------
# WestSideExtractor.extract_shows — Next.js streaming format
# ---------------------------------------------------------------------------


class TestExtractShowsNextFPush:
    def test_show_extracted_from_push_call(self):
        html = _build_html_with_next_f_push([_SHOW_ITEM])
        shows = WestSideExtractor.extract_shows(html)
        assert len(shows) == 1
        assert shows[0].title == "Dan Levin and Friends"

    def test_multiple_shows_from_push(self):
        html = _build_html_with_next_f_push([_SHOW_ITEM, _SHOW_ITEM_SOLD_OUT])
        shows = WestSideExtractor.extract_shows(html)
        assert len(shows) == 2


# ---------------------------------------------------------------------------
# WestSideShow.to_show()
# ---------------------------------------------------------------------------


class TestWestSideShowToShow:
    def test_basic_conversion(self):
        show_obj = WestSideShow(
            id="show-uuid-1",
            title="Dan Levin and Friends",
            datetime_str="2026-03-19T21:00:00",
            ticket_link="https://event.tixologi.com/event/9572/tickets",
            tixologi_event_id="9572",
            is_sold_out=False,
            metadata_text="Some description",
            show_comedians=[
                {"id": "c1", "display_name": "Dan Levin", "ordering": 0},
            ],
        )
        club = _club()
        show = show_obj.to_show(club)

        assert show is not None
        assert show.name == "Dan Levin and Friends"
        assert show.club_id == 8
        assert show.show_page_url == "https://event.tixologi.com/event/9572/tickets"
        assert len(show.lineup) == 1
        assert show.lineup[0].name == "Dan Levin"
        assert len(show.tickets) == 1
        assert show.tickets[0].purchase_url == "https://event.tixologi.com/event/9572/tickets"
        assert show.tickets[0].sold_out is False

    def test_sold_out_ticket(self):
        show_obj = WestSideShow(
            id="show-uuid-2",
            title="Sold Out Show",
            datetime_str="2026-03-22T18:00:00",
            ticket_link="https://event.tixologi.com/event/9999/tickets",
            tixologi_event_id="9999",
            is_sold_out=True,
            metadata_text=None,
            show_comedians=[],
        )
        show = show_obj.to_show(_club())
        assert show is not None
        assert show.tickets[0].sold_out is True

    def test_lineup_sorted_by_ordering(self):
        show_obj = WestSideShow(
            id="show-uuid-3",
            title="Multi-Comic Show",
            datetime_str="2026-04-01T20:00:00",
            ticket_link="https://event.tixologi.com/event/1234/tickets",
            tixologi_event_id="1234",
            is_sold_out=False,
            metadata_text=None,
            show_comedians=[
                {"id": "c2", "display_name": "Second Comic", "ordering": 2},
                {"id": "c1", "display_name": "First Comic", "ordering": 0},
                {"id": "c3", "display_name": "Third Comic", "ordering": 5},
            ],
        )
        show = show_obj.to_show(_club())
        assert show is not None
        assert [c.name for c in show.lineup] == ["First Comic", "Second Comic", "Third Comic"]

    def test_no_ticket_link_gives_no_ticket(self):
        show_obj = WestSideShow(
            id="show-uuid-4",
            title="Free Show",
            datetime_str="2026-04-05T19:00:00",
            ticket_link="",
            tixologi_event_id=None,
            is_sold_out=False,
            metadata_text=None,
            show_comedians=[],
        )
        show = show_obj.to_show(_club())
        assert show is not None
        assert len(show.tickets) == 0

    def test_invalid_datetime_returns_none(self):
        show_obj = WestSideShow(
            id="show-uuid-5",
            title="Bad Date Show",
            datetime_str="not-a-date",
            ticket_link="https://event.tixologi.com/event/1/tickets",
            tixologi_event_id="1",
            is_sold_out=False,
            metadata_text=None,
            show_comedians=[],
        )
        show = show_obj.to_show(_club())
        assert show is None

    def test_date_converted_to_utc(self):
        """21:00 ET should be 02:00 UTC the next day."""
        import pytz

        show_obj = WestSideShow(
            id="show-uuid-6",
            title="UTC Test",
            datetime_str="2026-03-19T21:00:00",
            ticket_link="https://event.tixologi.com/event/1/tickets",
            tixologi_event_id="1",
            is_sold_out=False,
            metadata_text=None,
            show_comedians=[],
        )
        show = show_obj.to_show(_club())
        assert show is not None
        utc = pytz.utc
        show_utc = show.date.astimezone(utc)
        assert show_utc.hour == 1  # EDT offset is -4 in March (EST would be -5, but DST)
