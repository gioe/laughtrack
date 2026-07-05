"""Unit tests for the generic Tessitura WordPress extractor (TASK-2924).

Fixtures mirror the verified live shape of capa.com's WP REST integration:
- ``/wp-json/wp/v2/genre`` returns taxonomy terms incl. a "Comedy" term.
- ``/wp-json/wp/v2/tessi_production?genre={id}`` returns productions whose
  ``content.rendered`` embeds "Saturday, December 5, 2099 | 7 PM", a
  "VENUE ... Plan Your Visit" block, and a ``tickets.{org}.com`` purchase URL.
"""

from datetime import datetime, timezone

import pytz

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.tessitura import TessituraEvent
from laughtrack.scrapers.implementations.api.tessitura.extractor import (
    discover_comedy_genre_ids,
    extract_event,
    extract_events,
)
from laughtrack.scrapers.implementations.api.tessitura.scraper import TessituraScraper

GENRE_TERMS = [
    {"id": 61, "name": "Broadway", "count": 31},
    {"id": 71, "name": "Comedy", "count": 73},
    {"id": 66, "name": "Music", "count": 284},
    {"id": 63, "name": "Virtual", "count": 0},
]

# A production with the bare-hour time form ("7 PM").
CONTENT_BARE_HOUR = """
<div>
  <h2>WHITNEY CUMMINGS: BIG BABY TOUR</h2>
  <div>Saturday, December 5, 2099  |  7 PM</div>
  <a href="https://tickets.capa.com/11600/11601/">On Sale Soon</a>
  <div>VENUE</div>
  <div><a href="https://www.capa.com/riffe-center-theatre-complex/">Davidson Theatre, Riffe Center</a></div>
  <a href="#">Plan Your Visit</a>
  <div>Description</div>
  <p>Whitney Cummings is touring North America.</p>
</div>
"""

# A production with the minute-bearing time form ("7:30 PM").
CONTENT_MINUTES = """
<div>
  <div>Wednesday, November 25, 2099 | 7:30 PM</div>
  <a href="https://tickets.capa.com/11574/11575/">Buy Tickets</a>
  <div>VENUE</div>
  <div>Palace Theatre</div>
  <a href="#">Plan Your Visit</a>
</div>
"""

WHITNEY = {
    "title": {"rendered": "WHITNEY CUMMINGS: BIG BABY TOUR"},
    "link": "https://www.capa.com/productions/whitney-cummings-big-baby/",
    "content": {"rendered": CONTENT_BARE_HOUR},
}
DRAG = {
    "title": {"rendered": "A Drag Queen Christmas"},
    "link": "https://www.capa.com/productions/a-drag-queen-christmas/",
    "content": {"rendered": CONTENT_MINUTES},
}
# No parseable showtime -> dropped.
NO_DATE = {
    "title": {"rendered": "On Sale Soon Mystery"},
    "link": "https://www.capa.com/productions/mystery/",
    "content": {"rendered": "<div>VENUE</div><div>Lincoln Theatre</div>"},
}


class _Club:
    id = 1
    name = "CAPA"
    timezone = "America/New_York"


def _scraper_club(source_url: str) -> Club:
    source = ScrapingSource(
        id=1,
        club_id=8731,
        platform="custom",
        scraper_key="tessitura",
        source_url=source_url,
    )
    return Club(
        id=8731,
        name="CAPA (Columbus)",
        address="55 East State Street",
        website="https://www.capa.com",
        popularity=0,
        zip_code="43215",
        phone_number="",
        visible=True,
        timezone="America/New_York",
        scraping_sources=[source],
        active_scraping_source=source,
    )


