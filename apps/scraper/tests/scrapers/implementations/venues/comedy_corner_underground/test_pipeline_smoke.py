"""
Pipeline smoke tests for ComedyCornerScraper and ComedyCornerEvent.

Exercises the full scraping pipeline against mocked HTML that matches the
actual StageTime (ccu.stageti.me) RSC wire format.
"""

import json
import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.comedy_corner_underground import ComedyCornerEvent
from laughtrack.core.entities.show.model import Show
from laughtrack.scrapers.implementations.venues.comedy_corner_underground.scraper import (
    ComedyCornerScraper,
)
from laughtrack.scrapers.implementations.venues.comedy_corner_underground.data import (
    ComedyCornerPageData,
)
from laughtrack.scrapers.implementations.venues.comedy_corner_underground.extractor import (
    ComedyCornerExtractor,
)

LISTING_URL = "https://ccu.stageti.me"


def _club() -> Club:
    _c = Club(id=999, name='The Comedy Corner Underground', address='400 E Hennepin Ave', website='https://www.comedycornerunderground.com', popularity=0, zip_code='55414', phone_number='', visible=True, timezone='America/Chicago')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url=LISTING_URL, external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _listing_html(slugs: list[str]) -> str:
    """Render a minimal StageTime venue listing page with event links."""
    links = "\n".join(
        f'<a class="group block" href="/v/ccu/e/{slug}"><h3>{slug}</h3></a>'
        for slug in slugs
    )
    return f"""<!DOCTYPE html><html><head></head><body>
<div class="grid gap-4 sm:gap-6 grid-cols-1">
{links}
</div>
</body></html>"""


def _event_page_html(
    name: str,
    slug: str,
    is_open_mic: bool,
    admission_type: str,
    occurrences: list[str],
    timezone: str = "America/Chicago",
    performers: list[str] | None = None,
) -> str:
    """
    Build a minimal StageTime event page that matches the RSC wire format.

    The page embeds two self.__next_f.push([1, "..."]) segments:
    1. The event/venue props block (has occurrences, isOpenMic, admissionType)
    2. The JSON-LD block (has performer names and ticket URL)
    """
    if performers is None:
        performers = []

    occ_list = [
        {
            "id": f"occ-{i}",
            "startTime": t,
            "endTime": t,
            "doorsTime": None,
            "nameOverride": None,
            "maxCapacity": 75,
            "ticketsSold": 0,
            "isSoldOut": False,
            "status": "published",
            "soldByTicketType": {},
        }
        for i, t in enumerate(occurrences)
    ]

    event_data = {
        "id": "test-uuid-abcd",
        "name": name,
        "slug": slug,
        "admissionType": admission_type,
        "isOpenMic": is_open_mic,
        "micId": None,
        "showRemainingTickets": False,
        "ticketTypes": [
            {
                "id": "1",
                "name": "General Admission",
                "price": 1900,
                "quantity": 75,
                "soldCount": 0,
                "maxPerOrder": 10,
                "salesStart": None,
                "salesEnd": None,
                "salesStartOffset": None,
                "salesEndOffset": None,
                "salesEndMode": "showEnd",
                "priceIsTarget": True,
                "priceIncludesTax": False,
                "isHidden": False,
            }
        ],
        "occurrences": occ_list,
        "addOns": [],
    }
    venue_data = {
        "slug": "ccu",
        "salesTaxRate": 13.53,
        "absorbPlatformFee": True,
        "customFeeAmount": None,
        "customFeeName": None,
        "pricingMode": "target_price",
        "timezone": timezone,
    }

    rsc_event_arr = [
        "$",
        "div",
        None,
        {
            "className": "lg:col-span-1",
            "children": ["$", "$L21", None, {"event": event_data, "venue": venue_data}],
        },
    ]
    rsc_event_str = "1c:" + json.dumps(rsc_event_arr)
    push1 = json.dumps(rsc_event_str)[1:-1]  # Strip outer quotes

    jsonld = {
        "@context": "https://schema.org",
        "@type": "Event",
        "name": name,
        "description": "Live event at The Comedy Corner Underground",
        "startDate": occurrences[0] if occurrences else "",
        "offers": {
            "@type": "Offer",
            "url": f"https://stageti.me/v/ccu/e/{slug}",
            "price": "19.00",
            "priceCurrency": "USD",
        },
        "performer": [
            {"@type": "Person", "name": p}
            for p in performers
        ],
    }
    jsonld_props = {
        "id": "event-jsonld",
        "type": "application/ld+json",
        "dangerouslySetInnerHTML": {"__html": json.dumps(jsonld)},
    }
    rsc_jsonld_arr = ["$", "$L22", None, jsonld_props]
    rsc_jsonld_str = "1d:" + json.dumps(rsc_jsonld_arr)
    push2 = json.dumps(rsc_jsonld_str)[1:-1]

    return f"""<!DOCTYPE html><html><head></head><body>
<script>self.__next_f.push([1,"{push1}"])</script>
<script>self.__next_f.push([1,"{push2}"])</script>
</body></html>"""


