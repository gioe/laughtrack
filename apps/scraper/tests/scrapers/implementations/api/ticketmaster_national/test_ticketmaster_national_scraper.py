"""Unit tests for TicketmasterNationalScraper."""

import importlib.util

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from laughtrack.scrapers.implementations.api.ticketmaster_national.scraper import (
    TicketmasterNationalScraper,
)
from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.show.model import Show


@pytest.fixture
def platform_club() -> Club:
    """Minimal 'platform' club row that triggers the national scraper."""
    _c = Club(
        id=999,
        name="Ticketmaster National",
        address="",
        website="",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
    )
    _c.active_scraping_source = ScrapingSource(
        id=1,
        club_id=_c.id,
        platform="ticketmaster_national",
        scraper_key="ticketmaster_national",
        source_url="www.ticketmaster.com",
        external_id=None,
    )
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _make_api_event(
    venue_id="KovZpZAEAaEA",
    venue_name="The Comedy Store",
    event_id="vvG1zZ4M8d8kBJ",
    event_url="https://www.ticketmaster.com/event/vvG1zZ4M8d8kBJ",
):
    """Build a minimal Ticketmaster Discovery API event dict."""
    return {
        "id": event_id,
        "name": "Comedy Night",
        "url": event_url,
        "dates": {
            "start": {"localDate": "2026-06-01", "localTime": "20:00:00"},
            "status": {"code": "onsale"},
        },
        "sales": {"public": {"startDateTime": "2026-01-01T00:00:00Z"}},
        "priceRanges": [{"type": "standard", "min": 25.0, "max": 35.0}],
        "_embedded": {
            "venues": [
                {
                    "id": venue_id,
                    "name": venue_name,
                    "timezone": "America/Los_Angeles",
                    "postalCode": "90069",
                    "address": {"line1": "8433 Sunset Blvd"},
                    "city": {"name": "West Hollywood"},
                    "state": {"stateCode": "CA"},
                }
            ],
            "attractions": [{"id": "K8vZ917KNeV", "name": "Dave Chappelle"}],
        },
    }


def _make_club(
    club_id=42,
    name="The Comedy Store",
    ticketmaster_id="KovZpZAEAaEA",
    timezone="America/Los_Angeles",
):
    _c = Club(
        id=club_id,
        name=name,
        address="8433 Sunset Blvd, West Hollywood, CA",
        website="",
        popularity=0,
        zip_code="90069",
        phone_number="",
        visible=True,
        timezone=timezone,
    )
    _c.active_scraping_source = ScrapingSource(
        id=1,
        club_id=_c.id,
        platform="ticketmaster",
        scraper_key="live_nation",
        source_url="www.ticketmaster.com",
        external_id=ticketmaster_id,
    )
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


_CONFIG_PATCH = "laughtrack.scrapers.implementations.api.ticketmaster_national.scraper.ConfigManager.get_config"


# ------------------------------------------------------------------ #
# collect_scraping_targets                                             #
# ------------------------------------------------------------------ #


@pytest.mark.asyncio
async def test_collect_targets_returns_national(platform_club):
    with patch(_CONFIG_PATCH, return_value="fake_api_key"):
        s = TicketmasterNationalScraper(platform_club)
    targets = await s.collect_scraping_targets()
    assert targets == ["national"]


# ------------------------------------------------------------------ #
# scrape_async — empty API response                                    #
# ------------------------------------------------------------------ #


@pytest.mark.asyncio
async def test_scrape_async_empty_response(platform_club):
    with patch(_CONFIG_PATCH, return_value="fake_api_key"):
        scraper = TicketmasterNationalScraper(platform_club)

    with patch.object(scraper, "_fetch_national_comedy_events", new=AsyncMock(return_value=[])):
        shows = await scraper.scrape_async()

    assert shows == []


# ------------------------------------------------------------------ #
# scrape_async — happy path                                            #
# ------------------------------------------------------------------ #


