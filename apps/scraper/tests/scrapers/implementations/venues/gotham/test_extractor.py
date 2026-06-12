"""Unit tests for GothamEventExtractor — live feed extraction and enrichment.

Uses the pre-recorded worker feed fixture (worker_feed_page.json) captured
from the live Cloudflare Worker endpoint. Upcoming-event fixture dates use
far-future years (2099) per project convention; the single past item is
intentionally static (2020) because the extractor must always skip it.
"""

import json
import pathlib
from unittest.mock import AsyncMock, MagicMock

import pytest

from laughtrack.core.clients.gotham.models.models import GothamFeedResponse
from laughtrack.scrapers.implementations.venues.gotham.data import GothamPageData
from laughtrack.scrapers.implementations.venues.gotham.extractor import GothamEventExtractor

_FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"


def _load_feed_fixture() -> dict:
    return json.loads((_FIXTURES_DIR / "worker_feed_page.json").read_text(encoding="utf-8"))


def _extractor(session=None) -> GothamEventExtractor:
    mock_club = MagicMock()
    mock_club.name = "Gotham Comedy Club"
    mock_club.as_context.return_value = {}

    async def _get_session(*args, **kwargs):
        return session

    return GothamEventExtractor(mock_club, _get_session)


def _session_returning(json_payload, status_code=200) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_payload
    if status_code >= 400:
        response.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    else:
        response.raise_for_status.return_value = None
    session = MagicMock()
    session.get = AsyncMock(return_value=response)
    return session


def _showclix_data(price="32.00", available=42, sold_out=False) -> MagicMock:
    data = MagicMock()
    data.get_primary_price.return_value = price
    data.get_available_tickets.return_value = available
    data.is_sold_out.return_value = sold_out
    data.event = "The Gotham All-Stars"
    data.venue.venue_name = "Gotham Comedy Club"
    return data


_FEED_URL = "https://square-mountain-7159.alex-cdc.workers.dev/items?limit=100&offset=0"


# ---------------------------------------------------------------------------
# _filter_upcoming
# ---------------------------------------------------------------------------


def test_filter_upcoming_drops_past_and_unparseable_events():
    ext = _extractor()
    feed = GothamFeedResponse.from_dict(_load_feed_fixture())
    upcoming = ext._filter_upcoming(feed.events, _FEED_URL)

    names = [e.name for e in upcoming]
    assert "Long Past Showcase" not in names, "past event must be dropped"
    assert "Show With Malformed Times" not in names, "unparseable start time must be dropped"
    assert len(upcoming) == 3
    assert names.count("The Gotham All-Stars") == 2  # both 2099 showtimes kept


# ---------------------------------------------------------------------------
# extract_events — end-to-end against the fixture page
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_events_returns_upcoming_enriched_events():
    session = _session_returning(_load_feed_fixture())
    ext = _extractor(session=session)
    ext.showclix_client.get_event_data = AsyncMock(return_value=_showclix_data())

    page_data = await ext.extract_events(_FEED_URL)

    assert isinstance(page_data, GothamPageData)
    assert len(page_data.event_list) == 3
    # Each kept event was enriched with Showclix ticket data
    for event in page_data.event_list:
        assert event.price == 32.0
        assert event.inventory == 42
        assert event.sold_out is False


@pytest.mark.asyncio
async def test_extract_events_enriches_each_unique_showclix_event_id():
    session = _session_returning(_load_feed_fixture())
    ext = _extractor(session=session)
    ext.showclix_client.get_event_data = AsyncMock(return_value=_showclix_data())

    await ext.extract_events(_FEED_URL)

    called_ids = {call.args[0] for call in ext.showclix_client.get_event_data.await_args_list}
    # The three upcoming fixture events carry these Showclix event ids
    assert called_ids == {"10378853", "10378852", "10359783"}


@pytest.mark.asyncio
async def test_extract_events_keeps_events_when_enrichment_fails():
    """Enrichment failure must not drop events — to_show still emits a fallback ticket."""
    session = _session_returning(_load_feed_fixture())
    ext = _extractor(session=session)
    ext.showclix_client.get_event_data = AsyncMock(return_value=None)

    page_data = await ext.extract_events(_FEED_URL)

    assert page_data is not None
    assert len(page_data.event_list) == 3
    for event in page_data.event_list:
        assert event.price is None
        assert event.inventory is None


@pytest.mark.asyncio
async def test_extract_events_returns_none_when_no_upcoming_events():
    payload = {
        "items": [],
        "pagination": {"limit": 100, "offset": 100, "total": 8},
    }
    session = _session_returning(payload)
    ext = _extractor(session=session)

    assert await ext.extract_events(_FEED_URL) is None


@pytest.mark.asyncio
async def test_extract_events_propagates_http_errors():
    """A Cloudflare 403 must propagate so the BaseScraper retry layer sees it."""
    session = _session_returning({}, status_code=403)
    ext = _extractor(session=session)

    with pytest.raises(Exception):
        await ext.extract_events(_FEED_URL)


@pytest.mark.asyncio
async def test_extract_events_uses_impersonated_session_with_headers():
    """The fetch must go through the shared (curl_cffi impersonated) session getter."""
    session = _session_returning(_load_feed_fixture())
    ext = _extractor(session=session)
    ext.showclix_client.get_event_data = AsyncMock(return_value=_showclix_data())

    await ext.extract_events(_FEED_URL)

    session.get.assert_awaited_once()
    args, kwargs = session.get.await_args
    assert args[0] == _FEED_URL
    assert "headers" in kwargs and kwargs["headers"], "feed fetch must send venue headers"
