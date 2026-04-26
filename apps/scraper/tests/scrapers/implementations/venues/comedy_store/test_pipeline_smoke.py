"""
Smoke tests for the Comedy Store scraper pipeline.

Exercises collect_scraping_targets() -> get_data() -> events together against
HTML fixtures that match the actual thecomedystore.com/calendar/YYYY-MM-DD
structure.

Key assertions:
  - collect_scraping_targets() returns SCRAPE_WINDOW_DAYS date-based URLs
  - get_data() parses title, datetime slug, room, and ticket URL correctly
  - sold-out shows are detected and the sold_out flag is set
  - days with no shows (empty HTML) return None without raising
"""

import importlib.util
from datetime import date

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.venues.comedy_store.scraper import (
    ComedyStoreScraper,
    _SCRAPE_WINDOW_DAYS,
)
from laughtrack.scrapers.implementations.venues.comedy_store.data import ComedyStorePageData


CALENDAR_BASE = "https://thecomedystore.com/calendar"
LA_JOLLA_CALENDAR_BASE = "https://thecomedystore.com/la-jolla/calendar"


def _club() -> Club:
    _c = Club(id=99, name='The Comedy Store', address='8433 W Sunset Blvd', website='https://thecomedystore.com', popularity=0, zip_code='90069', phone_number='', visible=True, timezone='America/Los_Angeles')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url=f'{CALENDAR_BASE}', external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _day_html(shows: list[dict]) -> str:
    """
    Build a minimal Comedy Store calendar day page with one or more show items.

    Each dict in `shows` should have:
      slug      - e.g. "2026-04-01t200000-0700-my-show"
      title     - e.g. "My Show"
      room      - e.g. "Main Room" (optional)
      ticket    - showclix URL (optional; omit to simulate sold-out / no ticket)
      sold_out  - bool (optional)
    """
    items_html = ""
    for s in shows:
        slug = s["slug"]
        title = s.get("title", "Test Show")
        room = s.get("room", "")
        ticket = s.get("ticket", "")
        sold_out_html = (
            '<div class="alert-container"><h3 class="text-store-yellow fw-bold">SOLD OUT</h3></div>'
            if s.get("sold_out")
            else ""
        )
        ticket_html = (
            f'<a href="{ticket}" class="btn btn-store mt-3 fw-bold slidebutton">Buy Tickets</a>'
            if ticket
            else ""
        )
        room_html = (
            f'<h3 class="text-white text-uppercase fw-bold fs-6 my-2 align-middle">'
            f'<span aria-hidden="true">MR</span>{room}</h3>'
            if room
            else ""
        )
        items_html += f"""
        <div class="bg-black show-item">
          <div class="row gx-3 h-100 show_row">
            <div class="col-12 col-sm-3 show_image">
              <div class="col-6 d-sm-none">
                <h2 class="font-cooper display-6 show-title">
                  <a href="/calendar/show/100/{slug}">{title}</a>
                </h2>
              </div>
            </div>
            <div class="d-none d-sm-block col-sm-9">
              {sold_out_html}
              <h2 class="font-cooper display-6 show-title">
                <a href="/calendar/show/100/{slug}">{title}</a>
              </h2>
              <div class="d-none d-md-block">
                <div class="col-12">
                  <div class="d-flex align-items-center">
                    <div class="me-5">
                      <span>April 1</span> | <span>8:00 PM</span>
                    </div>
                    {room_html}
                  </div>
                </div>
              </div>
              {ticket_html}
            </div>
          </div>
        </div>
        """
    return f"<html><body>{items_html}</body></html>"


