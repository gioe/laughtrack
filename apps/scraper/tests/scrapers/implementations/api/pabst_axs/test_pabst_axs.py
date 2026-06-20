"""Unit + smoke tests for the Pabst Theater Group venue-page scraper (TASK-3033).

The fixture is a recorded pabsttheater.org Riverside Theater venue page (trimmed
to the ``div.event_list`` subtree). Its shows are ``div.eventItem`` cards: a
title in the info/ticket link ``title`` attr ("More Info for <NAME>" / "Buy
Tickets for <NAME>"), an ``axs.com/...?skin=pabst`` ticket link, the venue's own
detail URL, and a dated thumbnail (``assets/img/YYYY.MM.DD-R-<slug>...png``).

The venue is music-dominated; only ~7 of the recorded shows are comedy, so the
scraper layers the shared comedy filter (keyword + per-source allowlist + known
comedian) to drop the concerts.
"""

import os

from unittest.mock import AsyncMock, MagicMock

import pytz

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.pabst_axs import PabstAXSEvent
from laughtrack.scrapers.implementations.api.pabst_axs.extractor import extract_events
from laughtrack.scrapers.implementations.api.pabst_axs.scraper import PabstAXSVenueScraper

_FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "riverside_venue_page.html")

# Comedy acts on the recorded page. Two carry the "comedy" keyword; the rest are
# comedian-name titles the keyword filter misses and the allowlist must catch.
_COMEDY_TITLES = {
    "Wait Wait… Don't Tell Me!",
    "HASAN HATES RONNY | RONNY HATES HASAN",
    "Anthony Jeselnik: Wrath of Man",
    "Ben Schwartz & Friends",
    "Josh Johnson's Comedy Band Camp",
    "Mojo Brookzz – Outta Pocket Comedy Tour",
    "Matt Mathews: Not What I Ordered World Tour",
}
# Per-source allowlist for the keyword-miss comedian acts (lives in
# scraping_sources.metadata.comedy_title_allowlist in production).
_ALLOWLIST = ["wait wait", "hasan", "anthony jeselnik", "ben schwartz", "matt mathews"]


def _load_fixture() -> str:
    with open(_FIXTURE, encoding="utf-8") as fh:
        return fh.read()


class _Club:
    id = 1
    name = "The Riverside Theater"
    timezone = "America/Chicago"

    def metadata_value(self, key):
        return None


class TestExtractEventsFromFixture:
    def test_parses_event_cards(self):
        events = extract_events(_load_fixture())
        # 24 eventItem cards; one ("Widespread Panic") carries no dated thumbnail
        # and is correctly skipped, leaving 23 dated shows.
        assert len(events) == 23

    def test_each_event_has_required_fields(self):
        for ev in extract_events(_load_fixture()):
            assert ev.title
            # ISO date parsed from the thumbnail filename.
            assert ev.date_str and len(ev.date_str) == 10 and ev.date_str[4] == "-"
            assert ev.show_page_url.startswith("http")

    def test_date_from_thumbnail_filename(self):
        ev = next(e for e in extract_events(_load_fixture()) if e.title == "Ben Schwartz & Friends")
        assert ev.date_str == "2026-10-16"
        assert "axs.com/events/" in (ev.ticket_url or "")

    def test_show_page_url_is_venue_detail_not_axs(self):
        ev = next(e for e in extract_events(_load_fixture()) if e.title == "Ben Schwartz & Friends")
        assert "pabsttheatergroup.com/events/detail/" in ev.show_page_url
        assert "axs.com" in (ev.ticket_url or "")

    def test_captures_comedy_among_concerts(self):
        titles = {e.title for e in extract_events(_load_fixture())}
        assert _COMEDY_TITLES <= titles  # all comedy acts present pre-filter

    def test_empty_html(self):
        assert extract_events("") == []


