"""Pipeline smoke tests for TicketWebScraper.

Verifies that collect_scraping_targets(), get_data(), and transform_data()
wire together correctly for TicketWeb-powered club calendar pages.

Tests both the JS-based (var all_events) and HTML fallback extraction paths,
including pagination in the HTML fallback.
"""

import importlib.util
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.ticketweb.scraper import TicketWebScraper
from laughtrack.scrapers.implementations.api.ticketweb.data import TicketWebPageData


CALENDAR_URL = "https://exampleclub.com/events"


def _club() -> Club:
    _c = Club(id=999, name='Test Comedy Club', address='123 Main St', website='https://exampleclub.com', popularity=0, zip_code='10001', phone_number='', visible=True, timezone='America/New_York')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url=CALENDAR_URL, external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _js_calendar_html(events=None):
    """Build a calendar page with var all_events JS array."""
    if events is None:
        events = [
            ("Comedy Night", "2099-04-15 20:00:00", "/event/comedy-night"),
        ]
    items = []
    for title, date, url in events:
        items.append(f"{{ title: '{title}', start: new Date('{date}'), url: '{url}' }}")
    return f"<script>var all_events = [{', '.join(items)}];</script>"


def _html_event_block(name="Comedy Night", date="Jan 15 -", time="8:00 PM",
                      url="/event/comedy-night"):
    return f"""
    <div class="five columns">
        <div class="tw-name"><a href="{url}">{name}</a></div>
        <span class="tw-event-date">{date}</span>
        <span class="tw-event-time">{time}</span>
    </div>
    """


def _html_calendar_page(*blocks, next_url=None):
    """Build an HTML fallback calendar page with optional pagination."""
    html = "<div>header</div>" + "".join(blocks)
    if next_url:
        html += f'<a class="next" href="{next_url}">Next</a>'
    return html


def _detail_page_html(ticket_url="https://www.ticketweb.com/event/test-abc123",
                      status="onsale", price_text=None):
    price_span = (
        f'<span class="tw-price">{price_text}</span>' if price_text else ""
    )
    return f"""
    <div class="event-detail">
        {price_span}
        <a href="{ticket_url}"
           class="tw-buy-tix-btn tw_{status}">Buy Tickets</a>
    </div>
    """


# ---------------------------------------------------------------------------
# collect_scraping_targets() — JS path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_targets_js_path():
    """collect_scraping_targets() returns event URLs from JS var all_events."""
    scraper = TicketWebScraper(_club())
    scraper.fetch_html = AsyncMock(return_value=_js_calendar_html([
        ("Show A", "2099-05-01 20:00:00", "/event/show-a"),
        ("Show B", "2099-05-02 21:00:00", "/event/show-b"),
    ]))

    targets = await scraper.collect_scraping_targets()

    assert targets == ["/event/show-a", "/event/show-b"]
    scraper.fetch_html.assert_called_once_with(CALENDAR_URL)


# ---------------------------------------------------------------------------
# collect_scraping_targets() — HTML fallback path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_targets_html_fallback():
    """Falls back to HTML parsing when JS array is absent."""
    scraper = TicketWebScraper(_club())
    scraper.fetch_html = AsyncMock(return_value=_html_calendar_page(
        _html_event_block(name="HTML Show", date="Jun 1 -", time="8:00 PM", url="/event/html-show"),
    ))

    targets = await scraper.collect_scraping_targets()

    assert targets == ["/event/html-show"]


@pytest.mark.asyncio
async def test_collect_targets_html_fallback_with_pagination():
    """HTML fallback follows pagination links to gather events from multiple pages."""
    page1 = _html_calendar_page(
        _html_event_block(name="Page 1 Show", date="Jul 1 -", time="8:00 PM", url="/event/p1"),
        next_url="/events?page=2",
    )
    page2 = _html_calendar_page(
        _html_event_block(name="Page 2 Show", date="Jul 2 -", time="9:00 PM", url="/event/p2"),
    )
    scraper = TicketWebScraper(_club())
    scraper.fetch_html = AsyncMock(side_effect=[page1, page2])

    targets = await scraper.collect_scraping_targets()

    assert "/event/p1" in targets
    assert "/event/p2" in targets
    assert len(targets) == 2


@pytest.mark.asyncio
async def test_collect_targets_returns_empty_when_no_scraping_url():
    """Returns empty list when club has no scraping_url configured."""
    club = _club()
    club.scraping_url = ""
    scraper = TicketWebScraper(club)

    targets = await scraper.collect_scraping_targets()

    assert targets == []