def _la_jolla_club() -> Club:
    _c = Club(id=200, name='The Comedy Store La Jolla', address='8971 Villa La Jolla Dr', website='https://thecomedystore.com/la-jolla', popularity=0, zip_code='92037', phone_number='', visible=True, timezone='America/Los_Angeles')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url=LA_JOLLA_CALENDAR_BASE, external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _la_jolla_day_html(shows: list[dict]) -> str:
    """Like _day_html but hrefs use the /la-jolla/calendar/show/ prefix.

    Each dict may include:
      slug      - e.g. "2026-04-01t200000-0700-my-show"
      title     - e.g. "My Show"
      room      - e.g. "Showroom" (optional)
      ticket    - showclix URL (optional; omit to simulate sold-out / no ticket)
      sold_out  - bool (optional)
    """
    items_html = ""
    for s in shows:
        slug = s["slug"]
        title = s.get("title", "Test Show")
        room = s.get("room", "")
        ticket = s.get("ticket", "")
        sold_out_html = (
            '<div class="alert-container"><h3 class="text-store-yellow fw-bold">SOLD OUT</h3></div>'
            if s.get("sold_out")
            else ""
        )
        ticket_html = (
            f'<a href="{ticket}" class="btn btn-store mt-3 fw-bold slidebutton">Buy Tickets</a>'
            if ticket
            else ""
        )
        room_html = (
            f'<h3 class="text-white text-uppercase fw-bold fs-6 my-2 align-middle">'
            f'<span aria-hidden="true">SR</span>{room}</h3>'
            if room
            else ""
        )
        items_html += f"""
        <div class="bg-black show-item">
          <div class="row gx-3 h-100 show_row">
            <div class="col-12 col-sm-3 show_image">
              <div class="col-6 d-sm-none">
                <h2 class="font-cooper display-6 show-title">
                  <a href="/la-jolla/calendar/show/100/{slug}">{title}</a>
                </h2>
              </div>
            </div>
            <div class="d-none d-sm-block col-sm-9">
              {sold_out_html}
              <h2 class="font-cooper display-6 show-title">
                <a href="/la-jolla/calendar/show/100/{slug}">{title}</a>
              </h2>
              <div class="d-none d-md-block">
                <div class="col-12">
                  <div class="d-flex align-items-center">
                    <div class="me-5">
                      <span>April 1</span> | <span>7:00 PM</span>
                    </div>
                    {room_html}
                  </div>
                </div>
              </div>
              {ticket_html}
            </div>
          </div>
        </div>
        """
    return f"<html><body>{items_html}</body></html>"


def _empty_day_html() -> str:
    return "<html><body><h1 class='display-3 font-cooper text-center'>No shows today</h1></body></html>"


# ---------------------------------------------------------------------------
# collect_scraping_targets
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_date_based_urls():
    """collect_scraping_targets() must return SCRAPE_WINDOW_DAYS date URLs."""
    scraper = ComedyStoreScraper(_club())
    targets = await scraper.collect_scraping_targets()

    assert len(targets) == _SCRAPE_WINDOW_DAYS, (
        f"Expected {_SCRAPE_WINDOW_DAYS} targets, got {len(targets)}"
    )
    for url in targets:
        assert url.startswith(f"{CALENDAR_BASE}/20"), (
            f"URL does not look like a date-based calendar URL: {url}"
        )


# ---------------------------------------------------------------------------
# get_data — happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_extracts_title_and_datetime(monkeypatch):
    """get_data() must parse show title and datetime from the slug."""
    scraper = ComedyStoreScraper(_club())
    html = _day_html([{
        "slug": "2026-04-01t200000-0700-bassem-friends",
        "title": "Bassem & Friends",
        "ticket": "https://www.showclix.com/event/bassem-2026-april",
    }])

    async def fake_fetch(self, url: str) -> str:
        return html

    monkeypatch.setattr(ComedyStoreScraper, "fetch_html", fake_fetch)

    result = await scraper.get_data(f"{CALENDAR_BASE}/2026-04-01")

    assert isinstance(result, ComedyStorePageData)
    assert len(result.event_list) == 1
    ev = result.event_list[0]
    assert ev.title == "Bassem & Friends"
    assert ev.datetime_slug == "2026-04-01t200000-0700"
    assert "showclix.com/event/bassem-2026-april" in ev.ticket_url


@pytest.mark.asyncio
async def test_get_data_concurrent_shows_same_time_different_rooms(monkeypatch):
    """Shows starting at the same time in different rooms must both be extracted.

    Regression test for the datetime-only dedup bug: two shows at 8:00 PM share
    the same datetime_slug prefix but have different full slugs.  Both must appear
    in the result.
    """
    scraper = ComedyStoreScraper(_club())
    html = _day_html([
        {
            "slug": "2026-04-01t200000-0700-bassem-friends",
            "title": "Bassem & Friends",
            "room": "Belly Room",
            "ticket": "https://www.showclix.com/event/bassem-2026-april",
        },
        {
            "slug": "2026-04-01t200000-0700-tippy-top-tier",
            "title": "Tippy Top Tier Comedy",
            "room": "Main Room",
            "ticket": "https://www.showclix.com/event/tier-2026-april",
        },
    ])

    async def fake_fetch(self, url: str) -> str:
        return html

    monkeypatch.setattr(ComedyStoreScraper, "fetch_html", fake_fetch)

    result = await scraper.get_data(f"{CALENDAR_BASE}/2026-04-01")
    assert result is not None
    assert len(result.event_list) == 2, (
        "Both concurrent shows must be extracted — one was silently dropped by dedup"
    )
    titles = {e.title for e in result.event_list}
    assert "Bassem & Friends" in titles
    assert "Tippy Top Tier Comedy" in titles