@pytest.mark.asyncio
async def test_scrape_async_persists_each_event_and_returns_empty(platform_club):
    """
    Two events from the same venue upsert the club once and produce a Show for
    each event. The national scraper persists the shows itself (in chunks) and
    returns [] so the per-club pipeline does not re-persist.
    """
    event1 = _make_api_event(event_id="ev1", event_url="https://tm.com/ev1")
    event2 = _make_api_event(event_id="ev2", event_url="https://tm.com/ev2")
    api_events = [event1, event2]
    upserted_club = _make_club()

    mock_show = MagicMock(spec=Show)
    mock_show.club_id = 42

    with patch(_CONFIG_PATCH, return_value="fake_api_key"):
        scraper = TicketmasterNationalScraper(platform_club)

    with patch.object(scraper, "_fetch_national_comedy_events", new=AsyncMock(return_value=api_events)):
        with patch.object(
            scraper._club_handler,
            "upsert_for_ticketmaster_venue",
            return_value=upserted_club,
        ):
            with patch.object(scraper, "_persist_in_chunks", new=AsyncMock(return_value=2)) as mock_persist:
                with patch(
                    "laughtrack.scrapers.implementations.api.ticketmaster_national.scraper.TicketmasterClient"
                ) as MockClient:
                    MockClient.return_value.create_show.return_value = mock_show
                    shows = await scraper.scrape_async()

    # scrape_async returns [] — shows were persisted internally, not handed back
    assert shows == []
    persisted_arg = mock_persist.call_args[0][0]
    assert len(persisted_arg) == 2
    assert all(s.club_id == 42 for s in persisted_arg)


# ------------------------------------------------------------------ #
# scrape_async — club upsert failure is isolated per venue            #
# ------------------------------------------------------------------ #


@pytest.mark.asyncio
async def test_scrape_async_skips_venue_on_upsert_failure(platform_club):
    """
    A DB error upserting one venue should not prevent other venues from
    being processed.
    """
    event_ok = _make_api_event(venue_id="V1", venue_name="Good Club", event_id="ev1")
    event_bad = _make_api_event(venue_id="V2", venue_name="Bad Club", event_id="ev2")
    api_events = [event_ok, event_bad]

    good_club = _make_club(club_id=1, ticketmaster_id="V1")
    mock_show = MagicMock(spec=Show)
    mock_show.club_id = 1

    def _upsert(venue):
        if venue.get("id") == "V2":
            raise RuntimeError("DB error")
        return good_club

    with patch(_CONFIG_PATCH, return_value="fake_api_key"):
        scraper = TicketmasterNationalScraper(platform_club)

    with patch.object(scraper, "_fetch_national_comedy_events", new=AsyncMock(return_value=api_events)):
        with patch.object(scraper._club_handler, "upsert_for_ticketmaster_venue", side_effect=_upsert):
            with patch.object(scraper, "_persist_in_chunks", new=AsyncMock(return_value=1)) as mock_persist:
                with patch(
                    "laughtrack.scrapers.implementations.api.ticketmaster_national.scraper.TicketmasterClient"
                ) as MockClient:
                    MockClient.return_value.create_show.return_value = mock_show
                    shows = await scraper.scrape_async()

    # only the good venue's show is produced + persisted; scrape_async returns []
    assert shows == []
    persisted_arg = mock_persist.call_args[0][0]
    assert len(persisted_arg) == 1
    assert persisted_arg[0].club_id == 1


# ------------------------------------------------------------------ #
# _persist_in_chunks — batched persistence                            #
# ------------------------------------------------------------------ #


