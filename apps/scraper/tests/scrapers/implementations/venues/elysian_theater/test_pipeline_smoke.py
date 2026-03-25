"""
Pipeline smoke tests for ElysianTheaterScraper and ElysianEvent.

Exercises get_data() against mocked Squarespace GetItemsByMonth API responses
matching the actual elysiantheater.com structure, and unit-tests the
ElysianEvent.to_show() transformation path.
"""

import pytest

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.elysian import ElysianEvent
from laughtrack.scrapers.implementations.venues.elysian_theater.scraper import ElysianTheaterScraper
from laughtrack.scrapers.implementations.venues.elysian_theater.data import ElysianPageData
from laughtrack.scrapers.implementations.venues.elysian_theater.extractor import ElysianEventExtractor

API_BASE_URL = "https://www.elysiantheater.com/api/open/GetItemsByMonth"
COLLECTION_ID = "613af44feffe2b7f78a46b63"


def _club() -> Club:
    return Club(
        id=300,
        name="The Elysian Theater",
        address="1944 Riverside Drive",
        website="https://www.elysiantheater.com",
        scraping_url=API_BASE_URL,
        popularity=0,
        zip_code="90039",
        phone_number="",
        visible=True,
        timezone="America/Los_Angeles",
    )


def _raw_event(
    id_="abc123",
    title="Spots Open Mic",
    start_date_ms=1743559200000,  # 2025-04-01 19:00:00 UTC (approx 12 PM LA)
    full_url="/shows/spots0401",
    excerpt="<p>FEATURING Solomon Giorgio, Zack Poitras.</p>",
    workflow_state=1,
) -> dict:
    return {
        "id": id_,
        "title": title,
        "startDate": start_date_ms,
        "endDate": start_date_ms + 7200000,
        "fullUrl": full_url,
        "excerpt": excerpt,
        "urlId": full_url.split("/")[-1],
        "workflowState": workflow_state,
    }


# ---------------------------------------------------------------------------
# ElysianEventExtractor tests
# ---------------------------------------------------------------------------


def test_extract_events_returns_events_from_list():
    """extract_events() parses a list of raw event dicts into ElysianEvent objects."""
    raw = [
        _raw_event(id_="1", title="Show A"),
        _raw_event(id_="2", title="Show B"),
        _raw_event(id_="3", title="Show C"),
    ]
    events = ElysianEventExtractor.extract_events(raw)

    assert len(events) == 3
    titles = {e.title for e in events}
    assert "Show A" in titles
    assert "Show B" in titles
    assert "Show C" in titles


def test_extract_events_returns_empty_list_for_empty_input():
    """extract_events() returns an empty list when given an empty array."""
    events = ElysianEventExtractor.extract_events([])
    assert events == []


def test_extract_events_skips_non_published_events():
    """extract_events() filters out events where workflowState != 1."""
    raw = [
        _raw_event(id_="1", title="Published", workflow_state=1),
        _raw_event(id_="2", title="Draft", workflow_state=0),
        _raw_event(id_="3", title="Scheduled", workflow_state=2),
    ]
    events = ElysianEventExtractor.extract_events(raw)

    assert len(events) == 1
    assert events[0].title == "Published"


def test_extract_events_skips_events_with_no_start_date():
    """extract_events() skips events missing startDate."""
    raw = [
        {"id": "1", "title": "No Date", "startDate": None, "fullUrl": "/shows/x", "workflowState": 1},
        _raw_event(id_="2", title="Has Date"),
    ]
    events = ElysianEventExtractor.extract_events(raw)

    assert len(events) == 1
    assert events[0].title == "Has Date"


def test_extract_events_skips_events_with_no_title():
    """extract_events() skips events missing a title."""
    raw = [
        {"id": "1", "title": "", "startDate": 1743559200000, "fullUrl": "/shows/x", "workflowState": 1},
        _raw_event(id_="2", title="Has Title"),
    ]
    events = ElysianEventExtractor.extract_events(raw)

    assert len(events) == 1
    assert events[0].title == "Has Title"


def test_extract_events_unescapes_html_entities_in_title():
    """extract_events() unescapes HTML entities in event titles."""
    raw = [_raw_event(id_="1", title="Open Mic &amp; Friends")]
    events = ElysianEventExtractor.extract_events(raw)

    assert len(events) == 1
    assert events[0].title == "Open Mic & Friends"


# ---------------------------------------------------------------------------
# ElysianEvent.to_show() unit tests
# ---------------------------------------------------------------------------


def _make_event(
    title="Spots Open Mic",
    start_date_ms=1743559200000,
    full_url="/shows/spots0401",
    excerpt="<p>FEATURING Solomon Giorgio.</p>",
) -> ElysianEvent:
    return ElysianEvent(
        id="abc123",
        title=title,
        start_date_ms=start_date_ms,
        full_url=full_url,
        excerpt=excerpt,
    )


def test_to_show_returns_show_with_correct_name():
    """to_show() produces a Show with the correct name."""
    event = _make_event(title="Valencia Grace Live")
    show = event.to_show(_club())

    assert show is not None
    assert show.name == "Valencia Grace Live"


def test_to_show_converts_ms_timestamp_to_la_timezone():
    """to_show() converts Unix ms timestamp to America/Los_Angeles datetime."""
    # 1743541200000 ms = 2025-04-01 21:00:00 UTC = 2025-04-01 14:00:00 PDT (UTC-7)
    event = _make_event(start_date_ms=1743541200000)
    show = event.to_show(_club())

    assert show is not None
    assert show.date.year == 2025
    assert show.date.month == 4
    assert show.date.day == 1
    assert show.date.hour == 14


