"""Unit tests for the dedicated Playhouse Square scraper (TASK-2942).

The fixture is a trimmed recording of the PHS load-more feed
(``/events/events_ajax/0``), already JSON-decoded to its inner HTML. It holds
five real ``m-eventItem`` cards spanning the relevant cases:
  - Marc Maron       — single date, Mimi Ohio Theatre, comedy
  - Jo Koy           — single date, KeyBank State Theatre, comedy
  - Nikki Glaser     — date RANGE (Aug 29-30), Connor Palace, comedy
  - The Lion King    — non-comedy (no comedian name match)
  - The Nutcracker   — Connor Palace; a junk "comedian" row exists with this
                       name, so it is the popularity-floor false-positive case
"""

import os

import pytz

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.playhouse_square import PlayhouseSquareEvent
from laughtrack.scrapers.implementations.api.playhouse_square.comedy_filter import (
    select_comedy_titles,
)
from laughtrack.scrapers.implementations.api.playhouse_square.extractor import extract_events
from laughtrack.scrapers.implementations.api.playhouse_square.scraper import (
    PlayhouseSquareScraper,
)

_FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "phs_events_ajax.html")
_BASE = "https://www.playhousesquare.org"


def _load_fixture() -> str:
    with open(_FIXTURE, encoding="utf-8") as fh:
        return fh.read()


class _Club:
    id = 1
    name = "Mimi Ohio Theatre"
    timezone = "America/New_York"

    def metadata_value(self, key):
        return None


# --------------------------------------------------------------------------- #
# Extraction
# --------------------------------------------------------------------------- #
class TestExtractEventsFromFixture:
    def test_parses_all_cards(self):
        events = extract_events(_load_fixture(), _BASE)
        assert len(events) == 5

    def test_required_fields_and_absolute_urls(self):
        for ev in extract_events(_load_fixture(), _BASE):
            assert ev.title
            assert ev.date_str
            assert ev.show_page_url.startswith("https://www.playhousesquare.org/events/detail/")

    def test_single_date_event(self):
        ev = next(e for e in extract_events(_load_fixture(), _BASE) if e.title == "Marc Maron")
        assert ev.date_str == "Oct 10, 2026"
        assert ev.venue_title == "Mimi Ohio Theatre"
        assert ev.ticket_url and "tickets.playhousesquare.org" in ev.ticket_url

    def test_range_date_takes_start(self):
        ev = next(e for e in extract_events(_load_fixture(), _BASE) if e.title == "Nikki Glaser")
        # Range "Aug 29 - 30, 2026" -> start date with the year from the range end.
        assert ev.date_str == "Aug 29, 2026"
        assert ev.venue_title == "Connor Palace"

    def test_venue_titles_captured(self):
        by_title = {e.title: e.venue_title for e in extract_events(_load_fixture(), _BASE)}
        assert by_title["Jo Koy"] == "KeyBank State Theatre"
        assert by_title["The Lion King"] == "KeyBank State Theatre"

    def test_empty_html(self):
        assert extract_events("", _BASE) == []

    def test_canceled_event_is_dropped(self):
        html = (
            '<div class="m-eventItem on_stage"><div class="m-eventItem__date">'
            '<span class="m-date__singleDate"><span class="m-date__month">Oct </span>'
            '<span class="m-date__day">10</span><span class="m-date__year">, 2026</span></span>'
            '<span class="venue_title">Mimi Ohio Theatre</span></div>'
            '<h3 class="m-eventItem__title"><a href="/events/detail/canceled-act">'
            "(Canceled) Some Comedian</a></h3></div>"
        )
        assert extract_events(html, _BASE) == []


# --------------------------------------------------------------------------- #
# to_show
# --------------------------------------------------------------------------- #
class TestToShow:
    def test_builds_future_show_with_default_time(self):
        ev = PlayhouseSquareEvent(
            title="Marc Maron",
            date_str="Oct 10, 2099",
            show_page_url="https://www.playhousesquare.org/events/detail/marc-maron-2",
            venue_title="Mimi Ohio Theatre",
            ticket_url="https://tickets.playhousesquare.org/online/default.asp?article_id=ABC",
        )
        show = ev.to_show(_Club())
        assert show is not None
        assert show.name == "Marc Maron"
        local = show.date.astimezone(pytz.timezone("America/New_York"))
        assert (local.year, local.hour, local.minute) == (2099, 19, 0)
        assert show.tickets[0].purchase_url.startswith("https://tickets.playhousesquare.org/")

    def test_full_month_name_parses(self):
        ev = PlayhouseSquareEvent(
            title="June Show",
            date_str="June 17, 2099",
            show_page_url="https://www.playhousesquare.org/events/detail/x",
        )
        assert ev.to_show(_Club()) is not None

    def test_default_show_time_override(self):
        class _ClubAt8(_Club):
            def metadata_value(self, key):
                return "20:30" if key == "default_show_time" else None

        ev = PlayhouseSquareEvent(
            title="Late Show",
            date_str="Oct 10, 2099",
            show_page_url="https://www.playhousesquare.org/events/detail/y",
        )
        local = ev.to_show(_ClubAt8()).date.astimezone(pytz.timezone("America/New_York"))
        assert (local.hour, local.minute) == (20, 30)

    def test_ticket_falls_back_to_page_url(self):
        ev = PlayhouseSquareEvent(
            title="No Ticket",
            date_str="Oct 10, 2099",
            show_page_url="https://www.playhousesquare.org/events/detail/z",
            ticket_url=None,
        )
        assert ev.to_show(_Club()).tickets[0].purchase_url.endswith("/events/detail/z")

    def test_past_show_returns_none(self):
        ev = PlayhouseSquareEvent(
            title="Old",
            date_str="Jan 06, 2020",
            show_page_url="https://www.playhousesquare.org/events/detail/old",
        )
        assert ev.to_show(_Club()) is None

    def test_unparseable_date_returns_none(self):
        ev = PlayhouseSquareEvent(
            title="Bad",
            date_str="sometime soon",
            show_page_url="https://www.playhousesquare.org/events/detail/bad",
        )
        assert ev.to_show(_Club()) is None