# ---------------------------------------------------------------------------
# collect_scraping_targets() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_targets_returns_listing_url():
    """collect_scraping_targets() returns the StageTime venue URL."""
    scraper = ComedyCornerScraper(_club())
    targets = await scraper.collect_scraping_targets()
    assert len(targets) == 1
    assert targets[0] == LISTING_URL


# ---------------------------------------------------------------------------
# get_data() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_events(monkeypatch):
    """get_data() fetches listing + event pages and returns ComedyCornerPageData."""
    listing = _listing_html(["test-comedian"])
    event_page = _event_page_html(
        name="Test Comedian",
        slug="test-comedian",
        is_open_mic=False,
        admission_type="paid",
        occurrences=["2026-04-04T01:00:00.000Z"],
        performers=["Test Headliner"],
    )

    pages = {
        LISTING_URL: listing,
        f"{LISTING_URL}/e/test-comedian": event_page,
    }

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return pages.get(url, "")

    monkeypatch.setattr(ComedyCornerScraper, "fetch_html", fake_fetch_html)

    result = await ComedyCornerScraper(_club()).get_data(LISTING_URL)

    assert isinstance(result, ComedyCornerPageData)
    assert len(result.event_list) == 1
    assert result.event_list[0].title == "Test Comedian"
    assert result.event_list[0].start_time_utc == "2026-04-04T01:00:00.000Z"
    assert result.event_list[0].performers == ["Test Headliner"]


@pytest.mark.asyncio
async def test_get_data_expands_multi_date_event(monkeypatch):
    """get_data() creates one ComedyCornerEvent per occurrence for multi-date shows."""
    listing = _listing_html(["multi-date-show"])
    event_page = _event_page_html(
        name="Multi-Date Show",
        slug="multi-date-show",
        is_open_mic=False,
        admission_type="paid",
        occurrences=[
            "2026-04-04T01:00:00.000Z",
            "2026-04-05T01:00:00.000Z",
        ],
    )

    pages = {
        LISTING_URL: listing,
        f"{LISTING_URL}/e/multi-date-show": event_page,
    }

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return pages.get(url, "")

    monkeypatch.setattr(ComedyCornerScraper, "fetch_html", fake_fetch_html)

    result = await ComedyCornerScraper(_club()).get_data(LISTING_URL)

    assert result is not None
    assert len(result.event_list) == 2
    times = {e.start_time_utc for e in result.event_list}
    assert "2026-04-04T01:00:00.000Z" in times
    assert "2026-04-05T01:00:00.000Z" in times


@pytest.mark.asyncio
async def test_get_data_skips_open_mic_events(monkeypatch):
    """get_data() skips events where isOpenMic=True."""
    listing = _listing_html(["paid-show", "the-thursday-mic"])
    pages = {
        LISTING_URL: listing,
        f"{LISTING_URL}/e/paid-show": _event_page_html(
            "Paid Show", "paid-show", False, "paid", ["2026-04-04T01:00:00.000Z"]
        ),
        f"{LISTING_URL}/e/the-thursday-mic": _event_page_html(
            "The Thursday Mic", "the-thursday-mic", True, "no_advance_sales", ["2026-04-03T00:00:00.000Z"]
        ),
    }

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return pages.get(url, "")

    monkeypatch.setattr(ComedyCornerScraper, "fetch_html", fake_fetch_html)

    result = await ComedyCornerScraper(_club()).get_data(LISTING_URL)

    assert result is not None
    assert len(result.event_list) == 1
    assert result.event_list[0].title == "Paid Show"