@pytest.mark.asyncio
async def test_get_data_extracts_room(monkeypatch):
    """get_data() must include the room name, stripping the abbreviation span."""
    scraper = ComedyStoreScraper(_club())
    html = _day_html([{
        "slug": "2026-04-01t210000-0700-headliners",
        "title": "Headliners",
        "room": "Main Room",
        "ticket": "https://www.showclix.com/event/headliners-2026",
    }])

    async def fake_fetch(self, url: str) -> str:
        return html

    monkeypatch.setattr(ComedyStoreScraper, "fetch_html", fake_fetch)

    result = await scraper.get_data(f"{CALENDAR_BASE}/2026-04-01")
    assert result is not None
    assert result.event_list[0].room == "Main Room"


@pytest.mark.asyncio
async def test_get_data_sold_out_show(monkeypatch):
    """Sold-out shows must have sold_out=True and fall back to the show-page URL."""
    scraper = ComedyStoreScraper(_club())
    html = _day_html([{
        "slug": "2026-04-01t200000-0700-big-show",
        "title": "Big Show",
        "sold_out": True,
        # no ticket URL — sold out
    }])

    async def fake_fetch(self, url: str) -> str:
        return html

    monkeypatch.setattr(ComedyStoreScraper, "fetch_html", fake_fetch)

    result = await scraper.get_data(f"{CALENDAR_BASE}/2026-04-01")
    assert result is not None
    ev = result.event_list[0]
    assert ev.sold_out is True
    assert ev.ticket_url.startswith("https://thecomedystore.com/calendar/show/")


@pytest.mark.asyncio
async def test_get_data_empty_day_returns_none(monkeypatch):
    """Days with no show-item divs must return None without raising."""
    scraper = ComedyStoreScraper(_club())

    async def fake_fetch(self, url: str) -> str:
        return _empty_day_html()

    monkeypatch.setattr(ComedyStoreScraper, "fetch_html", fake_fetch)

    result = await scraper.get_data(f"{CALENDAR_BASE}/2026-04-02")
    assert result is None


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transformation_pipeline_produces_shows(monkeypatch):
    """ComedyStoreEvent.to_show() must produce valid Show objects via the transformer."""
    scraper = ComedyStoreScraper(_club())
    html = _day_html([{
        "slug": "2026-04-01t200000-0700-bassem-friends",
        "title": "Bassem & Friends",
        "ticket": "https://www.showclix.com/event/bassem-2026-april",
    }])

    async def fake_fetch(self, url: str) -> str:
        return html

    monkeypatch.setattr(ComedyStoreScraper, "fetch_html", fake_fetch)

    page_data = await scraper.get_data(f"{CALENDAR_BASE}/2026-04-01")
    assert page_data is not None

    shows = scraper.transformation_pipeline.transform(page_data)
    assert len(shows) == 1, f"Expected 1 Show from to_show(), got {len(shows)}"
    show = shows[0]
    assert show.name == "Bassem & Friends"
    assert show.club_id == 99
    assert show.date is not None
    assert show.date.year == 2026
    assert show.date.month == 4
    assert show.date.day == 1


@pytest.mark.asyncio
async def test_full_pipeline_produces_events(monkeypatch):
    """End-to-end: collect_scraping_targets() feeds get_data() → events returned."""
    scraper = ComedyStoreScraper(_club())

    shows_for_day_1 = _day_html([
        {
            "slug": "2026-04-01t200000-0700-show-a",
            "title": "Show A",
            "ticket": "https://www.showclix.com/event/show-a",
        },
        {
            "slug": "2026-04-01t220000-0700-show-b",
            "title": "Show B",
            "ticket": "https://www.showclix.com/event/show-b",
        },
    ])

    today_str = date.today().strftime("%Y-%m-%d")

    async def fake_fetch(self, url: str) -> str:
        # Return shows for today's date URL, empty for all others
        if url.endswith(today_str):
            return shows_for_day_1
        return _empty_day_html()

    monkeypatch.setattr(ComedyStoreScraper, "fetch_html", fake_fetch)

    targets = await scraper.collect_scraping_targets()
    assert len(targets) > 0

    all_events = []
    for url in targets:
        page = await scraper.get_data(url)
        if page:
            all_events.extend(page.event_list)

    assert len(all_events) == 2, (
        f"Expected 2 events from the pipeline, got {len(all_events)}"
    )
    titles = {e.title for e in all_events}
    assert "Show A" in titles
    assert "Show B" in titles


