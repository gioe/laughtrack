"""
Pipeline smoke tests for TourDatesScraper.

Exercises the scrape_async() override:
  _get_comedians_with_tour_ids() -> _scrape_comedian() per comedian
  -> _persist_shows_and_lineups() -> List[Show]

Key assertions:
- collect_scraping_targets() returns ["tour_dates"]
- scrape_async() returns Shows via the Songkick path
- scrape_async() returns Shows via the BandsInTown path
- scrape_async() returns [] when no comedians have tour IDs
"""

import importlib.util
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.scrapers.implementations.api.tour_dates.scraper import TourDatesScraper


def _club() -> Club:
    """Minimal platform club row that triggers the tour_dates scraper."""
    return Club(
        id=999,
        name="Tour Dates",
        address="",
        website="",
        scraping_url="tour_dates",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
        scraper="tour_dates",
    )


def _make_show(name: str = "Tom Segura at Punch Line Philly") -> Show:
    """Minimal Show object for mocked _scrape_comedian results."""
    return Show(
        name=name,
        club_id=1,
        date=datetime(2026, 7, 10, 20, 0, tzinfo=timezone.utc),
        show_page_url="https://www.songkick.com/concerts/12345678",
        timezone="America/New_York",
    )


def _comedian_row(
    name: str = "Tom Segura",
    uuid: str = "abc-123",
    songkick_id: str = "4567890",
    bandsintown_id: str = None,
) -> dict:
    """Minimal comedian DB row dict as returned by _get_comedians_with_tour_ids()."""
    return {
        "name": name,
        "uuid": uuid,
        "songkick_id": songkick_id,
        "bandsintown_id": bandsintown_id,
    }


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_tour_dates():
    """collect_scraping_targets() returns a single ["tour_dates"] target."""
    scraper = TourDatesScraper(_club())
    targets = await scraper.collect_scraping_targets()
    assert targets == ["tour_dates"]


@pytest.mark.asyncio
async def test_scrape_async_returns_empty_when_no_comedians_with_tour_ids():
    """
    scrape_async() returns [] when _get_comedians_with_tour_ids() finds
    no comedians with Songkick or BandsInTown IDs configured.
    """
    scraper = TourDatesScraper(_club())

    with patch.object(scraper, "_get_comedians_with_tour_ids", return_value=[]):
        shows = await scraper.scrape_async()

    assert shows == [], (
        "scrape_async() should return [] when no comedians have tour IDs"
    )


@pytest.mark.asyncio
async def test_scrape_async_returns_shows_via_songkick_path():
    """
    scrape_async() returns Shows when a comedian has a songkick_id and
    _scrape_comedian produces shows for that comedian.
    """
    scraper = TourDatesScraper(_club())
    expected_show = _make_show("Tom Segura at The Vic")
    comedian_row = _comedian_row(songkick_id="4567890", bandsintown_id=None)

    with (
        patch.object(
            scraper,
            "_get_comedians_with_tour_ids",
            return_value=[comedian_row],
        ),
        patch.object(
            scraper,
            "_scrape_comedian",
            new=AsyncMock(return_value=[expected_show]),
        ),
        patch.object(scraper, "_persist_shows_and_lineups", return_value=None),
    ):
        shows = await scraper.scrape_async()

    assert len(shows) == 1, (
        "scrape_async() should return 1 Show from the Songkick path"
    )
    assert shows[0].name == "Tom Segura at The Vic"


@pytest.mark.asyncio
async def test_scrape_async_returns_shows_via_bandsintown_path():
    """
    scrape_async() returns Shows when a comedian has a bandsintown_id and
    _scrape_comedian produces shows for that comedian.
    """
    scraper = TourDatesScraper(_club())
    expected_show = _make_show("Nate Bargatze at Ryman Auditorium")
    comedian_row = _comedian_row(
        name="Nate Bargatze",
        uuid="def-456",
        songkick_id=None,
        bandsintown_id="nate-bargatze",
    )

    with (
        patch.object(
            scraper,
            "_get_comedians_with_tour_ids",
            return_value=[comedian_row],
        ),
        patch.object(
            scraper,
            "_scrape_comedian",
            new=AsyncMock(return_value=[expected_show]),
        ),
        patch.object(scraper, "_persist_shows_and_lineups", return_value=None),
    ):
        shows = await scraper.scrape_async()

    assert len(shows) == 1, (
        "scrape_async() should return 1 Show from the BandsInTown path"
    )
    assert shows[0].name == "Nate Bargatze at Ryman Auditorium"


@pytest.mark.asyncio
async def test_scrape_async_aggregates_shows_across_multiple_comedians():
    """
    scrape_async() aggregates Shows from multiple comedians into a flat list.
    """
    scraper = TourDatesScraper(_club())
    show_a = _make_show("Tom Segura at Club A")
    show_b = _make_show("Nate Bargatze at Club B")
    comedian_rows = [
        _comedian_row(name="Tom Segura", uuid="a-1", songkick_id="111"),
        _comedian_row(name="Nate Bargatze", uuid="b-2", songkick_id="222"),
    ]

    call_count = 0

    async def fake_scrape_comedian(row, semaphore):
        nonlocal call_count
        call_count += 1
        return [show_a] if row["name"] == "Tom Segura" else [show_b]

    with (
        patch.object(scraper, "_get_comedians_with_tour_ids", return_value=comedian_rows),
        patch.object(scraper, "_scrape_comedian", side_effect=fake_scrape_comedian),
        patch.object(scraper, "_persist_shows_and_lineups", return_value=None),
    ):
        shows = await scraper.scrape_async()

    assert call_count == 2, "scrape_async() should call _scrape_comedian once per comedian"
    assert len(shows) == 2, "scrape_async() should aggregate Shows from all comedians"
