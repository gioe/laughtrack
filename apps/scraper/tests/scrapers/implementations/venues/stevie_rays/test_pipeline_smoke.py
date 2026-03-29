"""
Pipeline smoke tests for StevieRaysScraper and StevieRaysEvent.

Exercises get_data() against mocked HTML that matches the actual
tickets.chanhassendt.com structure, and unit-tests the
StevieRaysEvent.to_show() transformation path.
"""

import pytest

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.stevie_rays import StevieRaysEvent
from laughtrack.core.entities.show.model import Show
from laughtrack.scrapers.implementations.venues.stevie_rays.scraper import (
    StevieRaysScraper,
)
from laughtrack.scrapers.implementations.venues.stevie_rays.data import (
    StevieRaysPageData,
)

LISTING_URL = "https://tickets.chanhassendt.com/Online/default.asp?BOparam::WScontent::loadArticle::permalink=stevierays"


def _club() -> Club:
    return Club(
        id=999,
        name="Stevie Ray's Improv Company",
        address="501 West 78th Street",
        website="https://stevierays.org",
        scraping_url=LISTING_URL,
        popularity=0,
        zip_code="55317",
        phone_number="",
        visible=True,
        timezone="America/Chicago",
    )


def _row_html(
    title: str = "Stevie Ray's Comedy Cabaret",
    start_date_str: str = "Friday, April 03, 2026 @ 7:30 PM",
    availability: str = "Excellent",
) -> str:
    """Render a minimal result-box-item matching the live ticketing page structure."""
    return f"""
<div class="odd result-box-item">
  <div class="item-description result-box-item-details">
    <div class="item-name">{title}</div>
    <div class="item-start-date">
      <span class="start-date-label">Show Time -</span>
      <span class="start-date">{start_date_str}</span>
    </div>
  </div>
  <div class="availability-indicator">
    <div class="availability-label">Availability</div>
    <div class="availability-text">{availability}</div>
  </div>
  <div class="item-link result-box-item-details last-column {availability.lower()}">
    <a class="btn btn-primary" tabindex="0" id="popupDivOpen"
       aria-label="Buy, {title}, {start_date_str}">
      <span>Buy</span>
    </a>
  </div>
</div>"""


def _listing_page(rows: list) -> str:
    """Wrap event rows in a minimal ticketing page shell."""
    return f"""<html><body>
<div class="results-box standard-search-results">
{''.join(rows)}
</div>
</body></html>"""


# ---------------------------------------------------------------------------
# get_data() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_events(monkeypatch):
    """get_data() parses a listing page and returns StevieRaysPageData."""
    scraper = StevieRaysScraper(_club())
    html = _listing_page([
        _row_html(
            title="Stevie Ray's Comedy Cabaret",
            start_date_str="Friday, April 03, 2026 @ 7:30 PM",
        ),
        _row_html(
            title="Stevie Ray's Comedy Cabaret",
            start_date_str="Saturday, April 04, 2026 @ 7:30 PM",
        ),
    ])

    async def fake_fetch_html_with_js(self, url: str) -> str:
        return html

    monkeypatch.setattr(StevieRaysScraper, "_fetch_html_with_js", fake_fetch_html_with_js)

    result = await scraper.get_data(LISTING_URL)

    assert isinstance(result, StevieRaysPageData)
    assert len(result.event_list) == 2
    date_strs = {e.start_date_str for e in result.event_list}
    assert "Friday, April 03, 2026 @ 7:30 PM" in date_strs
    assert "Saturday, April 04, 2026 @ 7:30 PM" in date_strs


