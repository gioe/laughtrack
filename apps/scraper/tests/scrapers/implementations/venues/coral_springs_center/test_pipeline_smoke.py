"""Smoke tests for the Coral Springs Center for the Arts venue scraper.

Exercises the extractor against HTML snippets matching the live thecentercs.com
markup: the server-rendered ``/events/category/comedy`` listing (``.eventItem``
result cards holding per-event ``/events/detail/<slug>`` links) and a detail page
whose ``.m-date__singleDate`` blocks (``m-date__month`` / ``m-date__day`` /
``m-date__year``), ``<h1 class="title">`` and eVenue ``SEGetEventInfo`` link are
the source of truth. Fixture dates use a far-future year so the past-event filter
never time-bombs the suite (convention #11). Also covers the async ``get_data``
seam (per-detail error containment + empty-extraction early returns).
"""

from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.implementations.venues.coral_springs_center.data import (
    CoralSpringsCenterPageData,
)
from laughtrack.scrapers.implementations.venues.coral_springs_center.extractor import (
    CoralSpringsCenterExtractor,
)
from laughtrack.scrapers.implementations.venues.coral_springs_center.scraper import (
    CoralSpringsCenterScraper,
)

_BASE = "https://www.thecentercs.com/events/category/comedy"
_DETAIL_URL = (
    "https://www.thecentercs.com/events/detail/"
    "colin-mochrie-and-brad-sherwood-asking-for-trouble"
)

# Live listing shape: .eventItem cards inside the .eventList wrapper; the detail
# href is absolute on the live site.
_LISTING_HTML = """
<div class="eventList event_list_grid">
  <div class="eventList__wrapper list" id="list">
    <div class="eventItem entry home featured group clearfix">
      <div class="thumb">
        <a href="https://www.thecentercs.com/events/detail/colin-mochrie-and-brad-sherwood-asking-for-trouble"
           title="More Info for Colin Mochrie and Brad Sherwood: Asking For Trouble">img</a>
      </div>
    </div>
  </div>
</div>
"""

# Mirrors the live detail markup: the same date repeats across THREE
# .m-date__singleDate blocks (two with year, one weekday-only) and the show time
# (7:30 PM) recurs while the doors time (6:30 PM) appears once.
_DETAIL_HTML = """
<div class="buttonWrapper">
  <span class="date"><span class="m-date__singleDate">
    <span class="m-date__month">Oct </span><span class="m-date__day"> 9</span>
    <span class="m-date__year">, 2099</span></span></span>
  <span class="date"><span class="m-date__singleDate">
    <span class="m-date__month">Oct </span><span class="m-date__day"> 9</span>
    <span class="m-date__year">, 2099</span></span></span>
  <span class="date"><span class="m-date__singleDate">
    <span class="m-date__month">Oct </span><span class="m-date__day"> 9</span>
    <span class="m-date__weekday"> / Fri</span></span></span>
  <h1 class="title"> Colin Mochrie and Brad Sherwood: Asking For Trouble </h1>
  <div class="showtime">Doors 6:30 PM / Show 7:30 PM</div>
  <a class="tickets" target="_blank" title="Buy Tickets for October 9 2099 at 7:30 PM"
     href="https://thecenter.evenue.net/cgi-bin/ncommerce3/SEGetEventInfo?ticketCode=GS%3ACSCC%3AC24%3ACMBS01%3A&amp;linkID=pfm-coralsprings">Buy Tickets 7:30 PM</a>
</div>
"""

# A two-night touring engagement: distinct dates across two .m-date__singleDate
# blocks → one event per night.
_DETAIL_HTML_MULTINIGHT = """
<div class="buttonWrapper">
  <span class="m-date__singleDate">
    <span class="m-date__month">Oct </span><span class="m-date__day"> 10</span>
    <span class="m-date__year">, 2099</span></span>
  <span class="m-date__singleDate">
    <span class="m-date__month">Oct </span><span class="m-date__day"> 9</span>
    <span class="m-date__year">, 2099</span></span>
  <h1 class="title">Touring Comedian: Two Nights</h1>
  <div class="showtime">Doors 7:00 PM / Show 8:00 PM</div>
  <a class="tickets" title="Buy 8:00 PM"
     href="https://thecenter.evenue.net/cgi-bin/ncommerce3/SEGetEventInfo?ticketCode=TWO">Buy 8:00 PM</a>
</div>
"""


def _club() -> Club:
    return Club(
        id=999,
        name="Coral Springs Center for the Arts",
        address="2855 Coral Springs Dr",
        website="https://www.thecentercs.com",
        popularity=0,
        zip_code="33065",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )


# ---- listing extraction (container-scoped) -------------------------------

def test_extract_comedy_detail_urls_resolves_absolute():
    urls = CoralSpringsCenterExtractor.extract_comedy_detail_urls(_LISTING_HTML, _BASE)
    assert urls == [_DETAIL_URL]


def test_extract_comedy_detail_urls_ignores_links_outside_event_cards():
    """A non-comedy link in a related/featured widget outside .eventItem is dropped."""
    listing = """
    <div class="eventList__wrapper">
      <div class="eventItem entry"><a href="/events/detail/comedy-show">x</a></div>
    </div>
    <div class="relatedEvents sidebar">
      <a href="/events/detail/symphony-orchestra-gala">Non-comedy widget link</a>
    </div>
    """
    urls = CoralSpringsCenterExtractor.extract_comedy_detail_urls(listing, _BASE)
    assert urls == ["https://www.thecentercs.com/events/detail/comedy-show"]


