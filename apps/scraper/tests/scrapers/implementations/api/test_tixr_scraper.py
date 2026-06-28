"""
Tests that legacy Tixr-only venue wrappers (St. Marks, Improv Asylum) have
been absorbed into the shared Tixr scrapers.

The legacy ``StMarksScraper`` and ``ImprovAsylumScraper`` classes have been
removed; their venue rows now route through the generic ``TixrPublicCardScraper``
and ``TixrScraper`` respectively. These tests pin both halves of that
behavior:

* St. Marks resolves through the generic public-card path and never fetches
  Tixr detail pages (those are DataDome-blocked in automation).
* Improv Asylum resolves through the generic Tixr scraper and still falls
  back to the Pixl Calendar API when the Tixr group page returns no event
  URLs.
"""

import importlib.util
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

import pytest
import pytz

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.app.scraper_resolver import ScraperResolver
from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.tixr.data import TixrPageData
from laughtrack.scrapers.implementations.api.tixr.scraper import (
    TixrPublicCardScraper,
    TixrScraper,
)


ST_MARKS_CALENDAR_URL = "https://www.stmarkscomedyclub.com/calendar"
ST_MARKS_TIXR_URL = "https://www.tixr.com/groups/stmarks/events/comedy-night-12345"
ST_MARKS_MISMATCHED_TIXR_URL = "https://www.tixr.com/groups/stmarks/events/other-show-54321"

IMPROV_ASYLUM_TIXR_URL = "https://www.tixr.com/groups/improvasylum"
IMPROV_ASYLUM_PIXL_API_URL = "https://calendar.improvasylum.com/api/events/improv-asylum"


