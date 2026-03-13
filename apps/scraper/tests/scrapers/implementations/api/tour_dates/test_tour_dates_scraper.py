"""Unit tests for TourDatesScraper."""

import asyncio
import os
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from laughtrack.scrapers.implementations.api.tour_dates.scraper import TourDatesScraper
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show


@pytest.fixture
def platform_club() -> Club:
    """Minimal platform club that triggers TourDatesScraper."""
    return Club(
        id=999,
        name="Tour Dates",
        address="",
        website="",
        scraping_url="tour_dates",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=False,
        scraper="tour_dates",
    )


def _make_venue_club(club_id: int = 1, name: str = "Madison Square Garden") -> Club:
    return Club(
        id=club_id,
        name=name,
        address="New York, NY",
        website="",
        scraping_url="tour_dates",
        popularity=0,
        zip_code="10001",
        phone_number="",
        visible=True,
        scraper="tour_dates",
        timezone="America/New_York",
    )


# ------------------------------------------------------------------ #
# collect_scraping_targets                                             #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_collect_targets_returns_tour_dates(platform_club):
    scraper = TourDatesScraper(platform_club)
    targets = await scraper.collect_scraping_targets()
    assert targets == ["tour_dates"]


# ------------------------------------------------------------------ #
# scrape_async — no comedians with tour IDs                           #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_scrape_async_no_comedians(platform_club):
    scraper = TourDatesScraper(platform_club)

    with patch.object(scraper, "_get_comedians_with_tour_ids", return_value=[]):
        shows = await scraper.scrape_async()

    assert shows == []


# ------------------------------------------------------------------ #
# scrape_async — Songkick happy path                                  #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_scrape_async_songkick_returns_shows(platform_club):
    """Given a comedian with songkick_id and a mocked API response, returns Shows."""
    comedian_row = {
        "uuid": "abc-123",
        "name": "John Mulaney",
        "songkick_id": "sk-12345",
        "bandsintown_id": None,
    }

    future_date = datetime(2027, 6, 1, 19, 30, tzinfo=timezone.utc)

    mock_show = Show(
        name="John Mulaney at Madison Square Garden",
        club_id=1,
        date=future_date,
        show_page_url="https://www.songkick.com/concerts/1",
        lineup=[],
    )

    scraper = TourDatesScraper(platform_club)
    scraper._songkick_api_key = "fake_key"

    with patch.object(scraper, "_get_comedians_with_tour_ids", return_value=[comedian_row]):
        with patch.object(
            scraper, "_fetch_songkick_shows", new=AsyncMock(return_value=[mock_show])
        ):
            with patch.object(scraper, "_persist_shows_and_lineups"):
                shows = await scraper.scrape_async()

    assert len(shows) == 1
    assert isinstance(shows[0], Show)


# ------------------------------------------------------------------ #
# scrape_async — BandsInTown happy path                               #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_scrape_async_bandsintown_returns_shows(platform_club):
    """Given a comedian with bandsintown_id and a mocked API response, returns Shows."""
    comedian_row = {
        "uuid": "def-456",
        "name": "Hannah Gadsby",
        "songkick_id": None,
        "bandsintown_id": "hannah-gadsby",
    }

    future_date = datetime(2027, 7, 15, 20, 0, tzinfo=timezone.utc)

    mock_show = Show(
        name="Hannah Gadsby at The Comedy Store",
        club_id=2,
        date=future_date,
        show_page_url="https://www.bandsintown.com/e/123",
        lineup=[],
    )

    scraper = TourDatesScraper(platform_club)
    scraper._bandsintown_app_id = "fake_app_id"

    with patch.object(scraper, "_get_comedians_with_tour_ids", return_value=[comedian_row]):
        with patch.object(
            scraper, "_fetch_bandsintown_shows", new=AsyncMock(return_value=[mock_show])
        ):
            with patch.object(scraper, "_persist_shows_and_lineups"):
                shows = await scraper.scrape_async()

    assert len(shows) == 1
    assert isinstance(shows[0], Show)


