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

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.tixr import TixrEvent
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.scrapers.implementations.api.tixr.scraper import TixrPublicCardScraper, TixrScraper
from laughtrack.scrapers.implementations.api.tixr.data import TixrPageData
from laughtrack.scrapers.implementations.api.tixr.extractor import TixrExtractor

CALENDAR_URL = "https://www.hahacomedyclub.com/calendar"
IMPROV_ASYLUM_TIXR_URL = "https://www.tixr.com/groups/improvasylum"
STAND_SCRAPING_URL = "thestandnyc.com"
STAND_PUBLIC_SHOWS_URL = "https://thestandnyc.com/shows"
STAND_TIXR_URL = "https://www.tixr.com/groups/thestandnyc/events/the-stand-presents-josh-ocean-thomas--187376"


def _club(scraping_url: str = CALENDAR_URL) -> Club:
    _c = Club(id=999, name='Test Tixr Venue', address='123 Main St', website='https://example.com', popularity=0, zip_code='90001', phone_number='', visible=True, timezone='America/Los_Angeles')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url=scraping_url, external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _improv_asylum_club() -> Club:
    _c = Club(id=141, name='Improv Asylum', address='216 Hanover St', website='https://improvasylum.com', popularity=0, zip_code='02113', phone_number='', visible=True, timezone='America/New_York')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='tixr', scraper_key='tixr', source_url=IMPROV_ASYLUM_TIXR_URL, external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _stand_club() -> Club:
    _c = Club(id=99, name='The Stand', address='', website='https://thestandnyc.com', popularity=0, zip_code='', phone_number='', visible=True, timezone='America/New_York')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url=STAND_SCRAPING_URL, external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


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


def _calendar_html_subdomain(group: str, event_slugs: list) -> str:
    """Calendar page with subdomain-form {group}.tixr.com/{slug} links."""
    links = "".join(
        f'<a href="https://{group}.tixr.com/{slug}">Buy Tickets</a>'
        for slug in event_slugs
    )
    return f"<html><body><div class='calendar'>{links}</div></body></html>"


def _calendar_html_with_more_shows(next_href: str, event_ids: list[str]) -> str:
    links = "".join(
        f'<a href="https://tixr.com/e/{event_id}" class="buy-tickets-btn">Buy Tickets</a>'
        for event_id in event_ids
    )
    return f"""
    <html><body>
    <div class='calendar'>{links}</div>
    <a class="btn btn-outline-light loading-btn" href="{next_href}">More Shows</a>
    </body></html>
    """


def _improv_asylum_pixl_response() -> dict:
    return {
        "events": [
            {
                "id": "d3b148b6-0c3c-4f11-86fa-ef5c6a24c800",
                "title": "Improv Asylum&#39;s Main Stage Show",
                "description": "Fast-paced improv",
                "start": "2026-05-08T23:00:00.000Z",
                "end": "2026-05-09T00:30:00.000Z",
                "price": 30,
                "venue": "Improv Asylum",
                "ticketUrl": "https://www.tixr.com/groups/improvasylum/events/improv-asylum-s-main-stage-show-169028",
                "status": "available",
                "timezone": "America/New_York",
                "sales": [
                    {
                        "id": 1852654,
                        "name": "General Admission",
                        "currentPrice": 33.54,
                        "state": "OPEN",
                    },
                    {
                        "id": 1852658,
                        "name": "Premium",
                        "currentPrice": 37.18,
                        "state": "OPEN",
                    },
                ],
            }
        ]
    }


def _stand_public_card_html() -> str:
    """Minimal Bootstrap-style show row matching thestandnyc.com/shows.

    The h2.showtitle href encodes the full ISO datetime in its slug; the
    a.btn-stand href carries the Tixr ticket URL. Sold-out shows replace
    the buy link with a span.btn-outline-danger and should be skipped.
    """
    return """<html><body>
<div class="row show_row ">
  <h2 class="showtitle"><a href="https://thestandnyc.com//shows/show/12964/2026-05-08-190000-the-stand-presents-josh-ocean-thomas">The Stand Presents: Josh Ocean Thomas</a></h2>
  <h3 class="showinfo"><span class="show_date">May 8</span> | <span class="show_date">7:00 PM</span> <span class="list-show-room">Upstairs</span></h3>
  <div class="text-uppercase">
    <a href="https://www.tixr.com/groups/thestandnyc/events/the-stand-presents-josh-ocean-thomas--187376" class="btn btn-stand">Buy Tickets</a>
  </div>
</div>
<div class="row show_row ">
  <h2 class="showtitle"><a href="/shows/show/12965/2026-05-08-200000-the-stand-presents-kyle-dunnigan">The Stand Presents: Kyle Dunnigan</a></h2>
  <h3 class="showinfo"><span class="show_date">May 8</span> | <span class="show_date">8:00 PM</span> <span class="list-show-room">Main Room</span></h3>
  <div class="text-uppercase">
    <span class="btn btn-outline-danger">Sold Out</span>
  </div>
</div>
</body></html>"""