def _st_marks_club() -> Club:
    club = Club(
        id=16,
        name="St. Marks Comedy Club",
        address="",
        website="https://www.stmarkscomedyclub.com",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="tixr",
        scraper_key="tixr_public_card",
        source_url=ST_MARKS_CALENDAR_URL,
        external_id=None,
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _improv_asylum_club() -> Club:
    club = Club(
        id=141,
        name="Improv Asylum",
        address="216 Hanover St",
        website="https://improvasylum.com",
        popularity=0,
        zip_code="02113",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="tixr",
        scraper_key="tixr",
        source_url=IMPROV_ASYLUM_TIXR_URL,
        external_id=None,
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _st_marks_card_date() -> datetime:
    """Tomorrow in the club's timezone. The card carries no year, and
    ``_parse_public_card_datetime`` resolves month/day against the real
    current date — rolling past dates to next year and rejecting anything
    beyond ``_MAX_YEAR_ROLLOVER_DAYS``. A hardcoded month/day therefore
    becomes unparseable the moment the card's own showtime passes (the
    original 'Jun 10' fixture started failing at 7:30 pm ET on June 10),
    so the fixture must always render a future date.
    """
    tz = pytz.timezone("America/New_York")
    return datetime.now(tz) + timedelta(days=1)


def _st_marks_card_html() -> str:
    """Webflow-style card from St. Marks' /calendar page with full event data."""
    card_date = _st_marks_card_date()
    return f"""<html><body>
<div class="event-item w-dyn-item" role="listitem">
  <a class="ticket-links grid w-inline-block" href="{ST_MARKS_TIXR_URL}">
    <div class="text-block-35">St. Marks Comedy Night</div>
    <div class="event-card grid">
      <div class="date-info grid">
        <div class="month grid date">{card_date.strftime("%a")}</div>
        <div class="month grid">{card_date.strftime("%b")}</div>
        <div class="month grid custom-filter">{card_date.strftime("%b")}</div>
        <div class="month day grid">{card_date.day}</div>
        <div class="month day time">7:30 pm</div>
      </div>
    </div>
  </a>
</div>
</body></html>"""


def _st_marks_card_html_with_jsonld_offer(
    *,
    offer_url: str = ST_MARKS_TIXR_URL,
    price: str | None = "25.00",
) -> str:
    price_field = "" if price is None else f'"price": "{price}",'
    card_date = _st_marks_card_date()
    return f"""<html><head>
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "Event",
  "name": "St. Marks Comedy Night",
  "offers": {{
    "@type": "Offer",
    {price_field}
    "priceCurrency": "USD",
    "url": "{offer_url}"
  }}
}}
</script>
</head><body>
<div class="event-item w-dyn-item" role="listitem">
  <a class="ticket-links grid w-inline-block" href="{ST_MARKS_TIXR_URL}">
    <div class="text-block-35">St. Marks Comedy Night</div>
    <div class="event-card grid">
      <div class="date-info grid">
        <div class="month grid date">{card_date.strftime("%a")}</div>
        <div class="month grid">{card_date.strftime("%b")}</div>
        <div class="month grid custom-filter">{card_date.strftime("%b")}</div>
        <div class="month day grid">{card_date.day}</div>
        <div class="month day time">7:30 pm</div>
      </div>
    </div>
  </a>
</div>
</body></html>"""


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
                "ticketUrl": (
                    "https://www.tixr.com/groups/improvasylum/events/"
                    "improv-asylum-s-main-stage-show-169028"
                ),
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


# ---------------------------------------------------------------------------
# Criterion 6733 — St. Marks resolves through the generic Tixr scraper path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_st_marks_uses_generic_tixr_path(monkeypatch):
    """The legacy ``st_marks`` wrapper key is unregistered, and St. Marks'
    Webflow calendar page is parsed by the shared ``TixrPublicCardScraper``
    without any fetch against Tixr-hosted event detail pages.
    """
    resolver = ScraperResolver()
    assert resolver.get("st_marks") is None, (
        "Legacy 'st_marks' scraper key is still registered — venue wrapper "
        "should be removed in favor of the generic Tixr scrapers"
    )
    assert resolver.get("tixr_public_card") is TixrPublicCardScraper

    scraper = TixrPublicCardScraper(_st_marks_club())

    async def fake_fetch_html(self, url, **kwargs):
        return _st_marks_card_html()

    monkeypatch.setattr(TixrPublicCardScraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(
        scraper.tixr_client,
        "get_event_detail_from_url",
        AsyncMock(side_effect=AssertionError("Tixr detail pages should not be fetched")),
    )

    result = await scraper.get_data(ST_MARKS_CALENDAR_URL)

    assert isinstance(result, TixrPageData)
    assert result.get_event_count() == 1
    event = result.event_list[0]
    assert event.title == "St. Marks Comedy Night"
    assert event.source_url == ST_MARKS_TIXR_URL
    assert event.show.show_page_url == ST_MARKS_TIXR_URL
    assert event.show.tickets[0].purchase_url == ST_MARKS_TIXR_URL
    assert event.show.date.hour == 19
    assert event.show.date.minute == 30
    scraper.tixr_client.get_event_detail_from_url.assert_not_called()


@pytest.mark.asyncio
async def test_st_marks_webflow_jsonld_offer_price_is_emitted(monkeypatch):
    scraper = TixrPublicCardScraper(_st_marks_club())

    async def fake_fetch_html(self, url, **kwargs):
        return _st_marks_card_html_with_jsonld_offer(price="25.00")

    monkeypatch.setattr(TixrPublicCardScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(ST_MARKS_CALENDAR_URL)

    assert result is not None
    ticket = result.event_list[0].show.tickets[0]
    assert ticket.purchase_url == ST_MARKS_TIXR_URL
    assert ticket.price == 25.0


@pytest.mark.asyncio
async def test_st_marks_webflow_jsonld_missing_offer_price_preserves_none(monkeypatch):
    scraper = TixrPublicCardScraper(_st_marks_club())

    async def fake_fetch_html(self, url, **kwargs):
        return _st_marks_card_html_with_jsonld_offer(price=None)

    monkeypatch.setattr(TixrPublicCardScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(ST_MARKS_CALENDAR_URL)

    assert result is not None
    assert result.event_list[0].show.tickets[0].price is None


@pytest.mark.asyncio
async def test_st_marks_webflow_jsonld_url_mismatch_keeps_price_none(monkeypatch):
    scraper = TixrPublicCardScraper(_st_marks_club())

    async def fake_fetch_html(self, url, **kwargs):
        return _st_marks_card_html_with_jsonld_offer(offer_url=ST_MARKS_MISMATCHED_TIXR_URL, price="30.00")

    monkeypatch.setattr(TixrPublicCardScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(ST_MARKS_CALENDAR_URL)

    assert result is not None
    ticket = result.event_list[0].show.tickets[0]
    assert ticket.purchase_url == ST_MARKS_TIXR_URL
    assert ticket.price is None


# ---------------------------------------------------------------------------
# Criterion 6734 — Improv Asylum generic Tixr path preserves the Pixl fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_improv_asylum_generic_path_preserves_pixl_fallback(monkeypatch):
    """The legacy ``improv_asylum`` wrapper key is unregistered, and the
    generic ``TixrScraper`` still falls back to ``calendar.improvasylum.com``
    when the Tixr group page returns no extractable event URLs (the
    DataDome-blocked path).
    """
    resolver = ScraperResolver()
    assert resolver.get("improv_asylum") is None, (
        "Legacy 'improv_asylum' scraper key is still registered — venue "
        "wrapper should be removed in favor of the generic Tixr scraper"
    )
    assert resolver.get("tixr") is TixrScraper

    scraper = TixrScraper(_improv_asylum_club())

    async def fake_fetch_calendar_html(url):
        return "<html><title>tixr.com</title><body>DataDome challenge</body></html>"

    pixl_url_seen: list[str] = []

    async def fake_fetch_json(url, **kwargs):
        pixl_url_seen.append(url)
        return _improv_asylum_pixl_response()

    monkeypatch.setattr(scraper, "_fetch_calendar_html", fake_fetch_calendar_html)
    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)
    scraper.tixr_client.get_event_detail_from_url = AsyncMock()

    result = await scraper.get_data(IMPROV_ASYLUM_TIXR_URL)

    assert pixl_url_seen == [IMPROV_ASYLUM_PIXL_API_URL]
    assert isinstance(result, TixrPageData)
    assert len(result.event_list) == 1
    event = result.event_list[0]
    assert event.title == "Improv Asylum's Main Stage Show"
    assert event.event_id == "169028"
    assert event.show.date.isoformat() == "2026-05-08T19:00:00-04:00"
    assert event.show.show_page_url == (
        "https://www.tixr.com/groups/improvasylum/events/"
        "improv-asylum-s-main-stage-show-169028"
    )
    assert [ticket.type for ticket in event.show.tickets] == [
        "General Admission",
        "Premium",
    ]
    assert [ticket.price for ticket in event.show.tickets] == [33.54, 37.18]
    scraper.tixr_client.get_event_detail_from_url.assert_not_called()


# ---------------------------------------------------------------------------
# The Black Buzzard (TASK-3384) — Webflow .event-item card variant with
# absolute (year-bearing) dates resolves through tixr_public_card without
# fetching Tixr detail pages.
# ---------------------------------------------------------------------------

BUZZARD_CALENDAR_URL = "https://www.theblackbuzzard.com/"
BUZZARD_TIXR_URL = "https://tixr.com/e/183458"


def _black_buzzard_club() -> Club:
    club = Club(
        id=4099,
        name="The Black Buzzard at Oskar Blues",
        address="1624 Market St",
        website="https://www.theblackbuzzard.com",
        popularity=0,
        zip_code="80202",
        phone_number="",
        visible=True,
        timezone="America/Denver",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="tixr",
        scraper_key="tixr_public_card",
        source_url=BUZZARD_CALENDAR_URL,
        external_id=None,
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _black_buzzard_card_html() -> str:
    """Two real Black Buzzard Webflow ``.event-item`` cards from the homepage.

    The card template differs from St. Marks: the title lives in
    ``.main-title-hover-2``, the absolute date in ``.date-2.lrg``, and the
    time in the second ``.long-date .date-2.sml`` node. Per-card JSON-LD
    supplies the offer price keyed by the Tixr ticket URL.
    """
    return f"""<html><body>
<div class="event-item w-dyn-item" role="listitem">
  <div class="schema w-embed w-script">
    <script type="application/ld+json">
    {{
      "@context": "https://schema.org",
      "@type": "Event",
      "name": "Max Meisel, Phil Coan - Stand Up Comedy",
      "startDate": "Jul 15, 2026",
      "offers": {{
        "@type": "Offer",
        "name": "General Admission",
        "price": "20.00",
        "priceCurrency": "USD",
        "url": "{BUZZARD_TIXR_URL}"
      }}
    }}
    </script>
  </div>
  <a class="row-clickto-ticket w-inline-block" href="{BUZZARD_TIXR_URL}" target="_blank"></a>
  <div class="event-card-2">
    <div class="div-stack">
      <div class="content-div date-div">
        <div class="date-2 lrg" fs-cmsfilter-field="date">Jul 15, 2026</div>
        <div class="long-date">
          <div class="date-2 sml">Wednesday</div>
          <div class="date-2 comma">,</div>
          <div class="date-2 sml">8:00 pm</div>
        </div>
      </div>
    </div>
    <div class="div-stack">
      <div class="content-div info">
        <div class="main-title-hover-2" fs-cmsfilter-field="artist">Max Meisel, Phil Coan - Stand Up Comedy</div>
        <div class="headlin-2" fs-cmsfilter-field="venue">The Black Buzzard at Oskar Blues Denver</div>
      </div>
      <div class="content-div cta">
        <a class="desktop-button tix center w-button" href="{BUZZARD_TIXR_URL}" target="_blank">buy TICKETS</a>
        <a class="desktop-button tix white w-button" href="/events/max-meisel---stand-up-comedy-denver">more info</a>
      </div>
    </div>
  </div>
</div>
<div class="event-item w-dyn-item" role="listitem">
  <a class="row-clickto-ticket w-inline-block" href="https://tixr.com/e/192155" target="_blank"></a>
  <div class="event-card-2">
    <div class="div-stack">
      <div class="content-div date-div">
        <div class="date-2 lrg" fs-cmsfilter-field="date">Sep 11, 2026</div>
        <div class="long-date">
          <div class="date-2 sml">Friday</div>
          <div class="date-2 comma">,</div>
          <div class="date-2 sml">7:00 pm</div>
        </div>
      </div>
    </div>
    <div class="div-stack">
      <div class="content-div info">
        <div class="main-title-hover-2" fs-cmsfilter-field="artist">John Caparulo - Stand Up Comedy (Night 1)</div>
      </div>
      <div class="content-div cta">
        <a class="desktop-button tix center w-button" href="https://tixr.com/e/192155" target="_blank">buy TICKETS</a>
      </div>
    </div>
  </div>
</div>
</body></html>"""


# ---------------------------------------------------------------------------
# Phil Long Music Hall (TASK-3429) — mixed-use Tixr music hall whose Webflow
# `.day-card` / `.b-show` calendar carries complete venue-owned cards. Only the
# stand-up shows survive the opt-in `include_title_patterns` comedy allowlist;
# Tixr detail pages are never fetched.
# ---------------------------------------------------------------------------

PHIL_LONG_CALENDAR_URL = "https://www.phillongmusichall.com/calendar"
PHIL_LONG_COMEDY_TIXR_URL = "https://tixr.com/e/195458"
PHIL_LONG_CONCERT_TIXR_URL = "https://tixr.com/e/182410"


def _phil_long_club() -> Club:
    club = Club(
        id=4200,
        name="Phil Long Music Hall at Bourbon Brothers",
        address="13071 Bass Pro Dr",
        website="https://www.phillongmusichall.com",
        popularity=0,
        zip_code="80921",
        phone_number="",
        visible=True,
        timezone="America/Denver",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="tixr",
        scraper_key="tixr_public_card",
        source_url=PHIL_LONG_CALENDAR_URL,
        external_id=None,
        metadata={
            "include_title_patterns": [
                "comedy",
                "comedian",
                "stand[ -]?up",
            ]
        },
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _phil_long_calendar_html() -> str:
    """One comedy `.day-card` + one concert `.day-card`, matching the real
    phillongmusichall.com/calendar Webflow markup."""
    return f"""<html><body>
<div class="day-card">
  <div class="event-info">
    <div class="event-info_dates-and-name">
      <div class="event-info_dates">
        <p class="b-venue date">October 23, 2026</p>
        <div class="calendar_dates-dash">|</div>
        <p class="b-venue date">8:00 pm</p>
        <p fs-cmsfilter-field="month" class="b-venue filter">October</p>
      </div>
      <div class="b-show">Comedy Night with Don McMillan</div>
      <div class="event-info_featuring-and-button">
        <div class="event-info_featuring-wrapper">
          <p class="b-venue name underline underline-white">Featuring:</p>
          <p fs-cmsfilter-field="venue" class="b-venue name">Don McMillan</p>
        </div>
      </div>
    </div>
    <div class="button-group is-right">
      <a href="{PHIL_LONG_COMEDY_TIXR_URL}" class="button">Get Tickets</a>
    </div>
  </div>
</div>
<div class="day-card">
  <div class="event-info">
    <div class="event-info_dates-and-name">
      <div class="event-info_dates">
        <p class="b-venue date">September 19, 2026</p>
        <div class="calendar_dates-dash">|</div>
        <p class="b-venue date">7:00 pm</p>
        <p fs-cmsfilter-field="month" class="b-venue filter">September</p>
      </div>
      <div class="b-show">Thunderstruck - A Tribute to ACDC</div>
    </div>
    <div class="button-group is-right">
      <a href="{PHIL_LONG_CONCERT_TIXR_URL}" class="button">Get Tickets</a>
    </div>
  </div>
</div>
</body></html>"""


@pytest.mark.asyncio
async def test_phil_long_keeps_only_comedy_via_title_filter(monkeypatch):
    """Phil Long's Webflow `.day-card` calendar parses through the shared
    public-card path; the opt-in comedy allowlist drops the concert and keeps
    only the stand-up show, and Tixr detail pages are never fetched."""
    scraper = TixrPublicCardScraper(_phil_long_club())

    async def fake_fetch_html(self, url, **kwargs):
        return _phil_long_calendar_html()

    monkeypatch.setattr(TixrPublicCardScraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(
        scraper.tixr_client,
        "get_event_detail_from_url",
        AsyncMock(side_effect=AssertionError("Tixr detail pages should not be fetched")),
    )

    result = await scraper.get_data(PHIL_LONG_CALENDAR_URL)

    assert isinstance(result, TixrPageData)
    assert result.get_event_count() == 1
    event = result.event_list[0]
    assert event.title == "Comedy Night with Don McMillan"
    assert event.event_id == "195458"
    assert event.source_url == PHIL_LONG_COMEDY_TIXR_URL
    # Absolute-dated card → unambiguous localized datetime (America/Denver, -06:00 in Oct).
    assert event.show.date.isoformat() == "2026-10-23T20:00:00-06:00"
    assert event.show.lineup == ["Don McMillan"]
    scraper.tixr_client.get_event_detail_from_url.assert_not_called()


@pytest.mark.asyncio
async def test_phil_long_parses_all_cards_without_title_filter(monkeypatch):
    """Without the opt-in title filter the `.day-card` parser returns every
    card (the filter is off by default, so pure-comedy Tixr sources are
    unchanged)."""
    club = _phil_long_club()
    club.active_scraping_source.metadata = {}
    scraper = TixrPublicCardScraper(club)

    async def fake_fetch_html(self, url, **kwargs):
        return _phil_long_calendar_html()

    monkeypatch.setattr(TixrPublicCardScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(PHIL_LONG_CALENDAR_URL)

    assert isinstance(result, TixrPageData)
    assert {e.title for e in result.event_list} == {
        "Comedy Night with Don McMillan",
        "Thunderstruck - A Tribute to ACDC",
    }


@pytest.mark.asyncio
async def test_black_buzzard_uses_generic_public_card_path(monkeypatch):
    """The Black Buzzard's Webflow homepage parses through the shared
    ``TixrPublicCardScraper`` (absolute-dated ``.event-item`` variant) without
    any fetch against Tixr-hosted event detail pages."""
    resolver = ScraperResolver()
    assert resolver.get("tixr_public_card") is TixrPublicCardScraper

    scraper = TixrPublicCardScraper(_black_buzzard_club())

    async def fake_fetch_html(self, url, **kwargs):
        return _black_buzzard_card_html()

    monkeypatch.setattr(TixrPublicCardScraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(
        scraper.tixr_client,
        "get_event_detail_from_url",
        AsyncMock(side_effect=AssertionError("Tixr detail pages should not be fetched")),
    )

    result = await scraper.get_data(BUZZARD_CALENDAR_URL)

    assert isinstance(result, TixrPageData)
    assert result.get_event_count() == 2

    by_id = {event.event_id: event for event in result.event_list}
    assert set(by_id) == {"183458", "192155"}

    max_meisel = by_id["183458"]
    assert max_meisel.title == "Max Meisel, Phil Coan - Stand Up Comedy"
    assert max_meisel.source_url == BUZZARD_TIXR_URL
    # Absolute-dated card → unambiguous localized datetime (America/Denver, -06:00 in July).
    assert max_meisel.show.date.isoformat() == "2026-07-15T20:00:00-06:00"
    # Price comes from the per-card JSON-LD offer keyed by the Tixr URL.
    assert [ticket.price for ticket in max_meisel.show.tickets] == [20.00]

    caparulo = by_id["192155"]
    assert caparulo.title == "John Caparulo - Stand Up Comedy (Night 1)"
    assert caparulo.show.date.isoformat() == "2026-09-11T19:00:00-06:00"
    # No JSON-LD block for this card → price is None, ticket still emitted.
    assert [ticket.price for ticket in caparulo.show.tickets] == [None]