# ------------------------------------------------------------------ #
# scrape_async — comedian error isolation                             #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_scrape_async_skips_comedian_on_api_error(platform_club):
    """An API error for one comedian should not prevent other comedians from being processed."""
    comedian_ok = {
        "uuid": "uuid-ok",
        "name": "Good Comic",
        "songkick_id": "sk-ok",
        "bandsintown_id": None,
    }
    comedian_bad = {
        "uuid": "uuid-bad",
        "name": "Bad Comic",
        "songkick_id": "sk-bad",
        "bandsintown_id": None,
    }

    future_date = datetime(2027, 8, 1, 19, 0, tzinfo=timezone.utc)
    good_show = Show(
        name="Good Comic at Venue",
        club_id=1,
        date=future_date,
        show_page_url="https://www.songkick.com/concerts/1",
        lineup=[],
    )

    async def fake_fetch_songkick(comedian, artist_id):
        if artist_id == "sk-bad":
            raise RuntimeError("API error")
        return [good_show]

    scraper = TourDatesScraper(platform_club)
    scraper._songkick_api_key = "fake_key"

    with patch.object(scraper, "_get_comedians_with_tour_ids", return_value=[comedian_ok, comedian_bad]):
        with patch.object(scraper, "_fetch_songkick_shows", side_effect=fake_fetch_songkick):
            with patch.object(scraper, "_persist_shows_and_lineups"):
                shows = await scraper.scrape_async()

    # The bad comedian is skipped; the good comedian's show is still returned
    assert len(shows) == 1
    assert shows[0].club_id == 1


# ------------------------------------------------------------------ #
# _songkick_event_to_show — filtering                                 #
# ------------------------------------------------------------------ #

def test_songkick_event_to_show_filters_non_us(platform_club):
    """Events not in the US should return None."""
    from laughtrack.core.entities.comedian.model import Comedian

    scraper = TourDatesScraper(platform_club)
    comedian = Comedian(name="Test Comic", uuid="test-uuid")

    non_us_event = {
        "id": 1,
        "displayName": "Test Comic at O2",
        "uri": "https://www.songkick.com/concerts/1",
        "location": {"city": "London, UK"},
        "venue": {"displayName": "The O2"},
        "start": {"datetime": "2027-09-01T20:00:00+0000"},
    }

    result = scraper._songkick_event_to_show(non_us_event, comedian)
    assert result is None


def test_songkick_event_to_show_creates_show_for_us_event(platform_club):
    """A valid US event with a mocked club upsert should produce a Show."""
    from laughtrack.core.entities.comedian.model import Comedian

    scraper = TourDatesScraper(platform_club)
    comedian = Comedian(name="John Mulaney", uuid="jm-uuid")
    venue_club = _make_venue_club()

    us_event = {
        "id": 42,
        "displayName": "John Mulaney at MSG",
        "uri": "https://www.songkick.com/concerts/42",
        "location": {"city": "New York, NY, US"},
        "venue": {"displayName": "Madison Square Garden"},
        "start": {"datetime": "2027-10-01T20:00:00+0000"},
    }

    with patch.object(
        scraper._club_handler, "upsert_for_tour_date_venue", return_value=venue_club
    ) as mock_upsert:
        show = scraper._songkick_event_to_show(us_event, comedian)

    assert show is not None
    assert show.club_id == 1
    assert show.lineup == [comedian]
    assert "John Mulaney" in show.name

    # Verify address is correctly parsed from "New York, NY, US" → "New York, NY"
    venue_dict = mock_upsert.call_args.args[0]
    assert venue_dict["address"] == "New York, NY"


# ------------------------------------------------------------------ #
# _bandsintown_event_to_show — filtering                              #
# ------------------------------------------------------------------ #

