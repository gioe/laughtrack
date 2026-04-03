"""
Pipeline smoke tests for the generic TixrScraper.

Exercises TixrExtractor, collect_scraping_targets(), and get_data() against
mocked HTML and a mocked TixrClient. Verifies that both short-form and
long-form Tixr URLs are extracted and resolved to TixrEvents.
"""

import importlib.util
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.tixr import TixrEvent
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.scrapers.implementations.api.tixr.scraper import TixrScraper
from laughtrack.scrapers.implementations.api.tixr.page_data import TixrPageData
from laughtrack.scrapers.implementations.api.tixr.extractor import TixrExtractor

CALENDAR_URL = "https://www.hahacomedyclub.com/calendar"


def _club(scraping_url: str = CALENDAR_URL) -> Club:
    return Club(
        id=999,
        name="Test Tixr Venue",
        address="123 Main St",
        website="https://example.com",
        scraping_url=scraping_url,
        popularity=0,
        zip_code="90001",
        phone_number="",
        visible=True,
        timezone="America/Los_Angeles",
    )


def _make_tixr_event(event_id: str, title: str) -> TixrEvent:
    show = Show(
        name=title,
        club_id=999,
        date=datetime(2026, 4, 1, 20, 0, tzinfo=timezone.utc),
        show_page_url=f"https://tixr.com/e/{event_id}",
        lineup=[],
        tickets=[
            Ticket(
                price=0.0,
                purchase_url=f"https://tixr.com/e/{event_id}",
                sold_out=False,
                type="General Admission",
            )
        ],
        supplied_tags=["event"],
        description=None,
        timezone=None,
        room="",
    )
    return TixrEvent.from_tixr_show(
        show=show, source_url=f"https://tixr.com/e/{event_id}", event_id=event_id
    )


def _calendar_html_short(tixr_ids: list) -> str:
    """Calendar page with short-form tixr.com/e/{id} links."""
    links = "".join(
        f'<a href="https://tixr.com/e/{id}" class="buy-tickets-btn">Buy Tickets</a>'
        for id in tixr_ids
    )
    return f"<html><body><div class='calendar'>{links}</div></body></html>"


def _calendar_html_long(slugs: list) -> str:
    """Calendar page with long-form tixr.com/groups/*/events/* links."""
    links = "".join(
        f'<a href="{slug}">Buy Tickets</a>' for slug in slugs
    )
    return f"<html><body><div class='calendar'>{links}</div></body></html>"


# ---------------------------------------------------------------------------
# TixrExtractor unit tests
# ---------------------------------------------------------------------------


def test_extractor_finds_short_form_urls():
    """extract_tixr_urls() picks up tixr.com/e/{id} links."""
    html = _calendar_html_short(["177558", "176996", "175370"])
    urls = TixrExtractor.extract_tixr_urls(html)
    assert urls == [
        "https://tixr.com/e/177558",
        "https://tixr.com/e/176996",
        "https://tixr.com/e/175370",
    ]


def test_extractor_finds_long_form_urls():
    """extract_tixr_urls() picks up tixr.com/groups/*/events/* links."""
    long_url = "https://www.tixr.com/groups/thestand/events/comedy-show-123456"
    html = _calendar_html_long([long_url])
    urls = TixrExtractor.extract_tixr_urls(html)
    assert urls == [long_url]


def test_extractor_finds_both_forms():
    """extract_tixr_urls() returns both short and long form URLs from the same page."""
    short_url = "https://tixr.com/e/12345"
    long_url = "https://www.tixr.com/groups/venue/events/show-99999"
    html = (
        f'<a href="{short_url}">Short</a>'
        f'<a href="{long_url}">Long</a>'
    )
    urls = TixrExtractor.extract_tixr_urls(html)
    assert short_url in urls
    assert long_url in urls
    assert len(urls) == 2


def test_extractor_deduplicates_urls():
    """extract_tixr_urls() returns each URL only once."""
    html = (
        '<a href="https://tixr.com/e/12345">Buy</a>'
        '<a href="https://tixr.com/e/12345">Buy Again</a>'
        '<a href="https://tixr.com/e/99999">Other</a>'
    )
    urls = TixrExtractor.extract_tixr_urls(html)
    assert urls == ["https://tixr.com/e/12345", "https://tixr.com/e/99999"]


