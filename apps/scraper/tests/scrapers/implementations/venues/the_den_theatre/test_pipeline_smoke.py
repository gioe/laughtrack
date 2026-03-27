"""
Pipeline smoke tests for SquarespaceScraper and SquarespaceEvent.

Exercises collect_scraping_targets() (monthly URL generation) → get_data()
(Squarespace GetItemsByMonth API) against mocked responses, and unit-tests the
SquarespaceEvent.to_show() transformation path.
"""

import pytest

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.squarespace import SquarespaceEvent
from laughtrack.scrapers.implementations.venues.the_den_theatre.scraper import SquarespaceScraper
from laughtrack.scrapers.implementations.venues.the_den_theatre.data import SquarespacePageData
from laughtrack.scrapers.implementations.venues.the_den_theatre.extractor import SquarespaceExtractor


BASE_DOMAIN = "https://thedentheatre.com"
COLLECTION_ID = "64bc3c406b6d3d1edd3c84db"
SCRAPING_URL = f"{BASE_DOMAIN}/api/open/GetItemsByMonth?collectionId={COLLECTION_ID}"


def _club() -> Club:
    return Club(
        id=99,
        name="The Den Theatre",
        address="1331 N Milwaukee Ave",
        website=BASE_DOMAIN,
        scraping_url=SCRAPING_URL,
        popularity=0,
        zip_code="60622",
        phone_number="",
        visible=True,
        timezone="America/Chicago",
    )


def _raw_event(
    event_id="abc123",
    title="Comedy Night",
    start_date_ms=1775260800000,  # 2026-04-02T00:00:00Z in ms
    full_url="/calendar/2026/4/2/comedy-night",
    excerpt="<p>A great show.</p>",
) -> dict:
    return {
        "id": event_id,
        "title": title,
        "startDate": start_date_ms,
        "endDate": start_date_ms + 5400000,
        "fullUrl": full_url,
        "excerpt": excerpt,
    }


def _api_response(events: list) -> list:
    """Squarespace GetItemsByMonth returns a JSON array at the root level."""
    return events


# ---------------------------------------------------------------------------
# SquarespaceExtractor tests
# ---------------------------------------------------------------------------


def test_extract_events_returns_events_from_array():
    """extract_events() parses a JSON array into SquarespaceEvent objects."""
    raw = _api_response([
        _raw_event(event_id="1", title="Show A"),
        _raw_event(event_id="2", title="Show B"),
        _raw_event(event_id="3", title="Show C"),
    ])
    events = SquarespaceExtractor.extract_events(raw, BASE_DOMAIN)

    assert len(events) == 3
    titles = {e.title for e in events}
    assert "Show A" in titles
    assert "Show B" in titles
    assert "Show C" in titles


def test_extract_events_returns_empty_list_for_empty_array():
    """extract_events() returns an empty list when the API returns []."""
    events = SquarespaceExtractor.extract_events([], BASE_DOMAIN)
    assert events == []


def test_extract_events_returns_empty_list_for_non_list_response():
    """extract_events() returns an empty list when the response is not a list."""
    events = SquarespaceExtractor.extract_events({}, BASE_DOMAIN)  # type: ignore[arg-type]
    assert events == []


def test_extract_events_skips_events_with_no_title():
    """extract_events() skips events with an empty or missing title."""
    raw = _api_response([
        {**_raw_event(event_id="1"), "title": ""},
        _raw_event(event_id="2", title="Has Title"),
    ])
    events = SquarespaceExtractor.extract_events(raw, BASE_DOMAIN)

    assert len(events) == 1
    assert events[0].title == "Has Title"


def test_extract_events_skips_events_with_no_id():
    """extract_events() skips events with a missing id field."""
    raw = _api_response([
        {**_raw_event(event_id="1"), "id": None},
        _raw_event(event_id="2", title="Has ID"),
    ])
    events = SquarespaceExtractor.extract_events(raw, BASE_DOMAIN)

    assert len(events) == 1
    assert events[0].title == "Has ID"