def test_bandsintown_event_to_show_filters_non_us(platform_club):
    """Non-US BandsInTown events should return None."""
    from laughtrack.core.entities.comedian.model import Comedian

    scraper = TourDatesScraper(platform_club)
    comedian = Comedian(name="Test Comic", uuid="test-uuid")

    non_us_event = {
        "id": "1",
        "url": "https://www.bandsintown.com/e/1",
        "datetime": "2027-09-01T20:00:00",
        "venue": {
            "name": "Roundhouse",
            "city": "London",
            "region": "",
            "country": "United Kingdom",
        },
    }

    result = scraper._bandsintown_event_to_show(non_us_event, comedian)
    assert result is None


def test_bandsintown_event_to_show_creates_show_for_us_event(platform_club):
    """A valid US BandsInTown event with a mocked club upsert should produce a Show."""
    from laughtrack.core.entities.comedian.model import Comedian

    scraper = TourDatesScraper(platform_club)
    comedian = Comedian(name="Hannah Gadsby", uuid="hg-uuid")
    venue_club = _make_venue_club(club_id=2, name="The Comedy Store")

    us_event = {
        "id": "99",
        "url": "https://www.bandsintown.com/e/99",
        "datetime": "2027-11-15T20:00:00",
        "venue": {
            "name": "The Comedy Store",
            "city": "Los Angeles",
            "region": "CA",
            "country": "United States",
        },
    }

    with patch.object(
        scraper._club_handler, "upsert_for_tour_date_venue", return_value=venue_club
    ) as mock_upsert:
        show = scraper._bandsintown_event_to_show(us_event, comedian)

    assert show is not None
    assert show.club_id == 2
    assert show.lineup == [comedian]
    assert "Hannah Gadsby" in show.name

    # Verify address is correctly assembled from city + region ("Los Angeles", "CA" → "Los Angeles, CA")
    venue_dict = mock_upsert.call_args.args[0]
    assert venue_dict["address"] == "Los Angeles, CA"


# ------------------------------------------------------------------ #
# _parse_datetime                                                      #
# ------------------------------------------------------------------ #

def test_parse_datetime_handles_utc_z(platform_club):
    scraper = TourDatesScraper(platform_club)
    dt = scraper._parse_datetime("2027-06-01T19:30:00Z")
    assert dt is not None
    assert dt.year == 2027
    assert dt.tzinfo is not None


def test_parse_datetime_handles_date_only(platform_club):
    scraper = TourDatesScraper(platform_club)
    dt = scraper._parse_datetime("2027-06-01")
    assert dt is not None
    assert dt.year == 2027


def test_parse_datetime_returns_none_for_invalid(platform_club):
    scraper = TourDatesScraper(platform_club)
    dt = scraper._parse_datetime("not-a-date")
    assert dt is None


# ------------------------------------------------------------------ #
# _persist_shows_and_lineups                                          #
# ------------------------------------------------------------------ #

def test_persist_shows_and_lineups_links_lineups(platform_club):
    """After insert_shows() sets IDs, batch_update_lineups is called with those shows."""
    from laughtrack.core.entities.comedian.model import Comedian

    future_date = datetime(2027, 9, 1, 20, 0, tzinfo=timezone.utc)
    comedian = Comedian(name="Test Comic", uuid="test-uuid")
    show = Show(
        name="Test Comic at Venue",
        club_id=1,
        date=future_date,
        show_page_url="https://www.songkick.com/concerts/42",
        lineup=[comedian],
    )

    def fake_insert_shows(shows):
        # Simulate ShowHandler setting show IDs on the original objects
        for s in shows:
            s.id = 99

    scraper = TourDatesScraper(platform_club)

    with patch.object(scraper._show_handler, "insert_shows", side_effect=fake_insert_shows):
        with patch.object(
            scraper._lineup_handler, "batch_update_lineups"
        ) as mock_lineups:
            scraper._persist_shows_and_lineups([show])

    mock_lineups.assert_called_once()
    called_shows = mock_lineups.call_args[0][0]
    assert len(called_shows) == 1
    assert called_shows[0].id == 99