class TestToShow:
    def test_builds_future_show_with_default_time(self):
        ev = PabstAXSEvent(
            title="Ben Schwartz & Friends",
            date_str="2099-10-16",
            show_page_url="https://www.pabsttheatergroup.com/events/detail/ben-schwartz",
            ticket_url="https://www.axs.com/events/1317682/ben-schwartz-friends-tickets?skin=pabst",
        )
        show = ev.to_show(_Club())
        assert show is not None
        assert show.name == "Ben Schwartz & Friends"
        local = show.date.astimezone(pytz.timezone("America/Chicago"))
        assert (local.year, local.hour, local.minute) == (2099, 19, 0)  # default 19:00
        assert show.tickets[0].purchase_url.startswith("https://www.axs.com/")

    def test_default_show_time_override(self):
        class _ClubAt8(_Club):
            def metadata_value(self, key):
                return "20:30" if key == "default_show_time" else None

        ev = PabstAXSEvent(
            title="Late Show",
            date_str="2099-10-16",
            show_page_url="https://www.pabsttheatergroup.com/events/detail/late",
        )
        show = ev.to_show(_ClubAt8())
        local = show.date.astimezone(pytz.timezone("America/Chicago"))
        assert (local.hour, local.minute) == (20, 30)

    def test_ticket_falls_back_to_page_url(self):
        ev = PabstAXSEvent(
            title="No Ticket Link",
            date_str="2099-10-16",
            show_page_url="https://www.pabsttheatergroup.com/events/detail/no-tix",
            ticket_url=None,
        )
        show = ev.to_show(_Club())
        assert show.tickets[0].purchase_url == "https://www.pabsttheatergroup.com/events/detail/no-tix"

    def test_past_show_returns_none(self):
        ev = PabstAXSEvent(
            title="Old Show",
            date_str="2020-01-06",
            show_page_url="https://www.pabsttheatergroup.com/events/detail/old",
        )
        assert ev.to_show(_Club()) is None

    def test_unparseable_date_returns_none(self):
        ev = PabstAXSEvent(
            title="Bad Date",
            date_str="sometime next year",
            show_page_url="https://www.pabsttheatergroup.com/events/detail/bad",
        )
        assert ev.to_show(_Club()) is None


def _make_scraper(*, source_url="https://pabsttheater.org/venues/the-riverside-theater/", metadata=None):
    src = ScrapingSource(
        platform="custom", scraper_key="pabst_axs", source_url=source_url,
        priority=0, enabled=True, id=1, club_id=999, metadata=metadata or {},
    )
    club = Club(
        id=999, name="The Riverside Theater", address="116 W Wisconsin Ave",
        website="https://pabsttheater.org", popularity=0, zip_code="53203",
        phone_number="", visible=True, timezone="America/Chicago",
        city="Milwaukee", state="WI",
        scraping_sources=[src], active_scraping_source=src,
    )
    scraper = PabstAXSVenueScraper(club)
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
        assert len(targets) == 1 and "the-riverside-theater" in targets[0]

    async def test_get_data_parses_fixture_unfiltered(self):
        scraper = _make_scraper()  # no comedy_filter → all dated shows
        scraper.fetch_html = AsyncMock(return_value=_load_fixture())
        page = await scraper.get_data("https://pabsttheater.org/venues/the-riverside-theater/")
        assert page is not None
        assert len(page.event_list) == 23

    async def test_comedy_filter_keeps_only_comedy(self):
        scraper = _make_scraper(
            metadata={"comedy_filter": True, "comedy_title_allowlist": _ALLOWLIST}
        )
        scraper.fetch_html = AsyncMock(return_value=_load_fixture())
        page = await scraper.get_data("https://pabsttheater.org/venues/the-riverside-theater/")
        assert page is not None
        kept = {e.title for e in page.event_list}
        assert kept == _COMEDY_TITLES

    async def test_get_data_empty_html_returns_none(self):
        scraper = _make_scraper()
        scraper.fetch_html = AsyncMock(return_value="")
        assert await scraper.get_data("https://pabsttheater.org/x") is None

    async def test_get_data_no_events_returns_none(self):
        scraper = _make_scraper()
        scraper.fetch_html = AsyncMock(return_value="<html><body>no cards here</body></html>")
        assert await scraper.get_data("https://pabsttheater.org/x") is None

    async def test_get_data_fetch_exception_returns_none(self):
        scraper = _make_scraper()
        scraper.fetch_html = AsyncMock(side_effect=RuntimeError("boom"))
        assert await scraper.get_data("https://pabsttheater.org/x") is None