@pytest.mark.asyncio
async def test_collect_targets_returns_empty_when_fetch_fails():
    """Returns empty list when fetch_html returns None."""
    scraper = TicketWebScraper(_club())
    scraper.fetch_html = AsyncMock(return_value=None)

    targets = await scraper.collect_scraping_targets()

    assert targets == []


@pytest.mark.asyncio
async def test_collect_targets_returns_empty_when_no_events():
    """Returns empty list when page has no events."""
    scraper = TicketWebScraper(_club())
    scraper.fetch_html = AsyncMock(return_value="<html><body>Empty</body></html>")

    targets = await scraper.collect_scraping_targets()

    assert targets == []


# ---------------------------------------------------------------------------
# get_data() — detail page extraction
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_ticket():
    """get_data() extracts ticket info from detail page."""
    scraper = TicketWebScraper(_club())
    # Populate the calendar cache via collect_scraping_targets
    scraper.fetch_html = AsyncMock(return_value=_js_calendar_html([
        ("Comedy Night", "2099-04-15 20:00:00", "/event/comedy-night"),
    ]))
    await scraper.collect_scraping_targets()

    # Now mock the detail page fetch
    scraper.fetch_html = AsyncMock(
        return_value=_detail_page_html("https://www.ticketweb.com/event/comedy-abc", "onsale"),
    )
    result = await scraper.get_data("/event/comedy-night")

    assert isinstance(result, TicketWebPageData)
    assert len(result.event_list) == 1
    assert result.event_list[0].name == "Comedy Night"
    assert result.event_list[0].ticket_url == "https://www.ticketweb.com/event/comedy-abc"
    assert result.event_list[0].sold_out is False


@pytest.mark.asyncio
async def test_get_data_detects_sold_out():
    """get_data() correctly detects sold-out status from detail page."""
    scraper = TicketWebScraper(_club())
    scraper.fetch_html = AsyncMock(return_value=_js_calendar_html([
        ("Sold Show", "2099-06-01 20:00:00", "/event/sold-show"),
    ]))
    await scraper.collect_scraping_targets()

    scraper.fetch_html = AsyncMock(
        return_value=_detail_page_html("https://www.ticketweb.com/event/sold-xyz", "ticketssold"),
    )
    result = await scraper.get_data("/event/sold-show")

    assert result.event_list[0].sold_out is True


@pytest.mark.asyncio
async def test_get_data_detects_ticketweb_page_level_sold_out():
    """get_data() follows the purchase page for its event-level status."""
    scraper = TicketWebScraper(_club())
    scraper.fetch_html = AsyncMock(return_value=_js_calendar_html([
        ("Alfred Robles", "2099-08-01 19:00:00", "/event/alfred-robles"),
    ]))
    await scraper.collect_scraping_targets()

    ticket_url = "https://www.ticketweb.com/event/alfred-robles-tickets/14197274"
    scraper.fetch_html = AsyncMock(side_effect=[
        _detail_page_html(ticket_url, "onsale"),
        """
        <div class="bg-bg-error-primary">
            <div class="text-text-error-primary">Sold Out</div>
        </div>
        """,
    ])

    result = await scraper.get_data("/event/alfred-robles")

    assert result.event_list[0].ticket_url == ticket_url
    assert result.event_list[0].sold_out is True
    assert scraper.fetch_html.await_args_list[1].args == (ticket_url,)
    assert scraper.fetch_html.await_args_list[1].kwargs == {
        "direct_js_fallback_on_proxy_error": True,
    }


@pytest.mark.asyncio
async def test_get_data_keeps_event_when_ticketweb_purchase_fetch_fails():
    """Purchase-page enrichment must not drop an otherwise valid event."""
    scraper = TicketWebScraper(_club())
    scraper.fetch_html = AsyncMock(return_value=_js_calendar_html([
        ("Comedy Night", "2099-08-02 19:00:00", "/event/comedy-night"),
    ]))
    await scraper.collect_scraping_targets()

    ticket_url = "https://www.ticketweb.com/event/comedy-night-tickets/12345"
    scraper.fetch_html = AsyncMock(side_effect=[
        _detail_page_html(ticket_url, "onsale"),
        RuntimeError("proxy unavailable"),
    ])

    result = await scraper.get_data("/event/comedy-night")

    assert result.event_list[0].ticket_url == ticket_url
    assert result.event_list[0].sold_out is False


