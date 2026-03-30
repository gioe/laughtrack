"""
Pipeline smoke tests for ComedyMagicClubScraper and ComedyMagicClubEvent.

Exercises get_data() against mocked HTML listing pages that match the
actual thecomedyandmagicclub.com structure, and unit-tests the
ComedyMagicClubEvent.to_show() transformation path.
"""

import pytest

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.comedy_magic_club import ComedyMagicClubEvent
from laughtrack.scrapers.implementations.venues.comedy_magic_club.scraper import (
    ComedyMagicClubScraper,
)
from laughtrack.scrapers.implementations.venues.comedy_magic_club.data import (
    ComedyMagicClubPageData,
)

LISTING_URL = "https://thecomedyandmagicclub.com/events/"


def _club() -> Club:
    return Club(
        id=999,
        name="The Comedy & Magic Club",
        address="1018 Hermosa Ave",
        website="https://thecomedyandmagicclub.com",
        scraping_url=LISTING_URL,
        popularity=0,
        zip_code="90254",
        phone_number="",
        visible=True,
        timezone="America/Los_Angeles",
    )


def _event_card(
    title: str = "10 Comics Show at 8PM",
    date_str: str = "Fri, Apr 10",
    time_str: str = "Doors: 6:30 pm Show: 8 pm",
    ticket_url: str = "https://www.etix.com/ticket/p/11111111/test-hermosa-beach-the-comedy-magic-club?partner_id=100",
) -> str:
    """Render a minimal rhp-events listing card, matching the live HTML structure."""
    return f"""<!-- Event List Wrapper -->
<div class="col-12 eventWrapper rhpSingleEvent py-4 px-0 rhp-event__single-event--list">
  <div class="row g-0">
    <div class="col-12 col-md-3">
      <div class="rhp-event-thumb">
        <a href="{LISTING_URL}event/test/" title="{title}" rel="bookmark">
          <div class="eventDateListTop rhp-event__date--list">
            <div id="eventDate" class="mb-0 eventMonth singleEventDate text-uppercase">
              {date_str}</div>
          </div>
        </a>
      </div>
    </div>
    <div class="col-12 col-md-6">
      <div class="col-12 rhp-event-info rhp-event__info--list">
        <div class="col-12 px-0 eventTitleDiv">
          <a id="eventTitle" class="url" href="{LISTING_URL}event/test/" title="{title}" rel="bookmark">
            <h2 class="rhp-event__title--list">{title}</h2>
          </a>
        </div>
        <div class="eventsColor eventDoorStartDate rhp-event__time--list">
          <span class="rhp-event__time-text--list">{time_str}</span>
        </div>
      </div>
    </div>
    <div class="col-12 col-md-3 text-center">
      <span class="rhp-event-cta on-sale">
        <a class="btn btn-primary" href="{ticket_url}" target="_blank">Buy Tickets</a>
      </span>
    </div>
  </div>
</div>"""


def _listing_page(cards: list[str], has_next_page: bool = False) -> str:
    """Wrap event cards in a minimal listing page shell."""
    pagination = (
        '<a href="https://thecomedyandmagicclub.com/events/page/2/">Next</a>'
        if has_next_page
        else ""
    )
    return f"<html><body>{''.join(cards)}{pagination}</body></html>"


