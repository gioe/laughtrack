"""Unit + smoke tests for the AEG/Goldenvoice Carbonhouse venue-page scraper.

The fixture is a recorded thewarfieldtheatre.com ``/events`` page (trimmed to the
``div#eventsList`` subtree). Its shows are ``div.entry`` cards: a title in
``h3.carousel_item_title_small a``, a date in ``span.date`` ("Wed, Jun 24,
2026"), a real show time in ``span.time`` ("Show 8:00 PM"), the venue's own
``/events/detail/<id>`` URL, and an ``axs.com/...?skin=warfield`` ticket link.

The Warfield is concert-dominated (19 of 20 recorded shows are music); only "The
Kevin Langue Show: Live!" is comedy, so the scraper layers the shared comedy
filter (keyword + per-source allowlist + known comedian) to drop the concerts.
"""

import os

from unittest.mock import AsyncMock, MagicMock

import pytz

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.aeg_axs import AEGAXSEvent
from laughtrack.scrapers.implementations.api.aeg_axs.extractor import extract_events
from laughtrack.scrapers.implementations.api.aeg_axs.scraper import AEGAXSVenueScraper

_FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "warfield_events_page.html")

# The single comedy act on the recorded page. It carries no comedy keyword and
# the comedian's stored popularity sits below the floor, so only the per-source
# allowlist can keep it.
_COMEDY_TITLE = "The Kevin Langue Show: Live!"
_ALLOWLIST = ["kevin langue"]


def _load_fixture() -> str:
    with open(_FIXTURE, encoding="utf-8") as fh:
        return fh.read()


class _Club:
    id = 1
    name = "The Warfield"
    timezone = "America/Los_Angeles"

    def metadata_value(self, key):
        return None


class TestExtractEventsFromFixture:
    def test_parses_all_event_cards(self):
        events = extract_events(_load_fixture())
        assert len(events) == 20

    def test_each_event_has_required_fields(self):
        for ev in extract_events(_load_fixture()):
            assert ev.title
            assert ev.date_str  # "Wed, Jun 24, 2026"
            assert ev.show_page_url.startswith("http")

    def test_parses_date_and_time(self):
        ev = next(e for e in extract_events(_load_fixture()) if e.title == _COMEDY_TITLE)
        assert ev.date_str == "Wed, Jun 24, 2026"
        assert ev.time_str == "8:00 PM"

    def test_show_page_url_is_venue_detail_not_axs(self):
        ev = next(e for e in extract_events(_load_fixture()) if e.title == _COMEDY_TITLE)
        assert "thewarfieldtheatre.com/events/detail/" in ev.show_page_url
        assert "axs.com/events/" in (ev.ticket_url or "")

    def test_captures_comedy_among_concerts(self):
        titles = {e.title for e in extract_events(_load_fixture())}
        assert _COMEDY_TITLE in titles
        assert "Killswitch Engage" in titles  # concert present pre-filter

    def test_empty_html(self):
        assert extract_events("") == []


class TestToShow:
    def test_builds_future_show_with_parsed_time(self):
        ev = AEGAXSEvent(
            title=_COMEDY_TITLE,
            date_str="Wed, Jun 24, 2099",
            show_page_url="https://www.thewarfieldtheatre.com/events/detail/1346846",
            time_str="8:00 PM",
            ticket_url="https://www.axs.com/events/1346846/the-kevin-langue-show-live-tickets?skin=warfield",
        )
        show = ev.to_show(_Club())
        assert show is not None
        assert show.name == _COMEDY_TITLE
        local = show.date.astimezone(pytz.timezone("America/Los_Angeles"))
        assert (local.year, local.hour, local.minute) == (2099, 20, 0)  # 8:00 PM
        assert show.tickets[0].purchase_url.startswith("https://www.axs.com/")

    def test_falls_back_to_default_time_when_no_card_time(self):
        class _ClubAt7(_Club):
            def metadata_value(self, key):
                return "19:30" if key == "default_show_time" else None

        ev = AEGAXSEvent(
            title="No Time Card",
            date_str="Wed, Jun 24, 2099",
            show_page_url="https://www.thewarfieldtheatre.com/events/detail/1",
            time_str=None,
        )
        show = ev.to_show(_ClubAt7())
        local = show.date.astimezone(pytz.timezone("America/Los_Angeles"))
        assert (local.hour, local.minute) == (19, 30)

    def test_ticket_falls_back_to_page_url(self):
        ev = AEGAXSEvent(
            title="No Ticket Link",
            date_str="Wed, Jun 24, 2099",
            show_page_url="https://www.thewarfieldtheatre.com/events/detail/2",
            ticket_url=None,
        )
        show = ev.to_show(_Club())
        assert show.tickets[0].purchase_url == "https://www.thewarfieldtheatre.com/events/detail/2"

    def test_past_show_returns_none(self):
        ev = AEGAXSEvent(
            title="Old Show",
            date_str="Mon, Jan 06, 2020",
            show_page_url="https://www.thewarfieldtheatre.com/events/detail/3",
        )
        assert ev.to_show(_Club()) is None

    def test_unparseable_date_returns_none(self):
        ev = AEGAXSEvent(
            title="Bad Date",
            date_str="sometime next year",
            show_page_url="https://www.thewarfieldtheatre.com/events/detail/4",
        )
        assert ev.to_show(_Club()) is None


