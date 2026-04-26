"""
Pipeline smoke tests for ComedyMothershipScraper and ComedyMothershipEvent.

Exercises the HTML extraction path against minimal fixtures that mirror the
real comedymothership.com/shows structure, and unit-tests the
ComedyMothershipEvent.to_show() transformation path.
"""

import importlib.util

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.comedy_mothership import ComedyMothershipEvent
from laughtrack.scrapers.implementations.venues.comedy_mothership.extractor import (
    ComedyMothershipEventExtractor,
)
from laughtrack.scrapers.implementations.venues.comedy_mothership.data import (
    ComedyMothershipPageData,
)
from laughtrack.scrapers.implementations.venues.comedy_mothership import (
    scraper as _scraper_mod,
)
from laughtrack.scrapers.implementations.venues.comedy_mothership.scraper import (
    ComedyMothershipScraper,
)

SHOWS_URL = "https://comedymothership.com/shows"


def _club() -> Club:
    _c = Club(id=1, name='Comedy Mothership', address='320 E 6th St', website='https://comedymothership.com', popularity=0, zip_code='78701', phone_number='', visible=True, timezone='America/Chicago')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url=SHOWS_URL, external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _fixture_html() -> str:
    """
    Minimal HTML fixture mirroring the real Comedy Mothership shows page structure.
    Contains three shows: a headliner, a generic showcase, and an "and Friends" show.
    """
    return """<html><body><ul>
  <li>
    <div class="EventCard_eventCard__abc">
      <div class="EventCard_textWrapper__xyz">
        <div class="EventCard_titleWrapper__def">
          <div class="h6">Wednesday, Apr 09</div>
          <h3>Lenny Clarke</h3>
        </div>
        <ul class="EventCard_detailsWrapper__ghi">
          <li>7:00 PM - 9:00 PM</li>
          <li>FAT MAN</li>
          <li>General Admission</li>
        </ul>
        <button>Buy Tickets</button>
        <a href="https://comedymothership.com/shows/100001">Share Event</a>
      </div>
    </div>
  </li>
  <li>
    <div class="EventCard_eventCard__abc">
      <div class="EventCard_textWrapper__xyz">
        <div class="EventCard_titleWrapper__def">
          <div class="h6">Wednesday, Apr 09</div>
          <h3>Comedy Mothership Showcase</h3>
        </div>
        <ul class="EventCard_detailsWrapper__ghi">
          <li>7:30 PM - 9:30 PM</li>
          <li>LITTLE BOY</li>
          <li>General Admission</li>
        </ul>
        <button>Sold Out</button>
        <a href="https://comedymothership.com/shows/100002">Share Event</a>
      </div>
    </div>
  </li>
  <li>
    <div class="EventCard_eventCard__abc">
      <div class="EventCard_textWrapper__xyz">
        <div class="EventCard_titleWrapper__def">
          <div class="h6">Thursday, Apr 10</div>
          <h3>Ron White and Friends</h3>
        </div>
        <ul class="EventCard_detailsWrapper__ghi">
          <li>10:00 PM - 12:00 AM</li>
          <li>FAT MAN</li>
          <li>General Admission</li>
        </ul>
        <button>Buy Tickets</button>
        <a href="https://comedymothership.com/shows/100003">Share Event</a>
      </div>
    </div>
  </li>
</ul></body></html>"""


def _concurrent_html() -> str:
    """
    HTML fixture with two shows starting at the same time in different rooms.
    Used to verify that concurrent shows are not deduplicated by datetime alone.
    """
    return """<html><body><ul>
  <li>
    <div class="EventCard_eventCard__abc">
      <div class="EventCard_textWrapper__xyz">
        <div class="EventCard_titleWrapper__def">
          <div class="h6">Friday, Apr 11</div>
          <h3>Mark Normand</h3>
        </div>
        <ul class="EventCard_detailsWrapper__ghi">
          <li>8:00 PM - 10:00 PM</li>
          <li>FAT MAN</li>
          <li>General Admission</li>
        </ul>
        <button>Buy Tickets</button>
        <a href="https://comedymothership.com/shows/200001">Share Event</a>
      </div>
    </div>
  </li>
  <li>
    <div class="EventCard_eventCard__abc">
      <div class="EventCard_textWrapper__xyz">
        <div class="EventCard_titleWrapper__def">
          <div class="h6">Friday, Apr 11</div>
          <h3>Kill Tony</h3>
        </div>
        <ul class="EventCard_detailsWrapper__ghi">
          <li>8:00 PM - 11:00 PM</li>
          <li>LITTLE BOY</li>
          <li>General Admission</li>
        </ul>
        <button>Buy Tickets</button>
        <a href="https://comedymothership.com/shows/200002">Share Event</a>
      </div>
    </div>
  </li>
</ul></body></html>"""


# ---------------------------------------------------------------------------
# Extractor unit tests
# ---------------------------------------------------------------------------


