"""
Pipeline smoke tests for EmpireComedyClubScraper.

Exercises the extractor against sample HTML fixtures, the transformer
against EmpireEvent objects, and get_data() against mocked HTML responses.
"""

import pytest
from datetime import datetime

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.empire import EmpireEvent
from laughtrack.scrapers.implementations.venues.empire_comedy_club.scraper import EmpireComedyClubScraper
from laughtrack.scrapers.implementations.venues.empire_comedy_club.data import EmpirePageData
from laughtrack.scrapers.implementations.venues.empire_comedy_club.extractor import EmpireEventExtractor
from laughtrack.scrapers.implementations.venues.empire_comedy_club.transformer import EmpireEventTransformer


SCRAPING_URL = "https://empirecomedyme.com/shows/"


def _club() -> Club:
    return Club(
        id=819,
        name="Empire Comedy Club",
        address="575 Congress St",
        website="https://empirecomedyme.com",
        scraping_url=SCRAPING_URL,
        popularity=0,
        zip_code="04101",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )


# ---------------------------------------------------------------------------
# HTML fixtures
# ---------------------------------------------------------------------------

SINGLE_SHOW_HTML = """
<html><body>
<section class="month-section" data-month-section="January 2099">
  <article class="show-card">
    <h3><a href="/show/comedy-night">Comedy Night</a></h3>
    <p class="status on-sale">On Sale</p>
    <p class="meta">Fri</p>
    <p class="meta">Jan 10</p>
    <p class="time"><time>7:00 PM</time></p>
  </article>
</section>
</body></html>
"""

MULTI_SHOW_HTML = """
<html><body>
<section class="month-section" data-month-section="February 2099">
  <article class="show-card">
    <h3><a href="/show/open-mic">Open Mic</a></h3>
    <p class="status on-sale">On Sale</p>
    <p class="meta">Mon</p>
    <p class="meta">Feb 3</p>
    <p class="time"><time>8:00 PM</time></p>
  </article>
  <article class="show-card">
    <h3><a href="/show/headliner">Big Headliner</a></h3>
    <p class="status sold-out">Sold Out</p>
    <p class="meta">Sat</p>
    <p class="meta">Feb 8</p>
    <p class="time"><time>9:00 PM</time></p>
  </article>
</section>
<section class="month-section" data-month-section="March 2099">
  <article class="show-card">
    <h3><a href="/show/late-show">Late Show</a></h3>
    <p class="status on-sale">On Sale</p>
    <p class="meta">Fri</p>
    <p class="meta">Mar 14</p>
    <p class="time"><time>10:30 PM</time></p>
  </article>
</section>
</body></html>
"""

EMPTY_PAGE_HTML = """
<html><body>
<div class="no-shows">No upcoming shows</div>
</body></html>
"""

MISSING_TIME_HTML = """
<html><body>
<section class="month-section" data-month-section="April 2099">
  <article class="show-card">
    <h3><a href="/show/no-time">No Time Show</a></h3>
    <p class="status on-sale">On Sale</p>
    <p class="meta">Wed</p>
    <p class="meta">Apr 9</p>
    <p class="time"><time></time></p>
  </article>
</section>
</body></html>
"""

MISSING_META_HTML = """
<html><body>
<section class="month-section" data-month-section="May 2099">
  <article class="show-card">
    <h3><a href="/show/bad-card">Bad Card</a></h3>
    <p class="status on-sale">On Sale</p>
    <p class="meta">Thu</p>
  </article>
</section>
</body></html>
"""


# ---------------------------------------------------------------------------
# Extractor tests
# ---------------------------------------------------------------------------


def test_extract_single_show():
    """Extractor parses a single show card with name, date, time, and URL."""
    events = EmpireEventExtractor.extract_events(SINGLE_SHOW_HTML)

    assert len(events) == 1
    event = events[0]
    assert event.name == "Comedy Night"
    assert event.date_time == datetime(2099, 1, 10, 19, 0)
    assert event.show_page_url == "https://empirecomedyme.com/show/comedy-night"
    assert event.status == "On Sale"


def test_extract_multiple_shows_across_sections():
    """Extractor handles multiple shows across multiple month sections."""
    events = EmpireEventExtractor.extract_events(MULTI_SHOW_HTML)

    assert len(events) == 3
    names = [e.name for e in events]
    assert names == ["Open Mic", "Big Headliner", "Late Show"]