def test_extract_events_skips_events_with_no_startdate():
    """extract_events() skips events with a missing or non-numeric startDate."""
    raw = _api_response([
        {**_raw_event(event_id="1"), "startDate": None},
        _raw_event(event_id="2", title="Has Date"),
    ])
    events = SquarespaceExtractor.extract_events(raw, BASE_DOMAIN)

    assert len(events) == 1
    assert events[0].title == "Has Date"


def test_extract_events_preserves_full_url():
    """extract_events() correctly captures the fullUrl path."""
    raw = _api_response([_raw_event(event_id="1", full_url="/calendar/2026/4/2/sammy-obeid")])
    events = SquarespaceExtractor.extract_events(raw, BASE_DOMAIN)

    assert len(events) == 1
    assert events[0].full_url == "/calendar/2026/4/2/sammy-obeid"


def test_extract_events_stores_base_domain():
    """extract_events() stores the base_domain on each event."""
    raw = _api_response([_raw_event(event_id="1")])
    events = SquarespaceExtractor.extract_events(raw, BASE_DOMAIN)

    assert len(events) == 1
    assert events[0].base_domain == BASE_DOMAIN


# ---------------------------------------------------------------------------
# SquarespaceEvent.to_show() unit tests
# ---------------------------------------------------------------------------


def _make_event(
    event_id="abc123",
    title="Comedy Night",
    start_date_ms=1775260800000,  # 2026-04-04T00:00:00Z in ms → 2026-04-03T19:00:00-05:00 CDT
    full_url="/calendar/2026/4/2/comedy-night",
    base_domain=BASE_DOMAIN,
    excerpt="",
) -> SquarespaceEvent:
    return SquarespaceEvent(
        id=event_id,
        title=title,
        start_date_ms=start_date_ms,
        full_url=full_url,
        base_domain=base_domain,
        excerpt=excerpt,
    )


def test_to_show_returns_show_with_correct_name():
    """to_show() produces a Show with the event title as the name."""
    event = _make_event(title="Sammy Obeid")
    show = event.to_show(_club())

    assert show is not None
    assert show.name == "Sammy Obeid"


def test_to_show_parses_ms_timestamp_in_chicago_timezone():
    """to_show() correctly converts a ms timestamp to a datetime in Chicago time."""
    # 1775260800000 ms = 2026-04-04T00:00:00Z → 2026-04-03T19:00:00-05:00 (CDT)
    event = _make_event(start_date_ms=1775260800000)
    show = event.to_show(_club())

    assert show is not None
    assert show.date.year == 2026
    assert show.date.month == 4
    assert show.date.day == 3
    assert show.date.hour == 19


def test_to_show_constructs_show_page_url_from_base_domain_and_full_url():
    """to_show() builds show_page_url as base_domain + full_url."""
    event = _make_event(
        base_domain="https://thedentheatre.com",
        full_url="/calendar/2026/4/3/sammy-obeid-the-den-theatre",
    )
    show = event.to_show(_club())

    assert show is not None
    assert show.show_page_url == "https://thedentheatre.com/calendar/2026/4/3/sammy-obeid-the-den-theatre"


def test_to_show_uses_show_page_url_as_ticket_url():
    """to_show() uses the show page URL as the ticket fallback when ticketing_url is absent."""
    event = _make_event(full_url="/calendar/2026/4/3/sammy-obeid-the-den-theatre")
    show = event.to_show(_club())

    assert show is not None
    assert len(show.tickets) == 1
    assert "thedentheatre.com" in show.tickets[0].purchase_url


def test_to_show_uses_ticketing_url_when_set():
    """to_show() uses ticketing_url as the ticket purchase URL when present."""
    event = _make_event(full_url="/calendar/2026/4/3/sammy-obeid-the-den-theatre")
    event.ticketing_url = "https://tickets.thedentheatre.com/event/sammy-obeid"
    show = event.to_show(_club())

    assert show is not None
    assert len(show.tickets) == 1
    assert show.tickets[0].purchase_url == "https://tickets.thedentheatre.com/event/sammy-obeid"


