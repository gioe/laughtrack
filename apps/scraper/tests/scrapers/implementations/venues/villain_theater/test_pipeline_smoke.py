"""
Pipeline smoke tests for Villain Theater (Squarespace scraper).

Villain Theater uses the generic SquarespaceScraper with:
  collectionId: 5b99c27d1ae6cfe40edce851
  timezone: America/New_York
  website: https://www.villaintheater.com
"""

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.squarespace import SquarespaceEvent
from laughtrack.scrapers.implementations.api.squarespace.scraper import SquarespaceScraper
from laughtrack.scrapers.implementations.api.squarespace.data import SquarespacePageData
from laughtrack.scrapers.implementations.api.squarespace.extractor import SquarespaceExtractor


BASE_DOMAIN = "https://www.villaintheater.com"
COLLECTION_ID = "5b99c27d1ae6cfe40edce851"
SCRAPING_URL = f"{BASE_DOMAIN}/api/open/GetItemsByMonth?collectionId={COLLECTION_ID}"


def _club() -> Club:
    _c = Club(id=99, name='Villain Theater', address='5865 NE 2nd Avenue', website=BASE_DOMAIN, popularity=0, zip_code='33137', phone_number='', visible=True, timezone='America/New_York')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url=SCRAPING_URL, external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _raw_event(
    event_id="abc123",
    title="Saturday Gigantic Improv Comedy Show",
    start_date_ms=1775260800000,  # 2026-04-03T20:00:00 EDT
    full_url="/all-shows/sg040426",
    excerpt="<p>The best improv comedy show in Miami.</p>",
) -> dict:
    return {
        "id": event_id,
        "title": title,
        "startDate": start_date_ms,
        "endDate": start_date_ms + 7200000,
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
    """collect_scraping_targets() URLs include Villain Theater's collectionId."""
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
    """collect_scraping_targets() returns three URLs with distinct month values."""
    scraper = SquarespaceScraper(_club())
    targets = await scraper.collect_scraping_targets()

    assert len(set(targets)) == 3, (
        f"Expected 3 distinct URLs (one per month), got duplicates: {targets}"
    )


@pytest.mark.asyncio
async def test_collect_scraping_targets_urls_use_villain_theater_domain():
    """collect_scraping_targets() uses villaintheater.com as the base domain."""
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
            _raw_event(event_id="1", title="Saturday Gigantic Improv Comedy Show"),
            _raw_event(event_id="2", title="Tuesday Improv Comedy Show"),
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
    assert "Saturday Gigantic Improv Comedy Show" in titles
    assert "Tuesday Improv Comedy Show" in titles


# ---------------------------------------------------------------------------
# Full pipeline smoke test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_pipeline_transformation_produces_shows(monkeypatch):
    """Full pipeline: SquarespacePageData → transformation_pipeline → Show objects."""
    scraper = SquarespaceScraper(_club())

    fake_event = SquarespaceEvent(
        id="abc123",
        title="Saturday Gigantic Improv Comedy Show",
        start_date_ms=1775260800000,  # 2026-04-03T20:00:00 EDT
        full_url="/all-shows/sg040426",
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
    assert shows[0].name == "Saturday Gigantic Improv Comedy Show"


@pytest.mark.asyncio
async def test_show_page_url_uses_villain_theater_domain(monkeypatch):
    """Shows produced by the pipeline have a show_page_url on villaintheater.com."""
    scraper = SquarespaceScraper(_club())

    fake_event = SquarespaceEvent(
        id="abc123",
        title="Saturday Gigantic Improv Comedy Show",
        start_date_ms=1775260800000,
        full_url="/all-shows/sg040426",
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