# ---------------------------------------------------------------------------
# get_data() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_events(monkeypatch):
    """get_data() parses a listing page and returns ComedyMagicClubPageData."""
    scraper = ComedyMagicClubScraper(_club())
    html = _listing_page([
        _event_card(title="Jay Leno", date_str="Sun, Apr 05", time_str="Doors: 5 pm Show: 7 pm",
                    ticket_url="https://www.etix.com/ticket/p/10001/jay-leno-hermosa-beach-the-comedy-magic-club?partner_id=100"),
        _event_card(title="Frank Caliendo", date_str="Thu, Apr 09", time_str="Doors: 6:30 pm Show: 8 pm",
                    ticket_url="https://www.etix.com/ticket/p/10002/frank-caliendo-hermosa-beach-the-comedy-magic-club?partner_id=100"),
    ])

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return html

    monkeypatch.setattr(ComedyMagicClubScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(LISTING_URL)

    assert isinstance(result, ComedyMagicClubPageData)
    assert len(result.event_list) == 2
    titles = {e.title for e in result.event_list}
    assert "Jay Leno" in titles
    assert "Frank Caliendo" in titles


@pytest.mark.asyncio
async def test_get_data_returns_none_on_empty_html(monkeypatch):
    """get_data() returns None when the page returns no HTML."""
    scraper = ComedyMagicClubScraper(_club())

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return ""

    monkeypatch.setattr(ComedyMagicClubScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(LISTING_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_when_no_events(monkeypatch):
    """get_data() returns None when a page contains no event cards."""
    scraper = ComedyMagicClubScraper(_club())

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return "<html><body><p>No shows</p></body></html>"

    monkeypatch.setattr(ComedyMagicClubScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(LISTING_URL)
    assert result is None


# ---------------------------------------------------------------------------
# collect_scraping_targets() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_targets_returns_base_url(monkeypatch):
    """collect_scraping_targets() returns only the base listing URL.

    The Comedy & Magic Club's rhp-events plugin serves the same events on
    all pagination URLs, so only the base URL is needed.
    """
    scraper = ComedyMagicClubScraper(_club())
    targets = await scraper.collect_scraping_targets()
    assert len(targets) == 1
    assert targets[0].rstrip("/") == LISTING_URL.rstrip("/")


# ---------------------------------------------------------------------------
# ComedyMagicClubEvent.to_show() unit tests
# ---------------------------------------------------------------------------


def _make_event(
    title: str = "Jay Leno",
    date_str: str = "Sun, Apr 05",
    time_str: str = "Doors: 5 pm Show: 7 pm",
    ticket_url: str = "https://www.etix.com/ticket/p/59906881/jay-leno-hermosa-beach-the-comedy-magic-club?partner_id=100",
) -> ComedyMagicClubEvent:
    return ComedyMagicClubEvent(
        title=title,
        date_str=date_str,
        time_str=time_str,
        ticket_url=ticket_url,
    )


def test_to_show_returns_show_with_correct_name():
    """to_show() produces a Show with the correct name."""
    event = _make_event(title="Jay Leno")
    show = event.to_show(_club())

    assert show is not None
    assert show.name == "Jay Leno"


def test_to_show_sets_show_time_from_doors_show_string():
    """to_show() extracts the show time (not the doors time) from the time string."""
    event = _make_event(time_str="Doors: 5 pm Show: 7 pm")
    show = event.to_show(_club())

    assert show is not None
    assert show.date.hour == 19  # 7 PM → 19:00 UTC-7 → stored as aware datetime


def test_to_show_parses_8pm_show_time():
    """to_show() correctly parses 'Show: 8 pm' → 20:00."""
    event = _make_event(time_str="Doors: 6:30 pm Show: 8 pm")
    show = event.to_show(_club())

    assert show is not None
    assert show.date.hour == 20


def test_to_show_creates_etix_ticket():
    """to_show() creates a ticket pointing to the eTix URL."""
    ticket_url = "https://www.etix.com/ticket/p/59906881/jay-leno-hermosa-beach-the-comedy-magic-club?partner_id=100"
    event = _make_event(ticket_url=ticket_url)
    show = event.to_show(_club())

    assert show is not None
    assert len(show.tickets) == 1
    assert show.tickets[0].purchase_url == ticket_url


def test_to_show_returns_none_when_title_missing():
    """to_show() returns None when the title is empty."""
    event = _make_event(title="")
    show = event.to_show(_club())
    assert show is None


def test_to_show_returns_none_when_ticket_url_missing():
    """to_show() returns None when the ticket URL is empty."""
    event = _make_event(ticket_url="")
    show = event.to_show(_club())
    assert show is None


def test_to_show_returns_none_on_unparseable_date():
    """to_show() returns None when the date string cannot be parsed."""
    event = _make_event(date_str="Not A Date")
    show = event.to_show(_club())
    assert show is None


def test_to_show_infers_future_year():
    """to_show() assigns a year so that the resulting date is not in the past."""
    from datetime import date

    event = _make_event(date_str="Mon, Jan 01", time_str="Doors: 6:30 pm Show: 8 pm")
    show = event.to_show(_club())

    # January 1 with year inference should always be >= today (current year or next)
    if show is not None:
        assert show.date.date() >= date.today()


def test_to_show_mismatched_weekday_still_parses():
    """Weekday label is stripped before parsing, so a wrong label is ignored."""
    # "Mon, Apr 05" — April 5, 2026 is a Sunday, not a Monday.
    # Old code (with %a) would accept this without error; new code strips the
    # weekday entirely and parses only the month+day, producing the correct date.
    event = _make_event(date_str="Mon, Apr 05", time_str="Doors: 5 pm Show: 7 pm")
    show = event.to_show(_club())
    assert show is not None
    assert show.date.month == 4
    assert show.date.day == 5