def _make_scraper(*, source_url="https://www.thewarfieldtheatre.com/events", metadata=None):
    src = ScrapingSource(
        platform="custom", scraper_key="aeg_axs", source_url=source_url,
        priority=0, enabled=True, id=1, club_id=999, metadata=metadata or {},
    )
    club = Club(
        id=999, name="The Warfield", address="982 Market St",
        website="https://www.thewarfieldtheatre.com", popularity=0, zip_code="94102",
        phone_number="", visible=True, timezone="America/Los_Angeles",
        city="San Francisco", state="CA",
        scraping_sources=[src], active_scraping_source=src,
    )
    scraper = AEGAXSVenueScraper(club)
    # Keep the comedy filter DB-free: stub the known-comedian lookups so only the
    # cheap keyword + allowlist signals decide. get_comedians_from_show_names
    # returns no matches, so non-comedy concerts are dropped.
    if scraper._comedy_filter:
        scraper._lineup_handler = MagicMock()
        scraper._lineup_handler.get_comedians_from_show_names.return_value = {}
        scraper._comedian_handler = MagicMock()
        scraper._comedian_handler.get_stored_popularity_by_names.return_value = {}
    return scraper


class TestScraperGlue:
    async def test_no_scraping_url_returns_empty_targets(self):
        scraper = _make_scraper(source_url="")
        assert await scraper.collect_scraping_targets() == []

    async def test_collect_targets_returns_source_url(self):
        scraper = _make_scraper()
        targets = await scraper.collect_scraping_targets()
        assert len(targets) == 1 and "thewarfieldtheatre.com/events" in targets[0]

    async def test_get_data_parses_fixture_unfiltered(self):
        scraper = _make_scraper()  # no comedy_filter → all shows
        scraper.fetch_html = AsyncMock(return_value=_load_fixture())
        page = await scraper.get_data("https://www.thewarfieldtheatre.com/events")
        assert page is not None
        assert len(page.event_list) == 20

    async def test_comedy_filter_keeps_only_comedy(self):
        scraper = _make_scraper(
            metadata={"comedy_filter": True, "comedy_title_allowlist": _ALLOWLIST}
        )
        scraper.fetch_html = AsyncMock(return_value=_load_fixture())
        page = await scraper.get_data("https://www.thewarfieldtheatre.com/events")
        assert page is not None
        kept = {e.title for e in page.event_list}
        assert kept == {_COMEDY_TITLE}

    async def test_comedy_filter_drops_all_when_no_match(self):
        # Empty allowlist + no known comedians → every concert dropped, get_data None.
        scraper = _make_scraper(metadata={"comedy_filter": True})
        scraper.fetch_html = AsyncMock(return_value=_load_fixture())
        assert await scraper.get_data("https://www.thewarfieldtheatre.com/events") is None

    async def test_get_data_empty_html_returns_none(self):
        scraper = _make_scraper()
        scraper.fetch_html = AsyncMock(return_value="")
        assert await scraper.get_data("https://www.thewarfieldtheatre.com/x") is None

    async def test_get_data_no_events_returns_none(self):
        scraper = _make_scraper()
        scraper.fetch_html = AsyncMock(return_value="<html><body>no cards here</body></html>")
        assert await scraper.get_data("https://www.thewarfieldtheatre.com/x") is None

    async def test_get_data_fetch_exception_returns_none(self):
        scraper = _make_scraper()
        scraper.fetch_html = AsyncMock(side_effect=RuntimeError("boom"))
        assert await scraper.get_data("https://www.thewarfieldtheatre.com/x") is None