class TestDiscoverComedyGenreIds:
    def test_finds_comedy_term(self):
        assert discover_comedy_genre_ids(GENRE_TERMS) == [71]

    def test_substring_match(self):
        terms = [{"id": 9, "name": "Stand-Up Comedy", "count": 5}]
        assert discover_comedy_genre_ids(terms) == [9]

    def test_skips_zero_count_terms(self):
        terms = [{"id": 5, "name": "Comedy", "count": 0}]
        assert discover_comedy_genre_ids(terms) == []

    def test_no_match_returns_empty(self):
        assert discover_comedy_genre_ids(GENRE_TERMS, target_names=("opera",)) == []


class TestExtractEvent:
    def test_parses_bare_hour_production(self):
        ev = extract_event(WHITNEY)
        assert ev is not None
        assert ev.title == "WHITNEY CUMMINGS: BIG BABY TOUR"
        assert ev.start_date_str == "Saturday, December 5, 2099 | 7 PM"
        assert ev.show_page_url == "https://www.capa.com/productions/whitney-cummings-big-baby/"
        assert ev.ticket_url == "https://tickets.capa.com/11600/11601/"
        assert ev.venue_name == "Davidson Theatre, Riffe Center"

    def test_parses_minute_bearing_production(self):
        ev = extract_event(DRAG)
        assert ev is not None
        assert ev.start_date_str == "Wednesday, November 25, 2099 | 7:30 PM"
        assert ev.venue_name == "Palace Theatre"

    def test_drops_production_without_showtime(self):
        assert extract_event(NO_DATE) is None


class TestExtractEvents:
    def test_keeps_parseable_drops_rest(self):
        events = extract_events([WHITNEY, NO_DATE, DRAG])
        assert [e.title for e in events] == [
            "WHITNEY CUMMINGS: BIG BABY TOUR",
            "A Drag Queen Christmas",
        ]

    def test_empty_input(self):
        assert extract_events([]) == []


class TestToShow:
    def test_builds_future_show_with_room_and_ticket(self):
        ev = extract_event(WHITNEY)
        show = ev.to_show(_Club())
        assert show is not None
        assert show.name == "WHITNEY CUMMINGS: BIG BABY TOUR"
        assert show.room == "Davidson Theatre, Riffe Center"
        assert show.date.tzinfo is not None
        # 7 PM America/New_York on 2099-12-05
        assert show.date.astimezone(pytz.timezone("America/New_York")).hour == 19
        assert show.tickets
        assert show.tickets[0].purchase_url == "https://tickets.capa.com/11600/11601/"

    def test_minute_bearing_time_parsed(self):
        ev = extract_event(DRAG)
        show = ev.to_show(_Club())
        assert show is not None
        local = show.date.astimezone(pytz.timezone("America/New_York"))
        assert (local.hour, local.minute) == (19, 30)

    def test_past_show_returns_none(self):
        ev = TessituraEvent(
            title="Old Show",
            start_date_str="Saturday, January 6, 2020 | 7 PM",
            show_page_url="https://www.capa.com/productions/old/",
        )
        assert ev.to_show(_Club()) is None

    def test_falls_back_to_page_url_when_no_ticket(self):
        # Far-future sentinel (2099-03-13 is a Friday) so to_show's past-drop
        # never rots the test; no DST offset assertions here, so the post-2037
        # pytz-table caveat doesn't apply (TASK-3586).
        ev = TessituraEvent(
            title="Future Show",
            start_date_str="Friday, March 13, 2099 | 8 PM",
            show_page_url="https://www.capa.com/productions/future/",
            ticket_url=None,
        )
        show = ev.to_show(_Club())
        assert show is not None
        assert show.tickets[0].purchase_url == "https://www.capa.com/productions/future/"
        assert show.date > datetime.now(timezone.utc)


class TestTessituraScraperTargets:
    def test_calendar_source_url_derives_wp_rest_origin(self):
        calendar_url = (
            "https://www.capa.com/event-calendar/?term_genre%5B%5D=comedy"
            "&start_date=2026-07-01&end_date="
        )
        scraper = TessituraScraper(_scraper_club(calendar_url))

        assert scraper._wp_rest_base() == "https://www.capa.com/wp-json/wp/v2"