@pytest.mark.asyncio
async def test_get_data_returns_none_on_empty_html(monkeypatch):
    """get_data() returns None when the page returns no HTML."""
    scraper = StevieRaysScraper(_club())

    async def fake_fetch_html_with_js(self, url: str) -> str:
        return ""

    monkeypatch.setattr(StevieRaysScraper, "_fetch_html_with_js", fake_fetch_html_with_js)

    result = await scraper.get_data(LISTING_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_when_no_events(monkeypatch):
    """get_data() returns None when the page contains no result-box-item elements."""
    scraper = StevieRaysScraper(_club())

    async def fake_fetch_html_with_js(self, url: str) -> str:
        return "<html><body><p>No upcoming shows</p></body></html>"

    monkeypatch.setattr(StevieRaysScraper, "_fetch_html_with_js", fake_fetch_html_with_js)

    result = await scraper.get_data(LISTING_URL)
    assert result is None


# ---------------------------------------------------------------------------
# collect_scraping_targets() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_targets_returns_single_listing_url():
    """collect_scraping_targets() returns only the ticketing listing URL."""
    scraper = StevieRaysScraper(_club())
    targets = await scraper.collect_scraping_targets()
    assert len(targets) == 1
    assert "chanhassendt.com" in targets[0]
    assert "stevierays" in targets[0]


# ---------------------------------------------------------------------------
# StevieRaysEvent.to_show() unit tests
# ---------------------------------------------------------------------------


def _make_event(
    title: str = "Stevie Ray's Comedy Cabaret",
    start_date_str: str = "Friday, April 03, 2026 @ 7:30 PM",
    ticket_url: str = LISTING_URL,
) -> StevieRaysEvent:
    return StevieRaysEvent(
        title=title,
        start_date_str=start_date_str,
        ticket_url=ticket_url,
    )


def test_to_show_returns_show_with_correct_name():
    """to_show() produces a Show with the correct title."""
    event = _make_event(title="Stevie Ray's Comedy Cabaret")
    show = event.to_show(_club())

    assert show is not None
    assert show.name == "Stevie Ray's Comedy Cabaret"


def test_to_show_parses_start_datetime():
    """to_show() correctly parses date + time into 7:30 PM Central time."""
    event = _make_event(start_date_str="Friday, April 03, 2026 @ 7:30 PM")
    show = event.to_show(_club())

    assert show is not None
    assert show.date.hour == 19
    assert show.date.minute == 30


def test_to_show_creates_ticket_with_listing_url():
    """to_show() creates a ticket pointing to the listing page URL."""
    event = _make_event(ticket_url=LISTING_URL)
    show = event.to_show(_club())

    assert show is not None
    assert len(show.tickets) == 1
    assert "chanhassendt.com" in show.tickets[0].purchase_url


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


def test_to_show_returns_none_on_invalid_date():
    """to_show() returns None when the date string cannot be parsed."""
    event = _make_event(start_date_str="not-a-date")
    show = event.to_show(_club())
    assert show is None


def test_to_show_parses_saturday_show():
    """to_show() correctly parses a Saturday 7:30 PM show."""
    event = _make_event(start_date_str="Saturday, April 04, 2026 @ 7:30 PM")
    show = event.to_show(_club())

    assert show is not None
    assert show.date.hour == 19
    assert show.date.minute == 30


def test_extractor_parses_title_and_date():
    """Extractor correctly extracts title and start_date_str from a row."""
    from laughtrack.scrapers.implementations.venues.stevie_rays.extractor import (
        StevieRaysExtractor,
    )

    html = _listing_page([
        _row_html(
            title="Stevie Ray's Comedy Cabaret",
            start_date_str="Friday, April 03, 2026 @ 7:30 PM",
        )
    ])
    events = StevieRaysExtractor.extract_events(html)

    assert len(events) == 1
    assert events[0].title == "Stevie Ray's Comedy Cabaret"
    assert events[0].start_date_str == "Friday, April 03, 2026 @ 7:30 PM"
    assert "chanhassendt.com" in events[0].ticket_url


def test_extractor_skips_row_without_start_date():
    """Extractor skips rows that have no start-date span."""
    from laughtrack.scrapers.implementations.venues.stevie_rays.extractor import (
        StevieRaysExtractor,
    )

    bad_row = """
<div class="odd result-box-item">
  <div class="item-description result-box-item-details">
    <div class="item-name">Stevie Ray's Comedy Cabaret</div>
  </div>
</div>"""
    events = StevieRaysExtractor.extract_events(f"<html><body>{bad_row}</body></html>")
    assert len(events) == 0


def test_extractor_handles_multiple_shows():
    """Extractor returns all rows from a page with multiple shows."""
    from laughtrack.scrapers.implementations.venues.stevie_rays.extractor import (
        StevieRaysExtractor,
    )

    html = _listing_page([
        _row_html(start_date_str="Friday, April 03, 2026 @ 7:30 PM"),
        _row_html(start_date_str="Saturday, April 04, 2026 @ 7:30 PM"),
        _row_html(start_date_str="Friday, April 10, 2026 @ 7:30 PM"),
    ])
    events = StevieRaysExtractor.extract_events(html)
    assert len(events) == 3


def test_transformation_pipeline_produces_shows():
    """
    Core regression: transformation_pipeline.transform() must return at least one Show
    when given StevieRaysPageData with real StevieRaysEvent objects.

    If can_transform() returns False for StevieRaysEvent (e.g., due to a type mismatch
    between the transformer's generic parameter and the event type), transform()
    silently returns an empty list with no error.
    """
    club = _club()
    scraper = StevieRaysScraper(club)

    events = [
        _make_event(start_date_str="Friday, April 03, 2026 @ 7:30 PM"),
        _make_event(start_date_str="Saturday, April 04, 2026 @ 7:30 PM"),
    ]
    page_data = StevieRaysPageData(event_list=events)

    shows = scraper.transformation_pipeline.transform(page_data)

    assert len(shows) > 0, (
        "transformation_pipeline.transform() returned 0 Shows from StevieRaysPageData — "
        "check StevieRaysEventTransformer.can_transform() and that the transformer is "
        "registered with the correct generic type"
    )
    assert all(isinstance(s, Show) for s in shows)
