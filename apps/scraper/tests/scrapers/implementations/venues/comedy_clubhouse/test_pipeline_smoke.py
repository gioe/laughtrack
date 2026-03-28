"""
Pipeline smoke tests for ComedyClubhouseScraper and ComedyClubhouseEvent.

Exercises get_data() against mocked HTML that matches the actual
ticketsource.com/thecomedyclubhouse structure, and unit-tests the
ComedyClubhouseEvent.to_show() transformation path.
"""

import pytest

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.comedy_clubhouse import ComedyClubhouseEvent
from laughtrack.scrapers.implementations.venues.comedy_clubhouse.scraper import (
    ComedyClubhouseScraper,
)
from laughtrack.scrapers.implementations.venues.comedy_clubhouse.data import (
    ComedyClubhousePageData,
)

LISTING_URL = "https://www.ticketsource.com/thecomedyclubhouse"


def _club() -> Club:
    return Club(
        id=999,
        name="The Comedy Clubhouse",
        address="1462 N Ashland Ave",
        website="https://www.thecomedyclubhouse.com",
        scraping_url=LISTING_URL,
        popularity=0,
        zip_code="60622",
        phone_number="",
        visible=True,
        timezone="America/Chicago",
    )


def _event_row(
    title: str = "MAIN STAGE Improv Showcase",
    start_iso: str = "2026-04-03T19:30",
    show_path: str = "/thecomedyclubhouse/main-stage-improv-showcase/e-vragvj",
    ticket_path: str = "/booking/init/GDDJIEI",
) -> str:
    """Render a minimal TicketSource eventRow card matching the live HTML structure."""
    return f"""
<div class="grid-x align-middle padding-1 eventRow" itemscope itemtype="http://schema.org/Event" data-id="12345">
  <div class="cell medium-2 large-1 event-image margin-right-1">
    <div class="eventBanner">
      <a href="{show_path}"><img alt="{title} banner image" src="https://cdn.ticketsource.com/images/test.png"></a>
    </div>
  </div>
  <div class="cell medium-11 grid-x event-info">
    <div class="eventCol left small-12 medium-9">
      <div class="topInfo">
        <div class="eventTitle">
          <a href="{show_path}" itemprop="url">
            <span itemprop="name">{title}</span>
          </a>
        </div>
        <div class="venueAddress" itemprop="location" itemscope itemtype="http://schema.org/EventVenue">
          <a href="/whats-on/il/the-comedy-clubhouse"><span itemprop="name">The Comedy Clubhouse</span></a>
        </div>
      </div>
      <div class="dateTime" itemprop="startDate" content="{start_iso}">
        <time>Fri, Apr 3 2026, <br>7:30PM - 9:15PM</time>
      </div>
    </div>
    <div class="eventCol small-12 medium-3 bottomInfo align-middle grid-x">
      <div class="cta small-order-2 medium-order-1 cell">
        <div class="event-btn">
          <a href="{ticket_path}" class="button ">
            <div class="button-text">Book Now</div>
          </a>
        </div>
      </div>
    </div>
  </div>
</div>"""


def _listing_page(rows: list[str]) -> str:
    """Wrap event rows in a minimal TicketSource listing page shell."""
    return f"""<html><body>
<div id="results-section" class="large-12 cell">
{''.join(rows)}
</div>
</body></html>"""