def test_to_show_builds_show_page_url_from_full_url():
    """to_show() constructs the show page URL as base domain + full_url."""
    event = _make_event(full_url="/shows/spots0401")
    show = event.to_show(_club())

    assert show is not None
    assert show.show_page_url == "https://www.elysiantheater.com/shows/spots0401"


def test_to_show_creates_fallback_ticket_pointing_to_show_page():
    """to_show() creates a fallback ticket pointing to the show page URL."""
    event = _make_event(full_url="/shows/spots0401")
    show = event.to_show(_club())

    assert show is not None
    assert len(show.tickets) == 1
    assert "elysiantheater.com" in show.tickets[0].purchase_url


def test_to_show_strips_html_from_excerpt_for_description():
    """to_show() strips HTML tags from excerpt and uses result as description."""
    event = _make_event(excerpt="<p>FEATURING Solomon Giorgio, Zack Poitras.</p>")
    show = event.to_show(_club())

    assert show is not None
    assert show.description is not None
    assert "<p>" not in show.description
    assert "Solomon Giorgio" in show.description


def test_to_show_returns_none_for_invalid_timestamp():
    """to_show() returns None when start_date_ms is not a valid timestamp."""
    event = _make_event(start_date_ms=-999999999999999)
    # Extremely out-of-range timestamp should raise on fromtimestamp
    # Use 0 but mock an exception scenario instead — test with a non-numeric value via subclass
    # Actually, test with a very negative timestamp that causes OSError on some platforms
    # For reliability, patch the conversion step:
    import unittest.mock as mock
    with mock.patch("laughtrack.core.entities.event.elysian.datetime") as mock_dt:
        mock_dt.fromtimestamp.side_effect = OSError("out of range")
        show = event.to_show(_club())
    assert show is None


def test_to_show_empty_excerpt_gives_none_description():
    """to_show() sets description to None when excerpt is empty."""
    event = _make_event(excerpt="")
    show = event.to_show(_club())

    assert show is not None
    assert show.description is None


# ---------------------------------------------------------------------------
# collect_scraping_targets() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_correct_number_of_urls():
    """collect_scraping_targets() returns current month + _MONTHS_AHEAD URLs (4 total)."""
    scraper = ElysianTheaterScraper(_club())
    targets = await scraper.collect_scraping_targets()

    assert len(targets) == 4  # current + 3 months ahead


@pytest.mark.asyncio
async def test_collect_scraping_targets_includes_collection_id():
    """collect_scraping_targets() includes the collection ID in each URL."""
    scraper = ElysianTheaterScraper(_club())
    targets = await scraper.collect_scraping_targets()

    for url in targets:
        assert "613af44feffe2b7f78a46b63" in url


@pytest.mark.asyncio
async def test_collect_scraping_targets_uses_club_scraping_url_as_base():
    """collect_scraping_targets() uses club.scraping_url as the base URL."""
    scraper = ElysianTheaterScraper(_club())
    targets = await scraper.collect_scraping_targets()

    for url in targets:
        assert url.startswith(API_BASE_URL)


@pytest.mark.asyncio
async def test_collect_scraping_targets_month_format():
    """collect_scraping_targets() formats months as MM-YYYY."""
    import re as _re
    scraper = ElysianTheaterScraper(_club())
    targets = await scraper.collect_scraping_targets()

    month_pattern = _re.compile(r"month=\d{2}-\d{4}")
    for url in targets:
        assert month_pattern.search(url), f"Month param not found or wrong format in: {url}"


# ---------------------------------------------------------------------------
# get_data() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_events(monkeypatch):
    """get_data() parses the API JSON array and returns ElysianPageData with events."""
    scraper = ElysianTheaterScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs):
        return [
            _raw_event(id_="1", title="Show A"),
            _raw_event(id_="2", title="Show B"),
        ]

    async def fake_await_if_needed(self, url: str):
        pass

    monkeypatch.setattr(ElysianTheaterScraper, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", lambda url: __import__("asyncio").sleep(0))

    result = await scraper.get_data(f"{API_BASE_URL}?month=04-2026&collectionId={COLLECTION_ID}")

    assert isinstance(result, ElysianPageData)
    assert len(result.event_list) == 2
    titles = {e.title for e in result.event_list}
    assert "Show A" in titles
    assert "Show B" in titles


@pytest.mark.asyncio
async def test_get_data_returns_none_on_empty_list(monkeypatch):
    """get_data() returns None when the API returns an empty array."""
    scraper = ElysianTheaterScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs):
        return []

    monkeypatch.setattr(ElysianTheaterScraper, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", lambda url: __import__("asyncio").sleep(0))

    result = await scraper.get_data(f"{API_BASE_URL}?month=04-2026&collectionId={COLLECTION_ID}")
    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_on_null_response(monkeypatch):
    """get_data() returns None when fetch_json returns None."""
    scraper = ElysianTheaterScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs):
        return None

    monkeypatch.setattr(ElysianTheaterScraper, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", lambda url: __import__("asyncio").sleep(0))

    result = await scraper.get_data(f"{API_BASE_URL}?month=04-2026&collectionId={COLLECTION_ID}")
    assert result is None


@pytest.mark.asyncio
async def test_get_data_filters_unpublished_events(monkeypatch):
    """get_data() only returns published events (workflowState == 1)."""
    scraper = ElysianTheaterScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs):
        return [
            _raw_event(id_="1", title="Published", workflow_state=1),
            _raw_event(id_="2", title="Draft", workflow_state=0),
        ]

    monkeypatch.setattr(ElysianTheaterScraper, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", lambda url: __import__("asyncio").sleep(0))

    result = await scraper.get_data(f"{API_BASE_URL}?month=04-2026&collectionId={COLLECTION_ID}")

    assert result is not None
    assert len(result.event_list) == 1
    assert result.event_list[0].title == "Published"