def test_extractor_deduplicates_cross_form():
    """extract_tixr_urls() returns at most one URL per event when both short and
    long forms for the same event ID appear on the same page."""
    short_url = "https://tixr.com/e/177558"
    long_url = "https://www.tixr.com/groups/venue/events/comedy-show-177558"
    html = (
        f'<a href="{short_url}">Buy Short</a>'
        f'<a href="{long_url}">Buy Long</a>'
    )
    urls = TixrExtractor.extract_tixr_urls(html)
    # Only the short form should appear; the long form is the same event.
    assert urls == [short_url]


def test_extractor_returns_empty_for_no_tixr_urls():
    """extract_tixr_urls() returns [] when no Tixr links are present."""
    html = "<html><body><p>No shows</p></body></html>"
    urls = TixrExtractor.extract_tixr_urls(html)
    assert urls == []


# ---------------------------------------------------------------------------
# TixrExtractor.extract_org_jsonld_event_urls tests
# ---------------------------------------------------------------------------

_ORG_JSONLD_HTML = """
<html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "Test Venue",
  "events": [
    {"@type": "Event", "url": "https://tixr.com/groups/venue/events/show-a-111"},
    {"@type": "Event", "url": "https://tixr.com/groups/venue/events/show-b-222"}
  ]
}
</script>
</head><body></body></html>
"""


def test_extract_org_jsonld_event_urls_returns_urls():
    """extract_org_jsonld_event_urls() returns URLs from Organization JSON-LD block."""
    urls = TixrExtractor.extract_org_jsonld_event_urls(_ORG_JSONLD_HTML)
    assert urls == [
        "https://tixr.com/groups/venue/events/show-a-111",
        "https://tixr.com/groups/venue/events/show-b-222",
    ]


def test_extract_org_jsonld_event_urls_returns_empty_when_no_block():
    """extract_org_jsonld_event_urls() returns [] when no Organization JSON-LD exists."""
    html = "<html><body><p>No structured data</p></body></html>"
    urls = TixrExtractor.extract_org_jsonld_event_urls(html)
    assert urls == []


def test_extract_org_jsonld_event_urls_ignores_non_org_blocks():
    """extract_org_jsonld_event_urls() ignores JSON-LD blocks that aren't @type Organization."""
    html = """
    <script type="application/ld+json">{"@type": "Event", "url": "https://tixr.com/e/123"}</script>
    <script type="application/ld+json">{"@type": "WebPage", "name": "Foo"}</script>
    """
    urls = TixrExtractor.extract_org_jsonld_event_urls(html)
    assert urls == []


# ---------------------------------------------------------------------------
# collect_scraping_targets() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_targets_returns_scraping_url():
    """collect_scraping_targets() returns only the club's scraping_url."""
    scraper = TixrScraper(_club())
    targets = await scraper.collect_scraping_targets()
    assert len(targets) == 1
    assert targets[0].rstrip("/") == CALENDAR_URL.rstrip("/")


@pytest.mark.asyncio
async def test_collect_targets_prepends_https_when_missing():
    """collect_scraping_targets() adds https:// when scraping_url has no scheme."""
    scraper = TixrScraper(_club(scraping_url="www.example.com/shows"))
    targets = await scraper.collect_scraping_targets()
    assert targets[0].startswith("https://")


# ---------------------------------------------------------------------------
# get_data() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_resolves_short_form_urls(monkeypatch):
    """get_data() extracts short-form Tixr URLs and resolves them to TixrEvents."""
    scraper = TixrScraper(_club())

    html = _calendar_html_short(["177558", "176996"])
    event_a = _make_tixr_event("177558", "Open Mic Night")
    event_b = _make_tixr_event("176996", "Comedy Night")

    async def fake_fetch_html(self, url, **kwargs):
        return html

    monkeypatch.setattr(TixrScraper, "fetch_html", fake_fetch_html)
    scraper.tixr_client.get_event_detail_from_url = AsyncMock(
        side_effect=lambda url: event_a if "177558" in url else event_b
    )

    result = await scraper.get_data(CALENDAR_URL)

    assert isinstance(result, TixrPageData)
    assert len(result.event_list) == 2
    titles = {e.title for e in result.event_list}
    assert "Open Mic Night" in titles
    assert "Comedy Night" in titles