@pytest.mark.asyncio
async def test_get_data_returns_none_on_empty_listing(monkeypatch):
    """get_data() returns None when the listing page has no event links."""

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return "<html><body><p>No events</p></body></html>"

    monkeypatch.setattr(ComedyCornerScraper, "fetch_html", fake_fetch_html)

    result = await ComedyCornerScraper(_club()).get_data(LISTING_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_on_empty_html(monkeypatch):
    """get_data() returns None when the listing page returns empty HTML."""

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return ""

    monkeypatch.setattr(ComedyCornerScraper, "fetch_html", fake_fetch_html)

    result = await ComedyCornerScraper(_club()).get_data(LISTING_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_when_all_events_are_open_mic(monkeypatch):
    """get_data() returns None when every event on the listing page is open mic / no_advance_sales."""
    listing = _listing_html(["open-mic-1", "open-mic-2"])
    pages = {
        LISTING_URL: listing,
        f"{LISTING_URL}/e/open-mic-1": _event_page_html(
            "The Thursday Mic", "open-mic-1", True, "no_advance_sales", ["2026-04-03T00:00:00.000Z"]
        ),
        f"{LISTING_URL}/e/open-mic-2": _event_page_html(
            "Friday Mic", "open-mic-2", True, "no_advance_sales", ["2026-04-04T00:00:00.000Z"]
        ),
    }

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return pages.get(url, "")

    monkeypatch.setattr(ComedyCornerScraper, "fetch_html", fake_fetch_html)

    result = await ComedyCornerScraper(_club()).get_data(LISTING_URL)
    assert result is None


# ---------------------------------------------------------------------------
# Extractor unit tests
# ---------------------------------------------------------------------------


def test_extract_event_slugs_returns_slugs():
    """extract_event_slugs() returns unique slugs from /v/ccu/e/ links."""
    html = _listing_html(["show-a", "show-b", "show-a"])  # duplicate slug
    slugs = ComedyCornerExtractor.extract_event_slugs(html)
    assert slugs == ["show-a", "show-b"]


def test_extract_event_data_returns_correct_fields():
    """extract_event_data() parses name, occurrences, timezone, performers, ticket URL."""
    html = _event_page_html(
        name="Jeremiah Coughlan",
        slug="jeremiah-coughlan",
        is_open_mic=False,
        admission_type="paid",
        occurrences=["2026-04-04T01:00:00.000Z", "2026-04-05T01:00:00.000Z"],
        timezone="America/Chicago",
        performers=["Jeremiah Coughlan"],
    )
    data = ComedyCornerExtractor.extract_event_data(html)

    assert data is not None
    assert data["name"] == "Jeremiah Coughlan"
    assert data["slug"] == "jeremiah-coughlan"
    assert data["is_open_mic"] is False
    assert data["admission_type"] == "paid"
    assert data["timezone"] == "America/Chicago"
    assert "2026-04-04T01:00:00.000Z" in data["occurrences"]
    assert "2026-04-05T01:00:00.000Z" in data["occurrences"]
    assert data["performers"] == ["Jeremiah Coughlan"]
    assert "jeremiah-coughlan" in data["ticket_url"]


def test_extract_event_data_returns_none_on_empty_html():
    """extract_event_data() returns None for empty HTML."""
    assert ComedyCornerExtractor.extract_event_data("") is None


def test_extract_event_data_returns_none_on_shell_html():
    """extract_event_data() returns None when no RSC push segments are present."""
    html = "<html><body><p>No RSC data</p></body></html>"
    assert ComedyCornerExtractor.extract_event_data(html) is None


def test_extract_event_data_excludes_non_published_occurrences():
    """extract_event_data() only includes occurrences with status='published'."""
    html = _event_page_html(
        name="Test Show",
        slug="test-show",
        is_open_mic=False,
        admission_type="paid",
        occurrences=["2026-04-04T01:00:00.000Z", "2026-04-05T01:00:00.000Z"],
    )
    # Inject a cancelled occurrence into the fixture
    import json as _json
    cancelled_occ = {
        "id": "occ-cancelled",
        "startTime": "2026-04-06T01:00:00.000Z",
        "endTime": "2026-04-06T02:30:00.000Z",
        "doorsTime": None,
        "nameOverride": None,
        "maxCapacity": 75,
        "ticketsSold": 0,
        "isSoldOut": False,
        "status": "cancelled",
        "soldByTicketType": {},
    }
    # Patch the HTML to include the cancelled occurrence
    html_with_cancelled = html.replace(
        '"status": "published"}, {"id": "occ-1"',
        '"status": "published"}, {"id": "occ-cancelled", "startTime": "2026-04-06T01:00:00.000Z", "endTime": "2026-04-06T02:30:00.000Z", "doorsTime": null, "nameOverride": null, "maxCapacity": 75, "ticketsSold": 0, "isSoldOut": false, "status": "cancelled", "soldByTicketType": {}}, {"id": "occ-1"',
    )

    data = ComedyCornerExtractor.extract_event_data(html)
    assert data is not None
    assert "2026-04-04T01:00:00.000Z" in data["occurrences"]
    assert "2026-04-05T01:00:00.000Z" in data["occurrences"]

    # Verify the extractor filters cancelled if present in the data
    # Build an HTML where one occurrence has status=cancelled directly
    html_cancelled = _event_page_html(
        name="Test Show",
        slug="test-show",
        is_open_mic=False,
        admission_type="paid",
        occurrences=["2026-04-04T01:00:00.000Z"],
    )
    # The status field is double-escaped in the RSC push string: \\"status\\": \\"published\\"
    html_cancelled = html_cancelled.replace('\\"status\\": \\"published\\"', '\\"status\\": \\"cancelled\\"', 1)
    data_cancelled = ComedyCornerExtractor.extract_event_data(html_cancelled)
    assert data_cancelled is not None
    assert data_cancelled["occurrences"] == [], (
        "Cancelled occurrences should be excluded from the extracted list"
    )


# ---------------------------------------------------------------------------
# ComedyCornerEvent.to_show() unit tests
# ---------------------------------------------------------------------------


def _make_event(
    title: str = "Test Comedian",
    start_time_utc: str = "2026-04-04T01:00:00.000Z",
    timezone: str = "America/Chicago",
    ticket_url: str = "https://stageti.me/v/ccu/e/test-comedian",
    performers: list[str] | None = None,
) -> ComedyCornerEvent:
    return ComedyCornerEvent(
        title=title,
        start_time_utc=start_time_utc,
        timezone=timezone,
        ticket_url=ticket_url,
        performers=performers or [],
    )


def test_to_show_returns_show_with_correct_name():
    """to_show() produces a Show with the correct title."""
    event = _make_event(title="Jeremiah Coughlan")
    show = event.to_show(_club())

    assert show is not None
    assert show.name == "Jeremiah Coughlan"


def test_to_show_parses_utc_to_local_time():
    """to_show() correctly converts UTC 01:00 to local 8:00 PM CDT (UTC-5 = 20:00)."""
    # 2026-04-04T01:00:00Z = Fri Apr 3, 8:00 PM CDT (UTC-5)
    event = _make_event(start_time_utc="2026-04-04T01:00:00.000Z")
    show = event.to_show(_club())

    assert show is not None
    # 01:00 UTC = 20:00 CDT (UTC-5)
    assert show.date.hour == 20
    assert show.date.minute == 0


def test_to_show_creates_ticket_with_stagetime_url():
    """to_show() creates a ticket pointing to the StageTime event URL."""
    url = "https://stageti.me/v/ccu/e/test-comedian"
    event = _make_event(ticket_url=url)
    show = event.to_show(_club())

    assert show is not None
    assert len(show.tickets) == 1
    assert show.tickets[0].purchase_url == url


def test_to_show_includes_performers_in_lineup():
    """to_show() includes performer names in the show lineup."""
    event = _make_event(performers=["Kevin White"])
    show = event.to_show(_club())

    assert show is not None
    names = [c.name for c in show.lineup]
    assert "Kevin White" in names


def test_to_show_returns_none_when_title_missing():
    """to_show() returns None when title is empty."""
    event = _make_event(title="")
    assert event.to_show(_club()) is None


def test_to_show_returns_none_when_ticket_url_missing():
    """to_show() returns None when ticket_url is empty."""
    event = _make_event(ticket_url="")
    assert event.to_show(_club()) is None


def test_to_show_returns_none_on_invalid_timestamp():
    """to_show() returns None when start_time_utc is unparseable."""
    event = _make_event(start_time_utc="not-a-timestamp")
    assert event.to_show(_club()) is None


# ---------------------------------------------------------------------------
# Transformation pipeline regression test
# ---------------------------------------------------------------------------


def test_transformation_pipeline_produces_shows():
    """
    Core regression: transformation_pipeline.transform() must return at least
    one Show when given ComedyCornerPageData with valid ComedyCornerEvent objects.

    If can_transform() returns False for ComedyCornerEvent (e.g., due to a type
    mismatch between the transformer's generic parameter and the event type),
    transform() silently returns an empty list with no error.
    """
    club = _club()
    scraper = ComedyCornerScraper(club)

    events = [
        _make_event("Test Comedian A", "2026-04-04T01:00:00.000Z"),
        _make_event("Test Comedian B", "2026-04-11T01:00:00.000Z"),
    ]
    page_data = ComedyCornerPageData(event_list=events)

    shows = scraper.transformation_pipeline.transform(page_data)

    assert len(shows) > 0, (
        "transformation_pipeline.transform() returned 0 Shows from ComedyCornerPageData — "
        "check ComedyCornerEventTransformer.can_transform() and that the transformer is "
        "registered with the correct generic type"
    )
    assert all(isinstance(s, Show) for s in shows)