@pytest.mark.asyncio
async def test_get_data_keeps_event_when_direct_recovery_returns_none():
    """A failed proxy and direct recovery still retain the calendar event."""
    scraper = TicketWebScraper(_club())
    scraper.fetch_html = AsyncMock(return_value=_js_calendar_html([
        ("Comedy Night", "2099-08-02 19:00:00", "/event/comedy-night"),
    ]))
    await scraper.collect_scraping_targets()

    ticket_url = "https://www.ticketweb.com/event/comedy-night-tickets/12345"
    scraper.fetch_html = AsyncMock(side_effect=[
        _detail_page_html(ticket_url, "onsale"),
        None,
    ])

    result = await scraper.get_data("/event/comedy-night")

    assert result.event_list[0].ticket_url == ticket_url
    assert result.event_list[0].sold_out is False
    scraper.fetch_html.assert_awaited_with(
        ticket_url,
        direct_js_fallback_on_proxy_error=True,
    )


@pytest.mark.asyncio
async def test_get_data_extracts_price_from_detail_page():
    """get_data() extracts the low end of the tw-price range into the event."""
    scraper = TicketWebScraper(_club())
    scraper.fetch_html = AsyncMock(return_value=_js_calendar_html([
        ("Priced Show", "2099-05-01 20:00:00", "/event/priced-show"),
    ]))
    await scraper.collect_scraping_targets()

    scraper.fetch_html = AsyncMock(
        return_value=_detail_page_html(
            "https://www.ticketweb.com/event/priced-abc", "onsale",
            price_text=" $25.47 - $170.68 ",
        ),
    )
    result = await scraper.get_data("/event/priced-show")

    assert result.event_list[0].price == 25.47

    show = result.event_list[0].to_show(_club())
    assert show.tickets[0].price == 25.47


@pytest.mark.asyncio
async def test_get_data_price_none_when_detail_page_has_no_price():
    """get_data() leaves price None when the detail page renders no tw-price."""
    scraper = TicketWebScraper(_club())
    scraper.fetch_html = AsyncMock(return_value=_js_calendar_html([
        ("Unpriced Show", "2099-05-02 20:00:00", "/event/unpriced-show"),
    ]))
    await scraper.collect_scraping_targets()

    scraper.fetch_html = AsyncMock(
        return_value=_detail_page_html("https://www.ticketweb.com/event/unpriced-abc"),
    )
    result = await scraper.get_data("/event/unpriced-show")

    assert result.event_list[0].price is None
    show = result.event_list[0].to_show(_club())
    assert show.tickets[0].price is None


@pytest.mark.asyncio
async def test_get_data_returns_none_for_uncached_target():
    """get_data() returns None when target URL is not in the calendar cache."""
    scraper = TicketWebScraper(_club())

    result = await scraper.get_data("/event/unknown")

    assert result is None


@pytest.mark.asyncio
async def test_get_data_handles_missing_ticket_url():
    """get_data() still returns PageData when detail page has no ticket link."""
    scraper = TicketWebScraper(_club())
    scraper.fetch_html = AsyncMock(return_value=_js_calendar_html([
        ("No Ticket Show", "2099-08-01 20:00:00", "/event/no-ticket"),
    ]))
    await scraper.collect_scraping_targets()

    scraper.fetch_html = AsyncMock(return_value="<html><body>No buy link</body></html>")
    result = await scraper.get_data("/event/no-ticket")

    assert isinstance(result, TicketWebPageData)
    assert result.event_list[0].ticket_url is None
    assert result.event_list[0].sold_out is False


# ---------------------------------------------------------------------------
# transform_data() — end-to-end pipeline
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transform_data_produces_shows():
    """Full pipeline: collect → get_data → transform produces Show objects."""
    scraper = TicketWebScraper(_club())
    scraper.fetch_html = AsyncMock(return_value=_js_calendar_html([
        ("Tuesday Open Mic", "2099-04-15 20:00:00", "/event/open-mic"),
    ]))
    await scraper.collect_scraping_targets()

    scraper.fetch_html = AsyncMock(
        return_value=_detail_page_html("https://www.ticketweb.com/event/mic-123", "onsale"),
    )
    page_data = await scraper.get_data("/event/open-mic")
    shows = scraper.transform_data(page_data, "/event/open-mic")

    assert len(shows) == 1
    show = shows[0]
    assert show.name == "Tuesday Open Mic"
    assert show.show_page_url == "/event/open-mic"
    assert len(show.tickets) == 1
    assert show.tickets[0].purchase_url == "https://www.ticketweb.com/event/mic-123"
    assert show.tickets[0].sold_out is False
    assert show.tickets[0].type == "General Admission"


@pytest.mark.asyncio
async def test_transform_data_returns_empty_for_none_page_data():
    """transform_data() returns [] when page_data is None."""
    scraper = TicketWebScraper(_club())
    shows = scraper.transform_data(None, "/event/missing")
    assert shows == []