def test_extractor_parses_headliner_show():
    """extract_shows() parses a headliner show with date, time, room, and performer."""
    events = ComedyMothershipEventExtractor.extract_shows(_fixture_html(), "America/Chicago")

    lenny = next((e for e in events if e.show_id == "100001"), None)
    assert lenny is not None
    assert lenny.title == "Lenny Clarke"
    assert "Apr 09" in lenny.date_str or "Apr 9" in lenny.date_str
    assert "7:00 PM" in lenny.time_str
    assert lenny.room == "FAT MAN"
    assert lenny.performers == ["Lenny Clarke"]
    assert lenny.sold_out is False


def test_extractor_generic_show_has_no_performers():
    """extract_shows() returns [] performers for a generic show title."""
    events = ComedyMothershipEventExtractor.extract_shows(_fixture_html(), "America/Chicago")

    showcase = next((e for e in events if e.show_id == "100002"), None)
    assert showcase is not None
    assert showcase.title == "Comedy Mothership Showcase"
    assert showcase.performers == []
    assert showcase.sold_out is True


def test_extractor_and_friends_strips_suffix():
    """extract_shows() strips ' and Friends' and returns the headliner name."""
    events = ComedyMothershipEventExtractor.extract_shows(_fixture_html(), "America/Chicago")

    ron = next((e for e in events if e.show_id == "100003"), None)
    assert ron is not None
    assert ron.title == "Ron White and Friends"
    assert ron.performers == ["Ron White"]


def test_extractor_returns_all_three_shows():
    """extract_shows() extracts all three shows from the fixture HTML."""
    events = ComedyMothershipEventExtractor.extract_shows(_fixture_html(), "America/Chicago")

    assert len(events) == 3
    ids = {e.show_id for e in events}
    assert ids == {"100001", "100002", "100003"}


def test_extractor_concurrent_shows_same_time_different_rooms():
    """
    Both concurrent shows at 8 PM in different rooms must be extracted.

    A dedup bug that keys on datetime only would silently drop one show.
    """
    events = ComedyMothershipEventExtractor.extract_shows(_concurrent_html(), "America/Chicago")

    assert len(events) == 2, "Both concurrent shows must be extracted"
    ids = {e.show_id for e in events}
    assert "200001" in ids
    assert "200002" in ids
    rooms = {e.room for e in events}
    assert "FAT MAN" in rooms
    assert "LITTLE BOY" in rooms


# ---------------------------------------------------------------------------
# Performer extraction unit tests
# ---------------------------------------------------------------------------


def test_extract_performers_headliner():
    """_extract_performers() returns the comedian's name for a plain headliner title."""
    assert ComedyMothershipEventExtractor._extract_performers("Lenny Clarke") == ["Lenny Clarke"]


def test_extract_performers_and_friends():
    """_extract_performers() strips ' and Friends' suffix."""
    assert ComedyMothershipEventExtractor._extract_performers("Ron White and Friends") == ["Ron White"]


def test_extract_performers_and_friend_singular():
    """_extract_performers() strips ' and Friend' (singular) suffix."""
    assert ComedyMothershipEventExtractor._extract_performers("Joe Rogan and Friend") == ["Joe Rogan"]


def test_extract_performers_generic_showcase():
    """_extract_performers() returns [] for a generic showcase title."""
    assert ComedyMothershipEventExtractor._extract_performers("Comedy Mothership Showcase") == []


def test_extract_performers_open_mic():
    """_extract_performers() returns [] for an open mic title."""
    assert ComedyMothershipEventExtractor._extract_performers("Mothership Open Mic And Crew Show") == []


def test_extract_performers_kill_tony():
    """_extract_performers() returns [] for Kill Tony (contains 'kill tony')."""
    assert ComedyMothershipEventExtractor._extract_performers("Kill Tony") == []


def test_extract_performers_presents():
    """_extract_performers() returns [] for titles containing 'Presents:'."""
    result = ComedyMothershipEventExtractor._extract_performers(
        "Adam Ray Presents: Randolph Davies Live"
    )
    assert result == []


# ---------------------------------------------------------------------------
# ComedyMothershipEvent.to_show() unit tests
# ---------------------------------------------------------------------------


def _make_event(
    show_id="100001",
    title="Lenny Clarke",
    date_str="Wednesday, Apr 09",
    time_str="7:00 PM - 9:00 PM",
    room="FAT MAN",
    timezone="America/Chicago",
    performers=None,
    sold_out=False,
) -> ComedyMothershipEvent:
    return ComedyMothershipEvent(
        show_id=show_id,
        title=title,
        date_str=date_str,
        time_str=time_str,
        room=room,
        timezone=timezone,
        performers=performers if performers is not None else ["Lenny Clarke"],
        sold_out=sold_out,
    )


def test_to_show_returns_show_with_correct_name():
    """to_show() produces a Show with the correct name."""
    event = _make_event(title="Lenny Clarke")
    show = event.to_show(_club())

    assert show is not None
    assert show.name == "Lenny Clarke"


