"""
Pipeline smoke tests for ComedyClubHaugScraper.

Exercises get_data() against mocked HTML responses and verifies
the full transformation pipeline produces Show objects.
"""

import importlib.util

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.comedy_club_haug import ComedyClubHaugEvent
from laughtrack.scrapers.implementations.venues.comedy_club_haug.scraper import (
    ComedyClubHaugScraper,
)
from laughtrack.scrapers.implementations.venues.comedy_club_haug.data import (
    ComedyClubHaugPageData,
)
from laughtrack.scrapers.implementations.venues.comedy_club_haug.extractor import (
    ComedyClubHaugExtractor,
)

SHOWS_URL = "https://comedyclubhaug.com/shows"


def _club() -> Club:
    return Club(
        id=157,
        name="Comedy Club Haug",
        address="Nieuwe Binnenweg 19",
        website="https://comedyclubhaug.com",
        scraping_url=SHOWS_URL,
        popularity=0,
        zip_code="3014 GA",
        phone_number="",
        visible=True,
        timezone="Europe/Amsterdam",
    )


def _raw_event(
    id_="123",
    title="Best of Stand-Up",
    status="active",
    start="2026-04-09T18:30:00+00:00",
    ticket_link="https://stager.co/events/best-of-stand-up",
    artists=None,
) -> dict:
    return {
        "id": id_,
        "title": title,
        "url": f"https://comedyclubhaug.com/shows/{title.lower().replace(' ', '-')}",
        "slug": title.lower().replace(" ", "-"),
        "eventTitle": title,
        "eventSubtitle": "",
        "eventStatus": status,
        "eventProgramStart": start,
        "eventProgramEnd": "2026-04-09T20:30:00+00:00",
        "eventTicketLink": ticket_link,
        "artists": artists or [{"title": "Comedian A"}],
        "eventCategories": [],
    }


# ---------------------------------------------------------------------------
# collect_scraping_targets
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_scraping_targets():
    scraper = ComedyClubHaugScraper(_club())
    targets = await scraper.collect_scraping_targets()
    assert targets == [SHOWS_URL]


# ---------------------------------------------------------------------------
# get_data tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data(monkeypatch):
    """get_data() returns ComedyClubHaugPageData with active events."""
    scraper = ComedyClubHaugScraper(_club())

    monkeypatch.setattr(
        ComedyClubHaugExtractor,
        "extract_shows",
        staticmethod(lambda html: [
            _raw_event(id_="1", title="Show A"),
            _raw_event(id_="2", title="Show B"),
        ]),
    )

    async def fake_fetch(self, url):
        return "<html>fake</html>"

    monkeypatch.setattr(ComedyClubHaugScraper, "fetch_html", fake_fetch)

    result = await scraper.get_data(SHOWS_URL)

    assert isinstance(result, ComedyClubHaugPageData)
    assert len(result.event_list) == 2
    titles = {e.title for e in result.event_list}
    assert "Show A" in titles
    assert "Show B" in titles


@pytest.mark.asyncio
async def test_get_data_filters_non_active_events(monkeypatch):
    """get_data() skips events that are not status=active."""
    scraper = ComedyClubHaugScraper(_club())

    monkeypatch.setattr(
        ComedyClubHaugExtractor,
        "extract_shows",
        staticmethod(lambda html: [
            _raw_event(id_="1", title="Active Show", status="active"),
            _raw_event(id_="2", title="Sold Out Show", status="sold_out"),
        ]),
    )

    async def fake_fetch(self, url):
        return "<html>fake</html>"

    monkeypatch.setattr(ComedyClubHaugScraper, "fetch_html", fake_fetch)

    result = await scraper.get_data(SHOWS_URL)

    assert isinstance(result, ComedyClubHaugPageData)
    assert len(result.event_list) == 1
    assert result.event_list[0].title == "Active Show"


@pytest.mark.asyncio
async def test_get_data_returns_none_on_empty_html(monkeypatch):
    """get_data() returns None when fetch returns empty HTML."""
    scraper = ComedyClubHaugScraper(_club())

    async def fake_fetch(self, url):
        return ""

    monkeypatch.setattr(ComedyClubHaugScraper, "fetch_html", fake_fetch)

    result = await scraper.get_data(SHOWS_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_on_no_events(monkeypatch):
    """get_data() returns None when extractor finds no events."""
    scraper = ComedyClubHaugScraper(_club())

    monkeypatch.setattr(
        ComedyClubHaugExtractor,
        "extract_shows",
        staticmethod(lambda html: []),
    )

    async def fake_fetch(self, url):
        return "<html>fake</html>"

    monkeypatch.setattr(ComedyClubHaugScraper, "fetch_html", fake_fetch)

    result = await scraper.get_data(SHOWS_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_strips_query_params_from_ticket_url(monkeypatch):
    """get_data() strips UTM parameters from ticket URLs."""
    scraper = ComedyClubHaugScraper(_club())

    monkeypatch.setattr(
        ComedyClubHaugExtractor,
        "extract_shows",
        staticmethod(lambda html: [
            _raw_event(ticket_link="https://stager.co/events/show?utm_source=website&utm_medium=link"),
        ]),
    )

    async def fake_fetch(self, url):
        return "<html>fake</html>"

    monkeypatch.setattr(ComedyClubHaugScraper, "fetch_html", fake_fetch)

    result = await scraper.get_data(SHOWS_URL)
    assert result is not None
    assert "utm_source" not in result.event_list[0].ticket_url


@pytest.mark.asyncio
async def test_get_data_extracts_performers_from_artists(monkeypatch):
    """get_data() extracts performer names from the artists array."""
    scraper = ComedyClubHaugScraper(_club())

    monkeypatch.setattr(
        ComedyClubHaugExtractor,
        "extract_shows",
        staticmethod(lambda html: [
            _raw_event(artists=[{"title": "Theo Maassen"}, {"title": "Hans Teeuwen"}]),
        ]),
    )

    async def fake_fetch(self, url):
        return "<html>fake</html>"

    monkeypatch.setattr(ComedyClubHaugScraper, "fetch_html", fake_fetch)

    result = await scraper.get_data(SHOWS_URL)
    assert result is not None
    assert result.event_list[0].performers == ["Theo Maassen", "Hans Teeuwen"]


# ---------------------------------------------------------------------------
# Full transformation pipeline
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transformation_pipeline_produces_shows(monkeypatch):
    """Full pipeline: get_data → transform → Show objects."""
    scraper = ComedyClubHaugScraper(_club())

    monkeypatch.setattr(
        ComedyClubHaugExtractor,
        "extract_shows",
        staticmethod(lambda html: [
            _raw_event(id_="1", title="Comedy Night"),
        ]),
    )

    async def fake_fetch(self, url):
        return "<html>fake</html>"

    monkeypatch.setattr(ComedyClubHaugScraper, "fetch_html", fake_fetch)

    page_data = await scraper.get_data(SHOWS_URL)
    assert page_data is not None

    shows = scraper.transformation_pipeline.transform(page_data)
    assert len(shows) >= 1
    assert shows[0].name == "Comedy Night"
    assert shows[0].club_id == 157