# ---------------------------------------------------------------------------
# TixrExtractor unit tests
# ---------------------------------------------------------------------------


def test_tixr_scraper_keys_are_distinct():
    """Detail-page and venue-owned public-card Tixr paths are queryable separately."""
    assert TixrScraper.key == "tixr"
    assert TixrPublicCardScraper.key == "tixr_public_card"


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


def test_extractor_finds_subdomain_urls():
    """extract_tixr_urls() picks up {group}.tixr.com/{slug} subdomain links."""
    html = (
        '<a href="https://rosecitycomedy.tixr.com/toddbarry">Todd Barry</a>'
        '<a href="https://rosecitycomedy.tixr.com/openmic">Open Mic</a>'
    )
    urls = TixrExtractor.extract_tixr_urls(html)
    assert urls == [
        "https://rosecitycomedy.tixr.com/toddbarry",
        "https://rosecitycomedy.tixr.com/openmic",
    ]


def test_extractor_deduplicates_subdomain_urls():
    """extract_tixr_urls() deduplicates repeated subdomain URLs."""
    html = (
        '<a href="https://rosecitycomedy.tixr.com/toddbarry">Buy</a>'
        '<a href="https://rosecitycomedy.tixr.com/toddbarry">Buy Again</a>'
    )
    urls = TixrExtractor.extract_tixr_urls(html)
    assert urls == ["https://rosecitycomedy.tixr.com/toddbarry"]


def test_extractor_excludes_www_subdomain():
    """extract_tixr_urls() does not match www.tixr.com as a subdomain URL."""
    html = '<a href="https://www.tixr.com/groups/venue/events/show-123">Buy</a>'
    urls = TixrExtractor.extract_tixr_urls(html)
    # Should be captured as long-form, not subdomain
    assert len(urls) == 1
    assert "groups/venue/events" in urls[0]


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


def test_get_event_id_short_form():
    """get_event_id() returns the numeric ID from a short-form Tixr URL."""
    assert TixrExtractor.get_event_id("https://tixr.com/e/177558") == "177558"


def test_get_event_id_long_form():
    """get_event_id() returns the numeric ID from a long-form Tixr URL."""
    assert TixrExtractor.get_event_id("https://www.tixr.com/groups/venue/events/comedy-show-177558") == "177558"


def test_get_event_id_double_dash_url():
    """get_event_id() still extracts the trailing numeric ID from double-dash URLs.
    These are client-side rendered and will be filtered out by the Org JSON-LD
    event ID set (not by URL format), so returning an ID here is correct."""
    assert TixrExtractor.get_event_id("https://tixr.com/groups/venue/events/show--182870") == "182870"


def test_get_event_id_returns_none_for_non_tixr_url():
    """get_event_id() returns None when the URL is not a recognized Tixr URL."""
    assert TixrExtractor.get_event_id("https://example.com/shows/123") is None


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
async def test_collect_targets_returns_scraping_url(monkeypatch):
    """collect_scraping_targets() returns the club's scraping_url when no pagination exists."""
    scraper = TixrScraper(_club())

    async def fake_fetch_html(self, url, **kwargs):
        return _calendar_html_short(["177558"])

    monkeypatch.setattr(TixrScraper, "fetch_html", fake_fetch_html)
    targets = await scraper.collect_scraping_targets()
    assert len(targets) == 1
    assert targets[0].rstrip("/") == CALENDAR_URL.rstrip("/")