# ---------------------------------------------------------------------------
# Z UTC offset — slug with 'Z' must not be silently dropped
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_z_utc_offset_slug(monkeypatch):
    """A slug with a 'Z' UTC offset must be extracted and normalised to '+0000'.

    Regression: _SLUG_DT_RE previously only matched [+-]\\d{4} offsets, so any
    show whose slug ended in 'Z' was silently dropped (dt_m was None → continue).
    """
    scraper = ComedyStoreScraper(_club())
    html = _day_html([{
        "slug": "2026-04-01t200000Z-z-offset-show",
        "title": "Z Offset Show",
        "ticket": "https://www.showclix.com/event/z-show",
    }])

    async def fake_fetch(self, url: str) -> str:
        return html

    monkeypatch.setattr(ComedyStoreScraper, "fetch_html", fake_fetch)

    result = await scraper.get_data(f"{CALENDAR_BASE}/2026-04-01")

    assert result is not None, "Event with Z offset was silently dropped"
    assert len(result.event_list) == 1
    ev = result.event_list[0]
    assert ev.title == "Z Offset Show"
    assert ev.datetime_slug == "2026-04-01t200000+0000", (
        f"Z should be normalised to +0000, got: {ev.datetime_slug!r}"
    )


# ---------------------------------------------------------------------------
# La Jolla location — /la-jolla/calendar/show/ href prefix
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_la_jolla_collect_scraping_targets_returns_date_based_urls():
    """La Jolla collect_scraping_targets() must return date-based URLs under /la-jolla/calendar."""
    scraper = ComedyStoreScraper(_la_jolla_club())
    targets = await scraper.collect_scraping_targets()

    assert len(targets) == _SCRAPE_WINDOW_DAYS
    for url in targets:
        assert url.startswith(f"{LA_JOLLA_CALENDAR_BASE}/20"), (
            f"URL does not look like a La Jolla date-based calendar URL: {url}"
        )


@pytest.mark.asyncio
async def test_la_jolla_get_data_extracts_title_and_datetime(monkeypatch):
    """La Jolla get_data() must parse shows from /la-jolla/calendar/show/ hrefs."""
    scraper = ComedyStoreScraper(_la_jolla_club())
    html = _la_jolla_day_html([{
        "slug": "2026-04-01t190000-0700-tuesday-night-potluck",
        "title": "Tuesday Night Potluck",
        "ticket": "https://www.showclix.com/event/potluck-la-jolla",
    }])

    async def fake_fetch(self, url: str) -> str:
        return html

    monkeypatch.setattr(ComedyStoreScraper, "fetch_html", fake_fetch)

    result = await scraper.get_data(f"{LA_JOLLA_CALENDAR_BASE}/2026-04-01")

    assert isinstance(result, ComedyStorePageData)
    assert len(result.event_list) == 1
    ev = result.event_list[0]
    assert ev.title == "Tuesday Night Potluck"
    assert ev.datetime_slug == "2026-04-01t190000-0700"
    assert "showclix.com/event/potluck-la-jolla" in ev.ticket_url


@pytest.mark.asyncio
async def test_la_jolla_get_data_concurrent_shows_same_time_different_rooms(monkeypatch):
    """La Jolla concurrent shows at the same time in different rooms must both be extracted.

    Verifies the /la-jolla/ href prefix does not break the full-slug dedup logic.
    """
    scraper = ComedyStoreScraper(_la_jolla_club())
    html = _la_jolla_day_html([
        {
            "slug": "2026-04-01t200000-0700-show-a",
            "title": "Show A",
            "room": "Showroom",
            "ticket": "https://www.showclix.com/event/show-a-lj",
        },
        {
            "slug": "2026-04-01t200000-0700-show-b",
            "title": "Show B",
            "room": "Bar Stage",
            "ticket": "https://www.showclix.com/event/show-b-lj",
        },
    ])

    async def fake_fetch(self, url: str) -> str:
        return html

    monkeypatch.setattr(ComedyStoreScraper, "fetch_html", fake_fetch)

    result = await scraper.get_data(f"{LA_JOLLA_CALENDAR_BASE}/2026-04-01")
    assert result is not None
    assert len(result.event_list) == 2, (
        "Both concurrent La Jolla shows must be extracted — one was silently dropped by dedup"
    )
    titles = {e.title for e in result.event_list}
    assert "Show A" in titles
    assert "Show B" in titles


@pytest.mark.asyncio
async def test_la_jolla_get_data_sold_out_show(monkeypatch):
    """La Jolla sold-out shows must use the /la-jolla/ show-page URL as fallback."""
    scraper = ComedyStoreScraper(_la_jolla_club())
    html = _la_jolla_day_html([{
        "slug": "2026-04-01t200000-0700-big-show",
        "title": "Big Show",
        "sold_out": True,
    }])

    async def fake_fetch(self, url: str) -> str:
        return html

    monkeypatch.setattr(ComedyStoreScraper, "fetch_html", fake_fetch)

    result = await scraper.get_data(f"{LA_JOLLA_CALENDAR_BASE}/2026-04-01")
    assert result is not None
    ev = result.event_list[0]
    assert ev.sold_out is True
    assert ev.ticket_url.startswith("https://thecomedystore.com/la-jolla/calendar/show/")