# ---------------------------------------------------------------------------
# get_data() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_events(monkeypatch):
    """get_data() parses a listing page and returns ComedyClubhousePageData."""
    scraper = ComedyClubhouseScraper(_club())
    html = _listing_page([
        _event_row(
            title="MAIN STAGE Improv Showcase",
            start_iso="2026-04-03T19:30",
            show_path="/thecomedyclubhouse/main-stage-improv-showcase/e-vragvj",
            ticket_path="/booking/init/GDDJIEI",
        ),
        _event_row(
            title="MAIN STAGE Stand-up Showcase",
            start_iso="2026-04-03T21:30",
            show_path="/thecomedyclubhouse/main-stage-stand-up-showcase/e-gryzjl",
            ticket_path="/booking/init/GDHHFED",
        ),
    ])

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return html

    monkeypatch.setattr(ComedyClubhouseScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(LISTING_URL)

    assert isinstance(result, ComedyClubhousePageData)
    assert len(result.event_list) == 2
    titles = {e.title for e in result.event_list}
    assert "MAIN STAGE Improv Showcase" in titles
    assert "MAIN STAGE Stand-up Showcase" in titles


@pytest.mark.asyncio
async def test_get_data_returns_none_on_empty_html(monkeypatch):
    """get_data() returns None when the page returns no HTML."""
    scraper = ComedyClubhouseScraper(_club())

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return ""

    monkeypatch.setattr(ComedyClubhouseScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(LISTING_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_when_no_events(monkeypatch):
    """get_data() returns None when the page contains no eventRow cards."""
    scraper = ComedyClubhouseScraper(_club())

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return "<html><body><p>No upcoming shows</p></body></html>"

    monkeypatch.setattr(ComedyClubhouseScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(LISTING_URL)
    assert result is None


# ---------------------------------------------------------------------------
# collect_scraping_targets() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_targets_returns_single_listing_url():
    """collect_scraping_targets() returns only the TicketSource listing URL."""
    scraper = ComedyClubhouseScraper(_club())
    targets = await scraper.collect_scraping_targets()
    assert len(targets) == 1
    assert "ticketsource.com/thecomedyclubhouse" in targets[0]


# ---------------------------------------------------------------------------
# ComedyClubhouseEvent.to_show() unit tests
# ---------------------------------------------------------------------------


def _make_event(
    title: str = "MAIN STAGE Improv Showcase",
    start_iso: str = "2026-04-03T19:30",
    show_url: str = "https://www.ticketsource.com/thecomedyclubhouse/main-stage-improv-showcase/e-vragvj",
    ticket_url: str = "https://www.ticketsource.com/booking/init/GDDJIEI",
) -> ComedyClubhouseEvent:
    return ComedyClubhouseEvent(
        title=title,
        start_iso=start_iso,
        show_url=show_url,
        ticket_url=ticket_url,
    )


def test_to_show_returns_show_with_correct_name():
    """to_show() produces a Show with the correct title."""
    event = _make_event(title="MAIN STAGE Improv Showcase")
    show = event.to_show(_club())

    assert show is not None
    assert show.name == "MAIN STAGE Improv Showcase"


def test_to_show_parses_start_datetime():
    """to_show() correctly parses the ISO start datetime into 7:30 PM Chicago time."""
    event = _make_event(start_iso="2026-04-03T19:30")
    show = event.to_show(_club())

    assert show is not None
    assert show.date.hour == 19
    assert show.date.minute == 30


def test_to_show_creates_ticketsource_ticket():
    """to_show() creates a ticket pointing to the TicketSource booking URL."""
    ticket_url = "https://www.ticketsource.com/booking/init/GDDJIEI"
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


def test_to_show_returns_none_on_invalid_iso():
    """to_show() returns None when start_iso cannot be parsed."""
    event = _make_event(start_iso="not-a-date")
    show = event.to_show(_club())
    assert show is None


def test_extractor_parses_ticket_and_show_urls():
    """Extractor correctly builds absolute ticket and show page URLs."""
    from laughtrack.scrapers.implementations.venues.comedy_clubhouse.extractor import (
        ComedyClubhouseExtractor,
    )

    html = _listing_page([
        _event_row(
            show_path="/thecomedyclubhouse/main-stage-improv-showcase/e-vragvj",
            ticket_path="/booking/init/GDDJIEI",
        )
    ])
    events = ComedyClubhouseExtractor.extract_events(html)

    assert len(events) == 1
    assert events[0].show_url == "https://www.ticketsource.com/thecomedyclubhouse/main-stage-improv-showcase/e-vragvj"
    assert events[0].ticket_url == "https://www.ticketsource.com/booking/init/GDDJIEI"


def test_extractor_skips_row_without_title():
    """Extractor skips event cards that have no title span."""
    from laughtrack.scrapers.implementations.venues.comedy_clubhouse.extractor import (
        ComedyClubhouseExtractor,
    )

    bad_row = """
<div class="grid-x align-middle padding-1 eventRow">
  <div class="dateTime" content="2026-04-03T19:30"><time>Fri, Apr 3 2026</time></div>
  <div class="event-btn"><a href="/booking/init/XXXXX">Book Now</a></div>
</div>"""
    events = ComedyClubhouseExtractor.extract_events(f"<html><body>{bad_row}</body></html>")
    assert len(events) == 0


def test_extractor_skips_row_without_datetime():
    """Extractor skips event cards that have no dateTime content."""
    from laughtrack.scrapers.implementations.venues.comedy_clubhouse.extractor import (
        ComedyClubhouseExtractor,
    )

    bad_row = """
<div class="grid-x align-middle padding-1 eventRow">
  <div class="eventTitle"><a href="/x" itemprop="url"><span itemprop="name">Test Show</span></a></div>
  <div class="dateTime"><time>Fri, Apr 3 2026</time></div>
  <div class="event-btn"><a href="/booking/init/XXXXX">Book Now</a></div>
</div>"""
    events = ComedyClubhouseExtractor.extract_events(f"<html><body>{bad_row}</body></html>")
    assert len(events) == 0


def test_extractor_skips_row_with_empty_ticket_href():
    """Extractor skips event cards where the ticket anchor has an empty href."""
    from laughtrack.scrapers.implementations.venues.comedy_clubhouse.extractor import (
        ComedyClubhouseExtractor,
    )

    bad_row = """
<div class="grid-x align-middle padding-1 eventRow">
  <div class="eventTitle"><a href="/x" itemprop="url"><span itemprop="name">Test Show</span></a></div>
  <div class="dateTime" content="2026-04-03T19:30"><time>Fri, Apr 3 2026</time></div>
  <div class="event-btn"><a href="">Book Now</a></div>
</div>"""
    events = ComedyClubhouseExtractor.extract_events(f"<html><body>{bad_row}</body></html>")
    assert len(events) == 0


@pytest.mark.asyncio
async def test_get_data_returns_none_on_extractor_exception(monkeypatch):
    """get_data() returns None and does not propagate when extract_events() raises."""
    from laughtrack.scrapers.implementations.venues.comedy_clubhouse.extractor import (
        ComedyClubhouseExtractor,
    )

    scraper = ComedyClubhouseScraper(_club())

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return "<html><body>some content</body></html>"

    def raising_extract(html: str):
        raise RuntimeError("parse failure")

    monkeypatch.setattr(ComedyClubhouseScraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(ComedyClubhouseExtractor, "extract_events", staticmethod(raising_extract))

    result = await scraper.get_data(LISTING_URL)
    assert result is None


def test_to_show_returns_none_when_start_iso_empty():
    """to_show() returns None when start_iso is an empty string."""
    event = _make_event(start_iso="")
    show = event.to_show(_club())
    assert show is None