@pytest.mark.asyncio
async def test_collect_targets_prepends_https_when_missing(monkeypatch):
    """collect_scraping_targets() adds https:// when scraping_url has no scheme."""
    scraper = TixrScraper(_club(scraping_url="www.example.com/shows"))

    async def fake_fetch_html(self, url, **kwargs):
        return _calendar_html_short(["177558"])

    monkeypatch.setattr(TixrScraper, "fetch_html", fake_fetch_html)
    targets = await scraper.collect_scraping_targets()
    assert targets[0].startswith("https://")


@pytest.mark.asyncio
async def test_collect_targets_discovers_more_shows_pages(monkeypatch):
    """collect_scraping_targets() follows bounded same-site pagination links."""
    scraper = TixrScraper(_club(scraping_url="https://thestandnyc.com/shows"))
    page_map = {
        "https://thestandnyc.com/shows": _calendar_html_with_more_shows(
            "/shows?page=2", ["177558"]
        ),
        "https://thestandnyc.com/shows?page=2": _calendar_html_short(["176996"]),
    }

    async def fake_fetch_html(self, url, **kwargs):
        return page_map[url]

    monkeypatch.setattr(TixrScraper, "fetch_html", fake_fetch_html)

    targets = await scraper.collect_scraping_targets()

    assert targets == [
        "https://thestandnyc.com/shows",
        "https://thestandnyc.com/shows?page=2",
    ]


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
async def test_get_data_resolves_subdomain_urls(monkeypatch):
    """get_data() extracts subdomain-form Tixr URLs and resolves them to TixrEvents."""
    scraper = TixrScraper(_club())

    html = _calendar_html_subdomain("rosecitycomedy", ["toddbarry", "openmic"])
    event_a = _make_tixr_event("100001", "Todd Barry")
    event_b = _make_tixr_event("100002", "Open Mic")

    async def fake_fetch_html(self, url, **kwargs):
        return html

    monkeypatch.setattr(TixrScraper, "fetch_html", fake_fetch_html)
    scraper.tixr_client.get_event_detail_from_url = AsyncMock(
        side_effect=lambda url: event_a if "toddbarry" in url else event_b
    )

    result = await scraper.get_data(CALENDAR_URL)

    assert isinstance(result, TixrPageData)
    assert len(result.event_list) == 2
    titles = {e.title for e in result.event_list}
    assert "Todd Barry" in titles
    assert "Open Mic" in titles


@pytest.mark.asyncio
async def test_public_card_scraper_avoids_blocked_detail_fetch(monkeypatch):
    """
    The Stand's /shows page exposes title, ISO datetime in the title-link
    slug, and a Tixr ticket URL, so the public-card scraper builds Show
    objects from the page instead of calling the DataDome-blocked Tixr
    detail endpoint. Sold-out cards have no Tixr URL and are skipped.
    """
    scraper = TixrPublicCardScraper(_stand_club())

    async def fake_fetch_html(self, url, **kwargs):
        return _stand_public_card_html()

    monkeypatch.setattr(TixrPublicCardScraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(
        scraper.tixr_client,
        "get_event_detail_from_url",
        AsyncMock(side_effect=AssertionError("Tixr detail pages should not be fetched")),
    )

    result = await scraper.get_data(STAND_PUBLIC_SHOWS_URL)

    assert isinstance(result, TixrPageData)
    assert result.get_event_count() == 1
    event = result.event_list[0]
    assert event.title == "The Stand Presents: Josh Ocean Thomas"
    assert event.source_url == STAND_TIXR_URL
    assert event.show.show_page_url == STAND_TIXR_URL
    assert event.show.tickets[0].purchase_url == STAND_TIXR_URL
    assert event.show.tickets[0].sold_out is False
    assert event.show.room == "Upstairs"
    assert event.show.date.year == 2026
    assert event.show.date.month == 5
    assert event.show.date.day == 8
    assert event.show.date.hour == 19
    assert event.show.date.minute == 0
    scraper.tixr_client.get_event_detail_from_url.assert_not_called()


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
async def test_get_data_uses_improv_asylum_pixl_fallback_when_tixr_group_is_blocked(monkeypatch):
    """Improv Asylum falls back to the venue-owned Pixl API when the Tixr group page has no event links."""
    scraper = TixrScraper(_improv_asylum_club())

    async def fake_fetch_calendar_html(url):
        return "<html><title>tixr.com</title><body>DataDome challenge</body></html>"

    async def fake_fetch_json(url, **kwargs):
        assert url == "https://calendar.improvasylum.com/api/events/improv-asylum"
        return _improv_asylum_pixl_response()

    monkeypatch.setattr(scraper, "_fetch_calendar_html", fake_fetch_calendar_html)
    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)
    scraper.tixr_client.get_event_detail_from_url = AsyncMock()

    result = await scraper.get_data(IMPROV_ASYLUM_TIXR_URL)

    assert isinstance(result, TixrPageData)
    assert len(result.event_list) == 1
    event = result.event_list[0]
    assert event.title == "Improv Asylum's Main Stage Show"
    assert event.event_id == "169028"
    assert event.show.date.isoformat() == "2026-05-08T19:00:00-04:00"
    assert event.show.show_page_url == (
        "https://www.tixr.com/groups/improvasylum/events/improv-asylum-s-main-stage-show-169028"
    )
    assert [ticket.type for ticket in event.show.tickets] == ["General Admission", "Premium"]
    assert [ticket.price for ticket in event.show.tickets] == [33.54, 37.18]
    scraper.tixr_client.get_event_detail_from_url.assert_not_called()


