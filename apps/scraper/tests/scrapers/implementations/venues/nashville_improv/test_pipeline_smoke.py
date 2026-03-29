"""
Pipeline smoke tests for Nashville Improv (Squarespace scraper).

Nashville Improv uses the generic SquarespaceScraper with:
  collectionId: 69af0d8e38f8403f319d32d8
  timezone: America/Chicago
  website: https://www.nashvilleimprov.com
"""

import pytest

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.squarespace import SquarespaceEvent
from laughtrack.scrapers.implementations.venues.the_den_theatre.scraper import SquarespaceScraper
from laughtrack.scrapers.implementations.venues.the_den_theatre.data import SquarespacePageData
from laughtrack.scrapers.implementations.venues.the_den_theatre.extractor import SquarespaceExtractor


BASE_DOMAIN = "https://www.nashvilleimprov.com"
COLLECTION_ID = "69af0d8e38f8403f319d32d8"
SCRAPING_URL = f"{BASE_DOMAIN}/api/open/GetItemsByMonth?collectionId={COLLECTION_ID}"


def _club() -> Club:
    return Club(
        id=99,
        name="Nashville Improv",
        address="2007 Belmont Blvd",
        website=BASE_DOMAIN,
        scraping_url=SCRAPING_URL,
        popularity=0,
        zip_code="37203",
        phone_number="",
        visible=True,
        timezone="America/Chicago",
    )


def _raw_event(
    event_id="abc123",
    title="Nashville Improv Show",
    start_date_ms=1775260800000,  # 2026-04-04T00:00:00Z → 2026-04-03T19:00:00 CDT
    full_url="/shows/nashville-improv-show",
    excerpt="<p>Live improv comedy.</p>",
) -> dict:
    return {
        "id": event_id,
        "title": title,
        "startDate": start_date_ms,
        "endDate": start_date_ms + 5400000,
        "fullUrl": full_url,
        "excerpt": excerpt,
    }


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
    """collect_scraping_targets() URLs include Nashville Improv's collectionId."""
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
async def test_collect_scraping_targets_returns_three_distinct_months():
    """collect_scraping_targets() returns three URLs with distinct month values.

    Guards against off-by-one regressions in the (today.month + i - 1) % 12 + 1
    formula that would produce duplicate month values.
    """
    scraper = SquarespaceScraper(_club())
    targets = await scraper.collect_scraping_targets()

    assert len(set(targets)) == 3, (
        f"Expected 3 distinct URLs (one per month), got duplicates: {targets}"
    )


@pytest.mark.asyncio
async def test_collect_scraping_targets_urls_use_nashvilleimprov_domain():
    """collect_scraping_targets() uses nashvilleimprov.com as the base domain."""
    scraper = SquarespaceScraper(_club())
    targets = await scraper.collect_scraping_targets()

    for url in targets:
        assert url.startswith(BASE_DOMAIN), f"Expected URL to start with {BASE_DOMAIN}, got {url}"


# ---------------------------------------------------------------------------
# get_data() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_events(monkeypatch):
    """get_data() fetches the Squarespace API and returns SquarespacePageData."""
    scraper = SquarespaceScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs):
        return [
            _raw_event(event_id="1", title="Your Musical!"),
            _raw_event(event_id="2", title="Harold Night"),
        ]

    async def noop_enrich(self, events):
        pass

    monkeypatch.setattr(SquarespaceScraper, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(SquarespaceScraper, "_enrich_with_ticket_urls", noop_enrich)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", lambda url: __import__("asyncio").sleep(0))

    result = await scraper.get_data(
        f"{BASE_DOMAIN}/api/open/GetItemsByMonth?month=04-2026&collectionId={COLLECTION_ID}"
    )

    assert isinstance(result, SquarespacePageData)
    assert len(result.event_list) == 2
    titles = {e.title for e in result.event_list}
    assert "Your Musical!" in titles
    assert "Harold Night" in titles


# ---------------------------------------------------------------------------
# Full pipeline smoke test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_pipeline_transformation_produces_shows(monkeypatch):
    """Full pipeline: SquarespacePageData → transformation_pipeline → Show objects."""
    scraper = SquarespaceScraper(_club())

    fake_event = SquarespaceEvent(
        id="abc123",
        title="Nashville Improv presents YOUR Musical!",
        start_date_ms=1775260800000,  # 2026-04-03T19:00:00 CDT
        full_url="/shows/nashville-improv-presents-your-musical",
        base_domain=BASE_DOMAIN,
        excerpt="",
    )

    monkeypatch.setattr(
        SquarespaceExtractor,
        "extract_events",
        staticmethod(lambda resp, domain: [fake_event]),
    )

    async def fake_fetch_json(self, url: str, **kwargs):
        return [_raw_event()]

    async def noop_enrich(self, events):
        pass

    monkeypatch.setattr(SquarespaceScraper, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(SquarespaceScraper, "_enrich_with_ticket_urls", noop_enrich)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", lambda url: __import__("asyncio").sleep(0))

    page_data = await scraper.get_data(
        f"{BASE_DOMAIN}/api/open/GetItemsByMonth?month=04-2026&collectionId={COLLECTION_ID}"
    )

    assert isinstance(page_data, SquarespacePageData)
    shows = scraper.transformation_pipeline.transform(page_data)
    assert len(shows) > 0, (
        "transformation_pipeline.transform() returned 0 Shows — "
        "check SquarespaceEventTransformer and Club timezone"
    )
    assert shows[0].name == "Nashville Improv presents YOUR Musical!"


@pytest.mark.asyncio
async def test_show_page_url_uses_nashvilleimprov_domain(monkeypatch):
    """Shows produced by the pipeline have a show_page_url on nashvilleimprov.com."""
    scraper = SquarespaceScraper(_club())

    fake_event = SquarespaceEvent(
        id="abc123",
        title="Harold Night",
        start_date_ms=1775260800000,
        full_url="/shows/harold-night",
        base_domain=BASE_DOMAIN,
        excerpt="",
    )

    monkeypatch.setattr(
        SquarespaceExtractor,
        "extract_events",
        staticmethod(lambda resp, domain: [fake_event]),
    )

    async def fake_fetch_json(self, url: str, **kwargs):
        return [_raw_event()]

    async def noop_enrich(self, events):
        pass

    monkeypatch.setattr(SquarespaceScraper, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(SquarespaceScraper, "_enrich_with_ticket_urls", noop_enrich)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", lambda url: __import__("asyncio").sleep(0))

    page_data = await scraper.get_data(
        f"{BASE_DOMAIN}/api/open/GetItemsByMonth?month=04-2026&collectionId={COLLECTION_ID}"
    )
    shows = scraper.transformation_pipeline.transform(page_data)

    assert len(shows) > 0
    assert shows[0].show_page_url.startswith(BASE_DOMAIN), (
        f"Expected show_page_url to start with {BASE_DOMAIN}, got {shows[0].show_page_url}"
    )