# --------------------------------------------------------------------------- #
# Comedy filter (DB handlers mocked)
# --------------------------------------------------------------------------- #
class _Comedian:
    def __init__(self, name):
        self.name = name


class _FakeLineupHandler:
    """Returns credible name matches keyed by show title."""

    def __init__(self, matches):
        self._matches = matches

    def get_comedians_from_show_names(self, show_names):
        wanted = {t[0] for t in show_names}
        return {
            title: [_Comedian(n) for n in names]
            for title, names in self._matches.items()
            if title in wanted
        }


class _FakeComedianHandler:
    def __init__(self, popularity):
        self._popularity = popularity

    def get_stored_popularity_by_names(self, names):
        return {n: self._popularity[n] for n in names if n in self._popularity}


class TestSelectComedyTitles:
    def test_keeps_popular_matches_drops_low_pop_and_unmatched(self):
        titles = ["Marc Maron", "The Nutcracker", "The Lion King"]
        lineup = _FakeLineupHandler(
            {
                "Marc Maron": ["Marc Maron"],
                "The Nutcracker": ["The Nutcracker"],  # junk comedian row
                # "The Lion King" has no comedian match at all
            }
        )
        comedian = _FakeComedianHandler({"Marc Maron": 0.55, "The Nutcracker": 0.18})
        result = select_comedy_titles(
            titles, lineup_handler=lineup, comedian_handler=comedian, min_popularity=0.30
        )
        assert result == {"Marc Maron"}

    def test_keeps_when_any_match_clears_floor(self):
        # "KILLERS OF KILL TONY" matches both a low-pop dup and the real act.
        lineup = _FakeLineupHandler(
            {"KILLERS OF KILL TONY": ["Killers of Kill Tony", "Kill Tony"]}
        )
        comedian = _FakeComedianHandler({"Killers of Kill Tony": 0.15, "Kill Tony": 0.52})
        result = select_comedy_titles(
            ["KILLERS OF KILL TONY"],
            lineup_handler=lineup,
            comedian_handler=comedian,
            min_popularity=0.30,
        )
        assert result == {"KILLERS OF KILL TONY"}

    def test_no_matches_returns_empty(self):
        lineup = _FakeLineupHandler({})
        comedian = _FakeComedianHandler({})
        assert (
            select_comedy_titles(
                ["Concert A"], lineup_handler=lineup, comedian_handler=comedian
            )
            == set()
        )


# --------------------------------------------------------------------------- #
# Scraper config / target building
# --------------------------------------------------------------------------- #
def _make_scraper(metadata=None, source_url="https://www.playhousesquare.org/events"):
    src = ScrapingSource(
        platform="custom", scraper_key="playhouse_square", source_url=source_url,
        priority=0, enabled=True, id=1, club_id=5058, metadata=metadata or {},
    )
    club = Club(
        id=5058, name="Connor Palace at Playhouse Square", address="",
        website="https://www.playhousesquare.org", popularity=0, zip_code="44115",
        phone_number="", visible=True, timezone="America/New_York", city="Cleveland",
        state="OH", scraping_sources=[src], active_scraping_source=src,
    )
    return PlayhouseSquareScraper(club)


class TestCollectScrapingTargets:
    async def test_builds_feed_url_with_default_per_page(self):
        scraper = _make_scraper(metadata={"venue_titles": ["Connor Palace"]})
        targets = await scraper.collect_scraping_targets()
        assert targets == [
            "https://www.playhousesquare.org/events/events_ajax/0?category=0&venue=0&team=0"
            "&per_page=500&came_from_page=event-list-page"
        ]

    async def test_per_page_override(self):
        scraper = _make_scraper(metadata={"venue_titles": ["Connor Palace"], "per_page": 50})
        assert "per_page=50" in (await scraper.collect_scraping_targets())[0]

    async def test_origin_derived_from_scraping_url(self):
        scraper = _make_scraper(
            metadata={"venue_titles": ["Connor Palace"]},
            source_url="https://www.playhousesquare.org/events?foo=bar",
        )
        assert (await scraper.collect_scraping_targets())[0].startswith(
            "https://www.playhousesquare.org/events/events_ajax/0?"
        )