@pytest.mark.asyncio
async def test_get_data_resolves_long_form_urls(monkeypatch):
    """get_data() extracts long-form Tixr URLs and resolves them to TixrEvents."""
    scraper = TixrScraper(_club())
    long_url = "https://www.tixr.com/groups/venue/events/comedy-show-177558"
    html = _calendar_html_long([long_url])
    event = _make_tixr_event("177558", "Comedy Show")

    async def fake_fetch_html(self, url, **kwargs):
        return html

    monkeypatch.setattr(TixrScraper, "fetch_html", fake_fetch_html)
    scraper.tixr_client.get_event_detail_from_url = AsyncMock(return_value=event)

    result = await scraper.get_data(CALENDAR_URL)

    assert isinstance(result, TixrPageData)
    assert len(result.event_list) == 1
    assert result.event_list[0].title == "Comedy Show"


@pytest.mark.asyncio
async def test_get_data_returns_none_when_no_tixr_urls(monkeypatch):
    """get_data() returns None when no Tixr links are found on the page."""
    scraper = TixrScraper(_club())

    async def fake_fetch_html(self, url, **kwargs):
        return "<html><body><p>No shows</p></body></html>"

    monkeypatch.setattr(TixrScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(CALENDAR_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_when_tixr_client_returns_nothing(monkeypatch):
    """get_data() returns None when TixrClient returns None for all URLs."""
    scraper = TixrScraper(_club())
    html = _calendar_html_short(["177558"])

    async def fake_fetch_html(self, url, **kwargs):
        return html

    monkeypatch.setattr(TixrScraper, "fetch_html", fake_fetch_html)
    scraper.tixr_client.get_event_detail_from_url = AsyncMock(return_value=None)

    result = await scraper.get_data(CALENDAR_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_filters_by_org_jsonld_when_present(monkeypatch):
    """get_data() only processes URLs found in the Organization JSON-LD block."""
    scraper = TixrScraper(_club())
    kept_url = "https://tixr.com/groups/venue/events/show-a-177558"
    dropped_url = "https://tixr.com/groups/venue/events/show-b--182870"  # double-dash, client-side

    org_jsonld = f"""
    <script type="application/ld+json">
    {{"@type": "Organization", "events": [{{"url": "{kept_url}"}}]}}
    </script>
    """
    html = f'<a href="{kept_url}">Show A</a><a href="{dropped_url}">Show B</a>{org_jsonld}'
    event = _make_tixr_event("177558", "Show A")

    async def fake_fetch_html(self, url, **kwargs):
        return html

    monkeypatch.setattr(TixrScraper, "fetch_html", fake_fetch_html)
    scraper.tixr_client.get_event_detail_from_url = AsyncMock(return_value=event)

    result = await scraper.get_data(CALENDAR_URL)

    assert isinstance(result, TixrPageData)
    assert len(result.event_list) == 1
    # Only the kept URL was passed to the client
    scraper.tixr_client.get_event_detail_from_url.assert_called_once_with(kept_url)


@pytest.mark.asyncio
async def test_get_data_falls_back_to_all_urls_when_no_org_jsonld(monkeypatch):
    """get_data() uses all HTML-extracted URLs when no Organization JSON-LD block exists."""
    scraper = TixrScraper(_club())
    html = _calendar_html_short(["177558", "176996"])
    event_a = _make_tixr_event("177558", "Show A")
    event_b = _make_tixr_event("176996", "Show B")

    async def fake_fetch_html(self, url, **kwargs):
        return html

    monkeypatch.setattr(TixrScraper, "fetch_html", fake_fetch_html)
    scraper.tixr_client.get_event_detail_from_url = AsyncMock(
        side_effect=lambda url: event_a if "177558" in url else event_b
    )

    result = await scraper.get_data(CALENDAR_URL)

    assert isinstance(result, TixrPageData)
    assert len(result.event_list) == 2


@pytest.mark.asyncio
async def test_get_data_returns_none_on_fetch_error(monkeypatch):
    """get_data() returns None (and logs) when fetch_html raises an exception."""
    scraper = TixrScraper(_club())

    async def fake_fetch_html(self, url, **kwargs):
        raise RuntimeError("connection timeout")

    monkeypatch.setattr(TixrScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(CALENDAR_URL)
    assert result is None