def test_persist_shows_and_lineups_skips_lineup_when_no_ids(platform_club):
    """If insert_shows() fails to set IDs, lineup insertion is skipped gracefully."""
    future_date = datetime(2027, 9, 2, 20, 0, tzinfo=timezone.utc)
    show = Show(
        name="Test Comic at Venue",
        club_id=1,
        date=future_date,
        show_page_url="https://www.songkick.com/concerts/43",
        lineup=[],
    )
    # show.id remains None — simulates insert returning no IDs

    scraper = TourDatesScraper(platform_club)

    with patch.object(scraper._show_handler, "insert_shows"):
        with patch.object(
            scraper._lineup_handler, "batch_update_lineups"
        ) as mock_lineups:
            scraper._persist_shows_and_lineups([show])

    mock_lineups.assert_not_called()


# ------------------------------------------------------------------ #
# Concurrency                                                         #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_comedians_processed_concurrently(platform_club):
    """Multiple comedians should be scraped concurrently, not one-by-one."""
    comedian_rows = [
        {"uuid": f"uuid-{i}", "name": f"Comic {i}", "songkick_id": f"sk-{i}", "bandsintown_id": None}
        for i in range(4)
    ]

    active = [0]
    max_active = [0]

    async def slow_fetch(comedian, artist_id):
        active[0] += 1
        max_active[0] = max(max_active[0], active[0])
        await asyncio.sleep(0)  # yield to let other coroutines run
        active[0] -= 1
        future_date = datetime(2027, 6, 1, 19, 30, tzinfo=timezone.utc)
        return [Show(name=f"Show for {comedian.name}", club_id=1, date=future_date, show_page_url="https://example.com", lineup=[])]

    scraper = TourDatesScraper(platform_club)
    scraper._songkick_api_key = "fake_key"

    with patch.object(scraper, "_get_comedians_with_tour_ids", return_value=comedian_rows):
        with patch.object(scraper, "_fetch_songkick_shows", side_effect=slow_fetch):
            with patch.object(scraper, "_persist_shows_and_lineups"):
                shows = await scraper.scrape_async()

    assert len(shows) == 4
    assert max_active[0] >= 2, f"Expected concurrent execution, but max_active={max_active[0]}"


@pytest.mark.asyncio
async def test_scrape_async_skips_comedian_on_error_concurrent(platform_club):
    """Error in one comedian does not abort others when processing concurrently."""
    comedian_rows = [
        {"uuid": "uuid-ok", "name": "Good Comic", "songkick_id": "sk-ok", "bandsintown_id": None},
        {"uuid": "uuid-bad", "name": "Bad Comic", "songkick_id": "sk-bad", "bandsintown_id": None},
    ]

    future_date = datetime(2027, 8, 1, 19, 0, tzinfo=timezone.utc)
    good_show = Show(name="Good Comic at Venue", club_id=1, date=future_date, show_page_url="https://example.com", lineup=[])

    async def fake_fetch(comedian, artist_id):
        if artist_id == "sk-bad":
            raise RuntimeError("API error")
        return [good_show]

    scraper = TourDatesScraper(platform_club)
    scraper._songkick_api_key = "fake_key"

    with patch.object(scraper, "_get_comedians_with_tour_ids", return_value=comedian_rows):
        with patch.object(scraper, "_fetch_songkick_shows", side_effect=fake_fetch):
            with patch.object(scraper, "_persist_shows_and_lineups"):
                shows = await scraper.scrape_async()

    assert len(shows) == 1
    assert shows[0].club_id == 1


def test_max_concurrent_comedians_reads_env_var(platform_club):
    """MAX_CONCURRENT_COMEDIANS env var controls the semaphore limit; falls back to default on bad values."""
    scraper = TourDatesScraper(platform_club)

    with patch.dict(os.environ, {"MAX_CONCURRENT_COMEDIANS": "3"}):
        assert scraper._max_concurrent_comedians == 3

    assert scraper._max_concurrent_comedians == 5  # default

    with patch.dict(os.environ, {"MAX_CONCURRENT_COMEDIANS": "abc"}):
        assert scraper._max_concurrent_comedians == 5  # invalid → default

    with patch.dict(os.environ, {"MAX_CONCURRENT_COMEDIANS": "0"}):
        assert scraper._max_concurrent_comedians == 5  # zero → default