def test_to_show_falls_back_to_show_page_url_when_ticketing_url_empty():
    """to_show() falls back to show_page_url when ticketing_url is empty string."""
    event = _make_event(
        full_url="/calendar/2026/4/3/sammy-obeid-the-den-theatre",
        base_domain=BASE_DOMAIN,
    )
    event.ticketing_url = ""
    show = event.to_show(_club())

    assert show is not None
    assert show.tickets[0].purchase_url == f"{BASE_DOMAIN}/calendar/2026/4/3/sammy-obeid-the-den-theatre"


def test_to_show_strips_html_from_excerpt():
    """to_show() strips HTML tags from excerpt for the show description."""
    event = _make_event(excerpt="<p>A great <b>show</b>.</p>")
    show = event.to_show(_club())

    assert show is not None
    assert show.description == "A great show."


def test_to_show_returns_none_for_invalid_timezone():
    """to_show() returns None when the club timezone cannot be parsed."""
    club = _club()
    club.timezone = "Not/A/Timezone"
    event = _make_event()
    show = event.to_show(club)

    assert show is None


def test_to_show_with_url_override():
    """to_show() uses the url argument instead of base_domain + full_url when provided."""
    event = _make_event()
    show = event.to_show(_club(), url="https://example.com/custom-url")

    assert show is not None
    assert show.show_page_url == "https://example.com/custom-url"


# ---------------------------------------------------------------------------
# collect_scraping_targets() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_three_urls():
    """collect_scraping_targets() returns exactly three monthly URLs."""
    scraper = SquarespaceScraper(_club())
    targets = await scraper.collect_scraping_targets()

    assert len(targets) == 3


@pytest.mark.asyncio
async def test_collect_scraping_targets_urls_contain_collection_id():
    """collect_scraping_targets() URLs include the correct collectionId."""
    scraper = SquarespaceScraper(_club())
    targets = await scraper.collect_scraping_targets()

    for url in targets:
        assert COLLECTION_ID in url, f"Expected collectionId in {url}"


@pytest.mark.asyncio
async def test_collect_scraping_targets_urls_contain_month_param():
    """collect_scraping_targets() URLs include a month= query parameter."""
    scraper = SquarespaceScraper(_club())
    targets = await scraper.collect_scraping_targets()

    for url in targets:
        assert "month=" in url, f"Expected month= param in {url}"


@pytest.mark.asyncio
async def test_collect_scraping_targets_urls_use_correct_base_domain():
    """collect_scraping_targets() uses the base domain extracted from scraping_url."""
    scraper = SquarespaceScraper(_club())
    targets = await scraper.collect_scraping_targets()

    for url in targets:
        assert url.startswith(BASE_DOMAIN), f"Expected URL to start with {BASE_DOMAIN}, got {url}"


@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_three_distinct_months():
    """collect_scraping_targets() returns three URLs with distinct month values.

    Guards against off-by-one regressions in the (today.month + i - 1) % 12 + 1
    formula that would produce duplicate month values (e.g. [03-2026, 03-2026, 04-2026]).
    """
    scraper = SquarespaceScraper(_club())
    targets = await scraper.collect_scraping_targets()

    assert len(set(targets)) == 3, (
        f"Expected 3 distinct URLs (one per month), got duplicates: {targets}"
    )