def test_extract_date_time_values():
    """Extractor correctly parses dates and times from show cards."""
    events = EmpireEventExtractor.extract_events(MULTI_SHOW_HTML)

    # Open Mic: Feb 3 2099, 8:00 PM
    assert events[0].date_time == datetime(2099, 2, 3, 20, 0)
    # Big Headliner: Feb 8 2099, 9:00 PM
    assert events[1].date_time == datetime(2099, 2, 8, 21, 0)
    # Late Show: Mar 14 2099, 10:30 PM
    assert events[2].date_time == datetime(2099, 3, 14, 22, 30)


def test_extract_sold_out_status():
    """Extractor preserves the status field from show cards."""
    events = EmpireEventExtractor.extract_events(MULTI_SHOW_HTML)

    assert events[0].status == "On Sale"
    assert events[1].status == "Sold Out"


def test_extract_show_page_url():
    """Extractor builds full URLs from relative hrefs."""
    events = EmpireEventExtractor.extract_events(MULTI_SHOW_HTML)

    assert events[0].show_page_url == "https://empirecomedyme.com/show/open-mic"
    assert events[2].show_page_url == "https://empirecomedyme.com/show/late-show"


def test_extract_empty_page_returns_empty_list():
    """Extractor returns an empty list when no month sections exist."""
    events = EmpireEventExtractor.extract_events(EMPTY_PAGE_HTML)
    assert events == []


def test_extract_skips_card_with_missing_time():
    """Extractor skips cards where the time element is empty."""
    events = EmpireEventExtractor.extract_events(MISSING_TIME_HTML)
    assert events == []


def test_extract_skips_card_with_insufficient_meta():
    """Extractor skips cards with fewer than two <p class='meta'> elements."""
    events = EmpireEventExtractor.extract_events(MISSING_META_HTML)
    assert events == []


def test_extract_year_from_section_attribute():
    """_extract_year_from_section parses the year from data-month-section."""
    from bs4 import BeautifulSoup

    html = '<section class="month-section" data-month-section="December 2099"></section>'
    soup = BeautifulSoup(html, "html.parser")
    section = soup.select_one("section")
    assert EmpireEventExtractor._extract_year_from_section(section) == 2099


def test_extract_year_returns_none_for_missing_attribute():
    """_extract_year_from_section returns None when attribute is absent."""
    from bs4 import BeautifulSoup

    html = '<section class="month-section"></section>'
    soup = BeautifulSoup(html, "html.parser")
    section = soup.select_one("section")
    assert EmpireEventExtractor._extract_year_from_section(section) is None


# ---------------------------------------------------------------------------
# Transformer tests
# ---------------------------------------------------------------------------


def _make_event(
    name="Comedy Night",
    date_time=None,
    show_page_url="https://empirecomedyme.com/show/comedy-night",
    status="On Sale",
) -> EmpireEvent:
    return EmpireEvent(
        name=name,
        date_time=date_time or datetime(2099, 1, 10, 19, 0),
        show_page_url=show_page_url,
        status=status,
    )


def test_transformer_produces_show_with_correct_fields():
    """Transformer converts an EmpireEvent to a Show with correct name and date."""
    transformer = EmpireEventTransformer(_club())
    event = _make_event(name="Open Mic", date_time=datetime(2099, 3, 5, 20, 0))
    show = transformer.transform_to_show(event, source_url=SCRAPING_URL)

    assert show is not None
    assert show.name == "Open Mic"
    assert show.date.year == 2099
    assert show.date.month == 3
    assert show.date.day == 5


def test_transformer_sets_timezone_from_club():
    """Transformer applies the club's timezone to the Show."""
    transformer = EmpireEventTransformer(_club())
    show = transformer.transform_to_show(_make_event(), source_url=SCRAPING_URL)

    assert show is not None
    assert show.timezone == "America/New_York"


def test_transformer_creates_ticket_with_purchase_url():
    """Transformer creates a ticket with the show_page_url as purchase link."""
    transformer = EmpireEventTransformer(_club())
    event = _make_event(show_page_url="https://empirecomedyme.com/show/special")
    show = transformer.transform_to_show(event, source_url=SCRAPING_URL)

    assert show is not None
    assert len(show.tickets) == 1
    assert show.tickets[0].purchase_url == "https://empirecomedyme.com/show/special"
    assert show.tickets[0].type == "General Admission"
    assert show.tickets[0].price == 0.0