@pytest.mark.asyncio
async def test_persist_in_chunks_batches_by_chunk_size(platform_club):
    """Shows are persisted via ShowService.insert_shows in _PERSIST_CHUNK_SIZE
    batches, and the total persisted count is returned."""
    with patch(_CONFIG_PATCH, return_value="fake_api_key"):
        scraper = TicketmasterNationalScraper(platform_club)
    scraper._PERSIST_CHUNK_SIZE = 2  # small chunk so 5 shows => 3 calls (2,2,1)

    shows = [MagicMock(spec=Show) for _ in range(5)]

    with patch("laughtrack.core.entities.show.service.ShowService") as MockService:
        persisted = await scraper._persist_in_chunks(shows)

    insert = MockService.return_value.insert_shows
    assert insert.call_count == 3
    # chunk sizes: 2, 2, 1
    assert [len(call.args[0]) for call in insert.call_args_list] == [2, 2, 1]
    assert persisted == 5


@pytest.mark.asyncio
async def test_persist_in_chunks_empty_is_noop(platform_club):
    with patch(_CONFIG_PATCH, return_value="fake_api_key"):
        scraper = TicketmasterNationalScraper(platform_club)
    with patch("laughtrack.core.entities.show.service.ShowService") as MockService:
        persisted = await scraper._persist_in_chunks([])
    assert persisted == 0
    MockService.return_value.insert_shows.assert_not_called()


# ------------------------------------------------------------------ #
# _process_events — non-comedy filtering                              #
# ------------------------------------------------------------------ #


@pytest.mark.asyncio
async def test_process_events_drops_non_comedy_events(platform_club):
    """The Discovery API returns multi-genre events (e.g. music festivals)
    under classificationName=Comedy. Their own classification is Music/Sports,
    so _is_comedy_event must drop them before venue upsert / show creation —
    otherwise their attractions land as fake comedians (e.g. Springsteen)."""
    comedy = _make_api_event(venue_id="V1", event_id="c1")  # no classifications -> comedy
    music = _make_api_event(venue_id="V2", venue_name="Amphitheater", event_id="m1")
    music["classifications"] = [{"segment": {"name": "Music"}, "genre": {"name": "Rock"}, "subGenre": {"name": "Pop"}}]

    upserted = _make_club(club_id=7)
    mock_show = MagicMock(spec=Show)
    mock_show.club_id = 7

    with patch(_CONFIG_PATCH, return_value="fake_api_key"):
        scraper = TicketmasterNationalScraper(platform_club)

    with patch.object(scraper._club_handler, "upsert_for_ticketmaster_venue", return_value=upserted) as mock_upsert:
        with patch(
            "laughtrack.scrapers.implementations.api.ticketmaster_national.scraper.TicketmasterClient"
        ) as MockClient:
            MockClient.return_value.create_show.return_value = mock_show
            shows = await scraper._process_events([comedy, music])

    # the music venue (V2) is never upserted and produces no show
    assert mock_upsert.call_count == 1
    upserted_venue = mock_upsert.call_args[0][0]
    assert upserted_venue.get("id") == "V1"
    assert len(shows) == 1


@pytest.mark.asyncio
async def test_process_events_fetches_ticketweb_html_before_create_show(platform_club):
    ticketweb_url = "https://www.ticketweb.com/event/andrew-schulz-ontario-improv-tickets/14938863"
    event = _make_api_event(event_url=ticketweb_url)
    upserted = _make_club(club_id=7)
    mock_show = MagicMock(spec=Show)
    mock_show.club_id = 7

    with patch(_CONFIG_PATCH, return_value="fake_api_key"):
        scraper = TicketmasterNationalScraper(platform_club)

    scraper.fetch_html = AsyncMock(return_value="<p>No more tickets currently available for purchase.</p>")

    with patch.object(scraper._club_handler, "upsert_for_ticketmaster_venue", return_value=upserted):
        with patch(
            "laughtrack.scrapers.implementations.api.ticketmaster_national.scraper.TicketmasterClient"
        ) as MockClient:
            MockClient.return_value.create_show.return_value = mock_show
            shows = await scraper._process_events([event])

    assert len(shows) == 1
    scraper.fetch_html.assert_awaited_once_with(
        ticketweb_url,
        timeout=scraper._REQUEST_TIMEOUT,
        scraper_key="ticketweb",
        direct_js_fallback_on_proxy_error=True,
    )
    create_show_event = MockClient.return_value.create_show.call_args[0][0]
    assert create_show_event["_ticketweb_html"] == "<p>No more tickets currently available for purchase.</p>"