# ---------------------------------------------------------------------------
# get_data() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_events(monkeypatch):
    """get_data() fetches the Squarespace API and returns SquarespacePageData."""
    scraper = SquarespaceScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs):
        return _api_response([
            _raw_event(event_id="1", title="Show A"),
            _raw_event(event_id="2", title="Show B"),
        ])

    monkeypatch.setattr(SquarespaceScraper, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", lambda url: __import__("asyncio").sleep(0))

    result = await scraper.get_data(
        f"{BASE_DOMAIN}/api/open/GetItemsByMonth?month=04-2026&collectionId={COLLECTION_ID}"
    )

    assert isinstance(result, SquarespacePageData)
    assert len(result.event_list) == 2
    titles = {e.title for e in result.event_list}
    assert "Show A" in titles
    assert "Show B" in titles


@pytest.mark.asyncio
async def test_get_data_returns_none_when_all_events_malformed(monkeypatch):
    """get_data() returns None when the API returns events but all fail extraction.

    Covers the branch where fetch_json returns a non-empty array but
    SquarespaceExtractor.extract_events() yields [] (e.g. all items missing id/title/startDate).
    """
    scraper = SquarespaceScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs):
        return [_raw_event()]  # non-empty array

    monkeypatch.setattr(SquarespaceScraper, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(SquarespaceExtractor, "extract_events", staticmethod(lambda resp, domain: []))
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", lambda url: __import__("asyncio").sleep(0))

    result = await scraper.get_data(
        f"{BASE_DOMAIN}/api/open/GetItemsByMonth?month=04-2026&collectionId={COLLECTION_ID}"
    )
    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_on_empty_array(monkeypatch):
    """get_data() returns None when the API returns an empty array."""
    scraper = SquarespaceScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs):
        return []

    monkeypatch.setattr(SquarespaceScraper, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", lambda url: __import__("asyncio").sleep(0))

    result = await scraper.get_data(
        f"{BASE_DOMAIN}/api/open/GetItemsByMonth?month=04-2026&collectionId={COLLECTION_ID}"
    )
    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_on_null_response(monkeypatch):
    """get_data() returns None when fetch_json returns None."""
    scraper = SquarespaceScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs):
        return None

    monkeypatch.setattr(SquarespaceScraper, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", lambda url: __import__("asyncio").sleep(0))

    result = await scraper.get_data(
        f"{BASE_DOMAIN}/api/open/GetItemsByMonth?month=04-2026&collectionId={COLLECTION_ID}"
    )
    assert result is None


# ---------------------------------------------------------------------------
# _enrich_with_ticket_urls() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_enrich_with_ticket_urls_sets_ticketing_url_from_top_level(monkeypatch):
    """_enrich_with_ticket_urls() populates ticketing_url from top-level ticketingUrl."""
    scraper = SquarespaceScraper(_club())
    event = _make_event(full_url="/calendar/2026/4/3/sammy-obeid")

    async def fake_fetch_json(self, url: str, **kwargs):
        return {"ticketingUrl": "https://tickets.thedentheatre.com/event/sammy-obeid"}

    monkeypatch.setattr(SquarespaceScraper, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", lambda url: __import__("asyncio").sleep(0))

    await scraper._enrich_with_ticket_urls([event])

    assert event.ticketing_url == "https://tickets.thedentheatre.com/event/sammy-obeid"


@pytest.mark.asyncio
async def test_enrich_with_ticket_urls_sets_ticketing_url_from_item_key(monkeypatch):
    """_enrich_with_ticket_urls() populates ticketing_url from item-nested ticketingUrl."""
    scraper = SquarespaceScraper(_club())
    event = _make_event(full_url="/calendar/2026/4/3/sammy-obeid")

    async def fake_fetch_json(self, url: str, **kwargs):
        return {"item": {"ticketingUrl": "https://tickets.thedentheatre.com/event/sammy-obeid"}}

    monkeypatch.setattr(SquarespaceScraper, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", lambda url: __import__("asyncio").sleep(0))

    await scraper._enrich_with_ticket_urls([event])

    assert event.ticketing_url == "https://tickets.thedentheatre.com/event/sammy-obeid"


@pytest.mark.asyncio
async def test_enrich_with_ticket_urls_leaves_ticketing_url_empty_when_absent(monkeypatch):
    """_enrich_with_ticket_urls() leaves ticketing_url empty when detail page has no ticketingUrl."""
    scraper = SquarespaceScraper(_club())
    event = _make_event(full_url="/calendar/2026/4/3/sammy-obeid")

    async def fake_fetch_json(self, url: str, **kwargs):
        return {"id": "abc123", "title": "Sammy Obeid"}  # no ticketingUrl

    monkeypatch.setattr(SquarespaceScraper, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", lambda url: __import__("asyncio").sleep(0))

    await scraper._enrich_with_ticket_urls([event])

    assert event.ticketing_url == ""


@pytest.mark.asyncio
async def test_enrich_with_ticket_urls_skips_events_with_no_full_url(monkeypatch):
    """_enrich_with_ticket_urls() skips events with an empty full_url."""
    scraper = SquarespaceScraper(_club())
    event = _make_event(full_url="")

    fetch_called = []

    async def fake_fetch_json(self, url: str, **kwargs):
        fetch_called.append(url)
        return {"ticketingUrl": "https://tickets.thedentheatre.com/event/x"}

    monkeypatch.setattr(SquarespaceScraper, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", lambda url: __import__("asyncio").sleep(0))

    await scraper._enrich_with_ticket_urls([event])

    assert fetch_called == []
    assert event.ticketing_url == ""


@pytest.mark.asyncio
async def test_enrich_with_ticket_urls_survives_fetch_error(monkeypatch):
    """_enrich_with_ticket_urls() continues gracefully when a detail fetch raises."""
    scraper = SquarespaceScraper(_club())
    event = _make_event(full_url="/calendar/2026/4/3/sammy-obeid")

    async def fake_fetch_json(self, url: str, **kwargs):
        raise RuntimeError("connection error")

    monkeypatch.setattr(SquarespaceScraper, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", lambda url: __import__("asyncio").sleep(0))

    await scraper._enrich_with_ticket_urls([event])  # must not raise

    assert event.ticketing_url == ""


@pytest.mark.asyncio
async def test_get_data_enriches_events_with_vivenu_ticket_url(monkeypatch):
    """get_data() enriches events with ticketing_url from per-event detail pages."""
    scraper = SquarespaceScraper(_club())

    VIVENU_URL = "https://tickets.thedentheatre.com/event/sammy-obeid"

    async def fake_fetch_json(self, url: str, **kwargs):
        if "GetItemsByMonth" in url:
            return _api_response([_raw_event(event_id="1", title="Sammy Obeid")])
        # detail page fetch
        return {"ticketingUrl": VIVENU_URL}

    monkeypatch.setattr(SquarespaceScraper, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", lambda url: __import__("asyncio").sleep(0))

    result = await scraper.get_data(
        f"{BASE_DOMAIN}/api/open/GetItemsByMonth?month=04-2026&collectionId={COLLECTION_ID}"
    )

    assert isinstance(result, SquarespacePageData)
    assert len(result.event_list) == 1
    assert result.event_list[0].ticketing_url == VIVENU_URL


# ---------------------------------------------------------------------------
# Full pipeline smoke test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_pipeline_transformation_produces_shows(monkeypatch):
    """Full pipeline: SquarespacePageData → transformation_pipeline → Show objects."""
    scraper = SquarespaceScraper(_club())

    fake_event = _make_event(title="Sammy Obeid", start_date_ms=1775260800000)

    monkeypatch.setattr(
        SquarespaceExtractor,
        "extract_events",
        staticmethod(lambda resp, domain: [fake_event]),
    )

    async def fake_fetch_json(self, url: str, **kwargs):
        return [_raw_event()]  # content doesn't matter; extractor is mocked

    monkeypatch.setattr(SquarespaceScraper, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", lambda url: __import__("asyncio").sleep(0))

    page_data = await scraper.get_data(
        f"{BASE_DOMAIN}/api/open/GetItemsByMonth?month=04-2026&collectionId={COLLECTION_ID}"
    )

    assert isinstance(page_data, SquarespacePageData)
    shows = scraper.transformation_pipeline.transform(page_data)
    assert len(shows) > 0, (
        "transformation_pipeline.transform() returned 0 Shows — "
        "check SquarespaceEventTransformer.can_transform() and that the transformer "
        "is registered with the correct generic type"
    )
    assert shows[0].name == "Sammy Obeid"
