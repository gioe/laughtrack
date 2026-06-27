"""Smoke tests for the Coral Springs Center for the Arts venue scraper.

Exercises the extractor against HTML snippets matching the live
thecentercs.com markup: the server-rendered ``/events/category/comedy`` listing
(per-event ``/events/detail/<slug>`` links) and a detail page whose
``m-date__month`` / ``m-date__day`` / ``m-date__year`` spans, ``<h1 class="title">``
and eVenue ``SEGetEventInfo`` link are the source of truth. Fixture dates use a
far-future year so the past-event filter never time-bombs the suite.
"""

from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.implementations.venues.coral_springs_center.extractor import (
    CoralSpringsCenterExtractor,
)

_BASE = "https://www.thecentercs.com/events/category/comedy"
_DETAIL_URL = (
    "https://www.thecentercs.com/events/detail/"
    "colin-mochrie-and-brad-sherwood-asking-for-trouble"
)

_LISTING_HTML = """
<div class="m-eventList">
  <div class="eventItem entry">
    <a href="/events/detail/colin-mochrie-and-brad-sherwood-asking-for-trouble"
       title="More Info for Colin Mochrie and Brad Sherwood: Asking For Trouble">img</a>
    <div class="date"><span class="m-date__singleDate">
      <span class="m-date__month">Oct </span><span class="m-date__day"> 9</span>
      <span class="m-date__weekday"> / Fri</span></span></div>
  </div>
</div>
"""

# Mirrors the live markup: the show time (7:30 PM) recurs in the title-attr,
# date line and buy button, while the doors time (6:30 PM) appears once — so the
# most-frequent time is the show time.
_DETAIL_HTML = """
<div class="buttonWrapper">
  <span class="date"><span class="m-date__singleDate">
    <span class="m-date__month">Oct </span><span class="m-date__day"> 9</span>
    <span class="m-date__year">, 2099</span></span></span>
  <h1 class="title"> Colin Mochrie and Brad Sherwood: Asking For Trouble </h1>
  <div class="showtime">Doors 6:30 PM / Show 7:30 PM</div>
  <a class="tickets" target="_blank" title="Buy Tickets for October 9 2099 at 7:30 PM"
     href="https://thecenter.evenue.net/cgi-bin/ncommerce3/SEGetEventInfo?ticketCode=GS%3ACSCC%3AC24%3ACMBS01%3A&amp;linkID=pfm-coralsprings">Buy Tickets 7:30 PM</a>
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


def test_extract_comedy_detail_urls_resolves_absolute():
    urls = CoralSpringsCenterExtractor.extract_comedy_detail_urls(_LISTING_HTML, _BASE)
    assert urls == [_DETAIL_URL]


def test_parse_detail_extracts_event_fields():
    event = CoralSpringsCenterExtractor.parse_detail(_DETAIL_HTML, _DETAIL_URL)
    assert event is not None
    assert event.name == "Colin Mochrie and Brad Sherwood: Asking For Trouble"
    assert event.start_date == "2099-10-09"
    assert event.start_time == "7:30PM"  # most-frequent time = show time, not doors
    assert event.detail_url == _DETAIL_URL
    # eVenue link is HTML-unescaped (&amp; -> &)
    assert event.ticket_url is not None
    assert "&amp;" not in event.ticket_url
    assert "SEGetEventInfo" in event.ticket_url


def test_parse_detail_skips_when_no_date():
    html = '<h1 class="title">Some Comedy Night</h1><div>7:30PM</div>'
    assert CoralSpringsCenterExtractor.parse_detail(html, _DETAIL_URL) is None


def test_extract_events_end_to_end():
    events = CoralSpringsCenterExtractor.extract_events(
        _LISTING_HTML, _BASE, {_DETAIL_URL: _DETAIL_HTML}
    )
    assert len(events) == 1
    assert events[0].name.startswith("Colin Mochrie")


def test_to_show_converts_to_localized_utc():
    event = CoralSpringsCenterExtractor.parse_detail(_DETAIL_HTML, _DETAIL_URL)
    show = event.to_show(_club())
    assert show is not None
    assert show.show_page_url == _DETAIL_URL
    # to_show stores the venue-local wall-clock (7:30 PM) tz-aware; the DB layer
    # normalizes to UTC on persist. Assert the wall-clock to stay tz/DST-agnostic.
    assert show.date.hour == 19
    assert show.date.minute == 30
    assert show.date.tzinfo is not None
    assert len(show.tickets) == 1
    assert show.tickets[0].purchase_url.startswith("https://thecenter.evenue.net")