@pytest.mark.asyncio
async def test_attach_ticketweb_html_keeps_event_when_recovery_returns_none(
    platform_club,
):
    ticketweb_url = "https://www.ticketweb.com/event/comedy-night-tickets/12345"
    event = _make_api_event(event_url=ticketweb_url)

    with patch(_CONFIG_PATCH, return_value="fake_api_key"):
        scraper = TicketmasterNationalScraper(platform_club)

    scraper.fetch_html = AsyncMock(return_value=None)

    result = await scraper._attach_ticketweb_html(event)

    assert result is event
    scraper.fetch_html.assert_awaited_once_with(
        ticketweb_url,
        timeout=scraper._REQUEST_TIMEOUT,
        scraper_key="ticketweb",
        direct_js_fallback_on_proxy_error=True,
    )


# ------------------------------------------------------------------ #
# _fetch_window — single-window pagination                            #
# ------------------------------------------------------------------ #

_W_START = datetime(2026, 6, 1)
_W_END = datetime(2026, 6, 11)


@pytest.mark.asyncio
async def test_fetch_window_paginates_until_last_page(platform_club, monkeypatch):
    """Paginator follows totalPages from the API and accumulates events."""
    page0_event = _make_api_event(venue_id="V1", event_id="ev1")
    page1_event = _make_api_event(venue_id="V2", venue_name="Venue 2", event_id="ev2")

    page0_data = {
        "_embedded": {"events": [page0_event]},
        "page": {"number": 0, "size": 200, "totalPages": 2, "totalElements": 2},
    }
    page1_data = {
        "_embedded": {"events": [page1_event]},
        "page": {"number": 1, "size": 200, "totalPages": 2, "totalElements": 2},
    }

    call_count = {"n": 0}

    async def fake_fetch_json(url, **kwargs):
        call_count["n"] += 1
        return page0_data if call_count["n"] == 1 else page1_data

    monkeypatch.setattr(
        "laughtrack.infrastructure.config.config_manager.ConfigManager.get_config",
        lambda *a, **kw: "fake_api_key",
    )

    with patch(_CONFIG_PATCH, return_value="fake_api_key"):
        scraper = TicketmasterNationalScraper(platform_club)
    scraper.fetch_json = fake_fetch_json

    events = await scraper._fetch_window(_W_START, _W_END)

    assert len(events) == 2
    assert call_count["n"] == 2


@pytest.mark.asyncio
async def test_fetch_window_stops_on_empty_embedded(platform_club):
    """Paginator stops when _embedded.events is empty."""
    page0_data = {
        "_embedded": {"events": [_make_api_event()]},
        "page": {"number": 0, "size": 200, "totalPages": 5, "totalElements": 1},
    }
    page1_data = {
        "_embedded": {"events": []},
        "page": {"number": 1, "size": 200, "totalPages": 5, "totalElements": 1},
    }

    call_count = {"n": 0}

    async def fake_fetch_json(url, **kwargs):
        call_count["n"] += 1
        return page0_data if call_count["n"] == 1 else page1_data

    with patch(_CONFIG_PATCH, return_value="fake_api_key"):
        scraper = TicketmasterNationalScraper(platform_club)
    scraper.fetch_json = fake_fetch_json

    events = await scraper._fetch_window(_W_START, _W_END)

    assert len(events) == 1
    assert call_count["n"] == 2


@pytest.mark.asyncio
async def test_fetch_window_stops_on_null_response(platform_club):
    """Paginator stops when fetch_json returns None."""
    with patch(_CONFIG_PATCH, return_value="fake_api_key"):
        scraper = TicketmasterNationalScraper(platform_club)
    scraper.fetch_json = AsyncMock(return_value=None)

    events = await scraper._fetch_window(_W_START, _W_END)

    assert events == []