def test_to_show_correct_date_components():
    """to_show() produces a Show with the correct month and day."""
    event = _make_event(date_str="Wednesday, Apr 09", time_str="7:00 PM - 9:00 PM")
    show = event.to_show(_club())

    assert show is not None
    assert show.date.month == 4
    assert show.date.day == 9


def test_to_show_correct_time():
    """to_show() sets the hour correctly from the time string."""
    event = _make_event(time_str="7:00 PM - 9:00 PM")
    show = event.to_show(_club())

    assert show is not None
    assert show.date.hour == 19  # 7 PM in local time, stored as UTC offset


def test_to_show_ticket_url_uses_show_id():
    """to_show() constructs the ticket URL from show_id."""
    event = _make_event(show_id="100001")
    show = event.to_show(_club())

    assert show is not None
    assert len(show.tickets) == 1
    assert "100001" in show.tickets[0].purchase_url


def test_to_show_sold_out_flag_propagated():
    """to_show() sets sold_out=True on the ticket when the event is sold out."""
    event = _make_event(sold_out=True)
    show = event.to_show(_club())

    assert show is not None
    assert len(show.tickets) == 1
    assert show.tickets[0].sold_out is True


def test_to_show_not_sold_out_by_default():
    """to_show() sets sold_out=False on the ticket for a normal event."""
    event = _make_event(sold_out=False)
    show = event.to_show(_club())

    assert show is not None
    assert len(show.tickets) == 1
    assert show.tickets[0].sold_out is False


def test_to_show_returns_none_on_missing_date():
    """to_show() returns None when date_str cannot be parsed."""
    event = _make_event(date_str="")
    show = event.to_show(_club())

    assert show is None


def test_to_show_returns_none_on_missing_time():
    """to_show() returns None when time_str contains no parseable time."""
    event = _make_event(time_str="TBD")
    show = event.to_show(_club())

    assert show is None


def test_to_show_sets_room():
    """to_show() sets the room on the returned Show."""
    event = _make_event(room="FAT MAN")
    show = event.to_show(_club())

    assert show is not None
    assert show.room == "FAT MAN"


# ---------------------------------------------------------------------------
# get_data() scraper integration tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_events(monkeypatch):
    """get_data() fetches HTML and returns ComedyMothershipPageData with events."""
    scraper = ComedyMothershipScraper(_club())

    async def fake_fetch(session, url, **kwargs):
        return _fixture_html()

    monkeypatch.setattr(_scraper_mod, "HttpClient", type("HC", (), {"fetch_html": staticmethod(fake_fetch)}))

    result = await scraper.get_data(SHOWS_URL)

    assert isinstance(result, ComedyMothershipPageData)
    assert len(result.event_list) == 3


@pytest.mark.asyncio
async def test_get_data_deduplicates_across_pages(monkeypatch):
    """get_data() deduplicates events by show_id across multiple page fetches."""
    scraper = ComedyMothershipScraper(_club())
    call_count = 0

    async def fake_fetch(session, url, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _fixture_html()
        # Second page returns same events → should all be deduped
        return _fixture_html()

    monkeypatch.setattr(_scraper_mod, "HttpClient", type("HC", (), {"fetch_html": staticmethod(fake_fetch)}))

    result = await scraper.get_data(SHOWS_URL)

    assert result is not None
    # Only 3 unique show IDs despite duplicate page content
    assert len(result.event_list) == 3


@pytest.mark.asyncio
async def test_get_data_returns_none_when_no_events(monkeypatch):
    """get_data() returns None when no events are found."""
    scraper = ComedyMothershipScraper(_club())

    async def fake_fetch(session, url, **kwargs):
        return "<html><body><p>No shows.</p></body></html>"

    monkeypatch.setattr(_scraper_mod, "HttpClient", type("HC", (), {"fetch_html": staticmethod(fake_fetch)}))

    result = await scraper.get_data(SHOWS_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_when_fetch_fails(monkeypatch):
    """get_data() returns None when HttpClient.fetch_html returns None."""
    scraper = ComedyMothershipScraper(_club())

    async def fake_fetch(session, url, **kwargs):
        return None

    monkeypatch.setattr(_scraper_mod, "HttpClient", type("HC", (), {"fetch_html": staticmethod(fake_fetch)}))

    result = await scraper.get_data(SHOWS_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_stops_pagination_on_empty_page(monkeypatch):
    """get_data() stops fetching further pages when a page returns no events."""
    scraper = ComedyMothershipScraper(_club())
    call_count = 0

    async def fake_fetch(session, url, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _fixture_html()
        # Subsequent pages are empty → pagination should stop
        return "<html><body></body></html>"

    monkeypatch.setattr(_scraper_mod, "HttpClient", type("HC", (), {"fetch_html": staticmethod(fake_fetch)}))

    result = await scraper.get_data(SHOWS_URL)

    assert result is not None
    assert len(result.event_list) == 3
    assert call_count == 2  # fetched page 1 (events) and page 2 (empty → stop)