def test_extract_comedy_detail_urls_falls_back_without_cards():
    """No .eventItem cards → whole-document scan (markup-change resilience)."""
    listing = '<div><a href="/events/detail/fallback-show">x</a></div>'
    urls = CoralSpringsCenterExtractor.extract_comedy_detail_urls(listing, _BASE)
    assert urls == ["https://www.thecentercs.com/events/detail/fallback-show"]


# ---- detail parsing (multi-date) -----------------------------------------

def test_parse_detail_dedupes_repeated_single_date():
    """The three repeated same-date blocks collapse to one event."""
    events = CoralSpringsCenterExtractor.parse_detail(_DETAIL_HTML, _DETAIL_URL)
    assert len(events) == 1
    event = events[0]
    assert event.name == "Colin Mochrie and Brad Sherwood: Asking For Trouble"
    assert event.start_date == "2099-10-09"
    assert event.start_time == "7:30PM"  # most-frequent time = show time, not doors
    assert event.detail_url == _DETAIL_URL
    assert event.ticket_url is not None
    assert "&amp;" not in event.ticket_url  # HTML-unescaped
    assert "SEGetEventInfo" in event.ticket_url


def test_parse_detail_multi_night_emits_one_event_per_date_sorted():
    events = CoralSpringsCenterExtractor.parse_detail(_DETAIL_HTML_MULTINIGHT, _DETAIL_URL)
    assert [e.start_date for e in events] == ["2099-10-09", "2099-10-10"]  # sorted
    assert {e.name for e in events} == {"Touring Comedian: Two Nights"}
    assert {e.start_time for e in events} == {"8:00PM"}


def test_parse_detail_returns_empty_when_no_date():
    html = '<h1 class="title">Some Comedy Night</h1><div>7:30PM</div>'
    assert CoralSpringsCenterExtractor.parse_detail(html, _DETAIL_URL) == []


def test_parse_detail_returns_empty_when_no_title():
    html = (
        '<span class="m-date__singleDate"><span class="m-date__month">Oct</span>'
        '<span class="m-date__day">9</span><span class="m-date__year">2099</span></span>'
    )
    assert CoralSpringsCenterExtractor.parse_detail(html, _DETAIL_URL) == []


def test_extract_events_end_to_end():
    events = CoralSpringsCenterExtractor.extract_events(
        _LISTING_HTML, _BASE, {_DETAIL_URL: _DETAIL_HTML}
    )
    assert len(events) == 1
    assert events[0].name.startswith("Colin Mochrie")


def test_to_show_converts_to_localized_wall_clock():
    events = CoralSpringsCenterExtractor.parse_detail(_DETAIL_HTML, _DETAIL_URL)
    show = events[0].to_show(_club())
    assert show is not None
    assert show.show_page_url == _DETAIL_URL
    # to_show stores the venue-local wall-clock (7:30 PM) tz-aware; the DB layer
    # normalizes to UTC on persist. Assert the wall-clock to stay tz/DST-agnostic.
    assert show.date.hour == 19
    assert show.date.minute == 30
    assert show.date.tzinfo is not None
    assert len(show.tickets) == 1
    assert show.tickets[0].purchase_url.startswith("https://thecenter.evenue.net")


# ---- async get_data: error containment + empty-extraction early returns ---


def _scraper() -> CoralSpringsCenterScraper:
    return CoralSpringsCenterScraper(_club())


def _fetch_map(mapping: dict, errors: dict | None = None):
    """Build an async fetch_html stub: url -> html, or raise from errors[url]."""
    errors = errors or {}

    async def _fetch(url: str):
        if url in errors:
            raise errors[url]
        return mapping.get(url, "")

    return _fetch


async def test_get_data_contains_per_detail_fetch_errors(monkeypatch):
    """One detail page raising on fetch must not drop the other detail pages."""
    good_url = "https://www.thecentercs.com/events/detail/good-show"
    bad_url = "https://www.thecentercs.com/events/detail/bad-show"
    listing = (
        '<div class="eventItem"><a href="/events/detail/good-show">a</a></div>'
        '<div class="eventItem"><a href="/events/detail/bad-show">b</a></div>'
    )
    scraper = _scraper()
    fetch = _fetch_map(
        {_BASE: listing, good_url: _DETAIL_HTML},
        errors={bad_url: RuntimeError("boom")},
    )
    monkeypatch.setattr(scraper, "fetch_html", fetch)

    page = await scraper.get_data(_BASE)
    assert isinstance(page, CoralSpringsCenterPageData)
    assert len(page.event_list) == 1  # the good page survived the bad one's error
    assert page.event_list[0].detail_url == good_url


async def test_get_data_returns_none_on_empty_listing(monkeypatch):
    scraper = _scraper()
    monkeypatch.setattr(scraper, "fetch_html", _fetch_map({_BASE: ""}))
    assert await scraper.get_data(_BASE) is None


async def test_get_data_returns_none_when_no_detail_urls(monkeypatch):
    scraper = _scraper()
    listing = '<div class="eventList__wrapper">no events scheduled</div>'
    monkeypatch.setattr(scraper, "fetch_html", _fetch_map({_BASE: listing}))
    assert await scraper.get_data(_BASE) is None


async def test_get_data_returns_none_when_no_parseable_events(monkeypatch):
    """Detail pages fetch fine but parse to nothing → None (not an empty page)."""
    detail_url = "https://www.thecentercs.com/events/detail/unparseable"
    listing = '<div class="eventItem"><a href="/events/detail/unparseable">x</a></div>'
    scraper = _scraper()
    monkeypatch.setattr(
        scraper,
        "fetch_html",
        _fetch_map({_BASE: listing, detail_url: "<h1 class='title'>No Date Here</h1>"}),
    )
    assert await scraper.get_data(_BASE) is None