@pytest.mark.asyncio
async def test_fetch_window_skips_events_without_venues(platform_club):
    """Events with no embedded venue are excluded from results."""
    event_with_venue = _make_api_event()
    event_without_venue = {
        "id": "ev_no_venue",
        "name": "Mystery Show",
        "_embedded": {},
    }

    page_data = {
        "_embedded": {"events": [event_with_venue, event_without_venue]},
        "page": {"number": 0, "size": 200, "totalPages": 1, "totalElements": 2},
    }

    with patch(_CONFIG_PATCH, return_value="fake_api_key"):
        scraper = TicketmasterNationalScraper(platform_club)
    scraper.fetch_json = AsyncMock(return_value=page_data)

    events = await scraper._fetch_window(_W_START, _W_END)

    assert len(events) == 1
    assert events[0]["id"] == "vvG1zZ4M8d8kBJ"


@pytest.mark.asyncio
async def test_fetch_window_respects_deep_paging_cap(platform_club):
    """Never request more than _MAX_PAGES_PER_WINDOW pages, even when the API
    reports many more — this is what keeps requests under the DIS1035 cap
    ((page * size) must be < 1000)."""
    call_count = {"n": 0}

    async def fake_fetch_json(url, **kwargs):
        call_count["n"] += 1
        n = call_count["n"]
        return {
            "_embedded": {"events": [_make_api_event(venue_id=f"V{n}", event_id=f"ev{n}")]},
            # API claims far more pages than the cap allows
            "page": {"number": n - 1, "size": 200, "totalPages": 50, "totalElements": 10000},
        }

    with patch(_CONFIG_PATCH, return_value="fake_api_key"):
        scraper = TicketmasterNationalScraper(platform_club)
    scraper.fetch_json = fake_fetch_json

    events = await scraper._fetch_window(_W_START, _W_END)

    assert call_count["n"] == TicketmasterNationalScraper._MAX_PAGES_PER_WINDOW
    assert len(events) == TicketmasterNationalScraper._MAX_PAGES_PER_WINDOW


# ------------------------------------------------------------------ #
# _fetch_national_comedy_events — date-window sharding + dedup        #
# ------------------------------------------------------------------ #


@pytest.mark.asyncio
async def test_fetch_national_shards_full_horizon(platform_club):
    """The horizon is sharded into (HORIZON_DAYS / WINDOW_DAYS) windows,
    one _fetch_window call each, covering the full booking window."""
    windows_seen = []

    async def fake_window(start, end):
        windows_seen.append((start, end))
        # unique event per window so nothing is deduped away
        return [_make_api_event(venue_id=f"V{len(windows_seen)}", event_id=f"ev{len(windows_seen)}")]

    with patch(_CONFIG_PATCH, return_value="fake_api_key"):
        scraper = TicketmasterNationalScraper(platform_club)
    scraper._fetch_window = fake_window

    events = await scraper._fetch_national_comedy_events()

    expected_windows = TicketmasterNationalScraper._HORIZON_DAYS // TicketmasterNationalScraper._WINDOW_DAYS
    assert len(windows_seen) == expected_windows
    assert len(events) == expected_windows
    # windows are contiguous and non-overlapping
    for (_, prev_end), (next_start, _) in zip(windows_seen, windows_seen[1:]):
        assert prev_end == next_start


@pytest.mark.asyncio
async def test_fetch_national_dedupes_events_across_windows(platform_club):
    """An event appearing in more than one window (boundary overlap) is
    returned only once."""

    async def fake_window(start, end):
        # every window returns the SAME event id
        return [_make_api_event(venue_id="V1", event_id="dup")]

    with patch(_CONFIG_PATCH, return_value="fake_api_key"):
        scraper = TicketmasterNationalScraper(platform_club)
    scraper._fetch_window = fake_window

    events = await scraper._fetch_national_comedy_events()

    assert len(events) == 1
    assert events[0]["id"] == "dup"