def test_transformer_sets_sold_out_from_status():
    """Transformer sets sold_out=True when status is 'Sold Out'."""
    transformer = EmpireEventTransformer(_club())
    event = _make_event(status="Sold Out")
    show = transformer.transform_to_show(event, source_url=SCRAPING_URL)

    assert show is not None
    assert show.tickets[0].sold_out is True


def test_transformer_not_sold_out_for_on_sale():
    """Transformer sets sold_out=False when status is 'On Sale'."""
    transformer = EmpireEventTransformer(_club())
    event = _make_event(status="On Sale")
    show = transformer.transform_to_show(event, source_url=SCRAPING_URL)

    assert show is not None
    assert show.tickets[0].sold_out is False


def test_transformer_can_transform_valid_event():
    """can_transform returns True for a valid EmpireEvent."""
    transformer = EmpireEventTransformer(_club())
    assert transformer.can_transform(_make_event()) is True


def test_transformer_rejects_missing_name():
    """can_transform returns False when name is empty."""
    transformer = EmpireEventTransformer(_club())
    event = _make_event(name="")
    assert transformer.can_transform(event) is False


def test_transformer_rejects_missing_date():
    """can_transform returns False when date_time is None."""
    transformer = EmpireEventTransformer(_club())
    event = EmpireEvent(name="Show", date_time=None, show_page_url="https://example.com")
    assert transformer.can_transform(event) is False


# ---------------------------------------------------------------------------
# get_data() integration tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_events(monkeypatch):
    """get_data() fetches HTML and returns EmpirePageData with extracted events."""
    scraper = EmpireComedyClubScraper(_club())

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return SINGLE_SHOW_HTML

    monkeypatch.setattr(EmpireComedyClubScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(SCRAPING_URL)

    assert isinstance(result, EmpirePageData)
    assert len(result.event_list) == 1
    assert result.event_list[0].name == "Comedy Night"


@pytest.mark.asyncio
async def test_get_data_returns_multiple_events(monkeypatch):
    """get_data() extracts all events across multiple month sections."""
    scraper = EmpireComedyClubScraper(_club())

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return MULTI_SHOW_HTML

    monkeypatch.setattr(EmpireComedyClubScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(SCRAPING_URL)

    assert isinstance(result, EmpirePageData)
    assert len(result.event_list) == 3


@pytest.mark.asyncio
async def test_get_data_returns_none_on_empty_html(monkeypatch):
    """get_data() returns EmpirePageData with empty list when no shows found."""
    scraper = EmpireComedyClubScraper(_club())

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return EMPTY_PAGE_HTML

    monkeypatch.setattr(EmpireComedyClubScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(SCRAPING_URL)

    assert isinstance(result, EmpirePageData)
    assert result.event_list == []


@pytest.mark.asyncio
async def test_get_data_returns_none_on_fetch_failure(monkeypatch):
    """get_data() returns None when fetch_html returns None."""
    scraper = EmpireComedyClubScraper(_club())

    async def fake_fetch_html(self, url: str, **kwargs):
        return None

    monkeypatch.setattr(EmpireComedyClubScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(SCRAPING_URL)
    assert result is None


# ---------------------------------------------------------------------------
# Module import smoke test
# ---------------------------------------------------------------------------


def test_empire_comedy_club_package_imports():
    """Verify that the empire_comedy_club package exports are importable."""
    from laughtrack.scrapers.implementations.venues.empire_comedy_club import (
        EmpireEventExtractor,
        EmpireEventTransformer,
        EmpirePageData,
    )

    assert EmpireEventExtractor is not None
    assert EmpireEventTransformer is not None
    assert EmpirePageData is not None


def test_empire_event_entity_import():
    """Verify the EmpireEvent entity is importable."""
    from laughtrack.core.entities.event.empire import EmpireEvent

    assert EmpireEvent is not None


def test_scraper_class_has_correct_key():
    """EmpireComedyClubScraper.key matches the expected registry key."""
    assert EmpireComedyClubScraper.key == "empire_comedy_club"