@pytest.mark.asyncio
async def test_get_data_uses_improv_asylum_pixl_fallback_when_tixr_group_fetch_returns_none(monkeypatch):
    """Improv Asylum still falls back when DataDome/CAPTCHA makes the Tixr group fetch unrecoverable."""
    scraper = TixrScraper(_improv_asylum_club())

    async def fake_fetch_calendar_html(url):
        return None

    async def fake_fetch_json(url, **kwargs):
        assert url == "https://calendar.improvasylum.com/api/events/improv-asylum"
        return _improv_asylum_pixl_response()

    monkeypatch.setattr(scraper, "_fetch_calendar_html", fake_fetch_calendar_html)
    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)
    scraper.tixr_client.get_event_detail_from_url = AsyncMock()

    result = await scraper.get_data(IMPROV_ASYLUM_TIXR_URL)

    assert isinstance(result, TixrPageData)
    assert len(result.event_list) == 1
    event = result.event_list[0]
    assert event.title == "Improv Asylum's Main Stage Show"
    assert event.event_id == "169028"
    scraper.tixr_client.get_event_detail_from_url.assert_not_called()


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
async def test_get_data_filters_by_event_id_when_url_forms_differ(monkeypatch):
    """get_data() matches events by ID even when HTML has short-form URLs and
    Org JSON-LD has long-form URLs for the same events (or vice versa)."""
    scraper = TixrScraper(_club())

    # HTML has short-form; JSON-LD has long-form for the same event — string
    # equality would produce an empty intersection here.
    short_url = "https://tixr.com/e/177558"
    long_url_jsonld = "https://www.tixr.com/groups/venue/events/comedy-show-177558"
    dropped_long_url = "https://www.tixr.com/groups/venue/events/dropped--182870"

    org_jsonld = f"""
    <script type="application/ld+json">
    {{"@type": "Organization", "events": [{{"url": "{long_url_jsonld}"}}]}}
    </script>
    """
    html = (
        f'<a href="{short_url}">Short</a>'
        f'<a href="{long_url_jsonld}">Long</a>'
        f'<a href="{dropped_long_url}">Dropped</a>'
        + org_jsonld
    )
    event = _make_tixr_event("177558", "Comedy Show")

    async def fake_fetch_html(self, url, **kwargs):
        return html

    monkeypatch.setattr(TixrScraper, "fetch_html", fake_fetch_html)
    scraper.tixr_client.get_event_detail_from_url = AsyncMock(return_value=event)

    result = await scraper.get_data(CALENDAR_URL)

    assert isinstance(result, TixrPageData)
    assert len(result.event_list) == 1
    # TixrExtractor deduplicates cross-form, keeping the short-form URL
    scraper.tixr_client.get_event_detail_from_url.assert_called_once_with(short_url)


@pytest.mark.asyncio
async def test_get_data_returns_none_on_fetch_error(monkeypatch):
    """get_data() returns None (and logs) when fetch_html raises an exception."""
    scraper = TixrScraper(_club())

    async def fake_fetch_html(self, url, **kwargs):
        raise RuntimeError("connection timeout")

    monkeypatch.setattr(TixrScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(CALENDAR_URL)
    assert result is None
