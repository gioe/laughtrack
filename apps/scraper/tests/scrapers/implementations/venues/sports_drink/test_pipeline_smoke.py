"""
Pipeline smoke tests for SportsDrinkScraper and SportsDrinkEvent.

Exercises get_data() against mocked HTML that matches the actual
app.opendate.io/v/sports-drink-1939 structure, and unit-tests the
SportsDrinkEvent.to_show() transformation path.
"""

import pytest

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.sports_drink import SportsDrinkEvent
from laughtrack.core.entities.show.model import Show
from laughtrack.scrapers.implementations.venues.sports_drink.scraper import (
    SportsDrinkScraper,
)
from laughtrack.scrapers.implementations.venues.sports_drink.data import (
    SportsDrinkPageData,
)

LISTING_URL = "https://app.opendate.io/v/sports-drink-1939?per_page=500"


def _club() -> Club:
    return Club(
        id=999,
        name="Sports Drink",
        address="1042 Toledano St",
        website="https://www.sportsdrink.org",
        scraping_url=LISTING_URL,
        popularity=0,
        zip_code="70115",
        phone_number="",
        visible=True,
        timezone="America/Chicago",
    )


def _card_html(
    title: str = "Ian Lara at SPORTS DRINK (Friday, 7:00p)",
    event_url: str = "https://app.opendate.io/e/ian-lara-at-sports-drink-friday-7-00p-april-03-2026-565468",
    date_str: str = "April 03, 2026",
    time_str: str = "Doors: 6:30 PM - Show: 7:00 PM",
) -> str:
    """Render a minimal OpenDate confirm-card matching the live HTML structure."""
    return f"""
<div class="col-12 col-sm-6 col-md-4 col-xl-3" style="margin-bottom: 58px;">
<div class="card confirm-card" style="border-radius: 16px; border: 2px solid white;">
<div class="card-body" style="padding: 15px;">
<div style="margin-bottom: 20px;">
<img class="consumer-order-img img-fluid" src="https://example.com/img.jpg" style="border-radius: 16px;"/>
</div>
<p class="mb-0 text-dark" style="font-size: 20px; line-height: 20px;">
<a class="text-dark stretched-link text-decoration-none" href="{event_url}" target="_parent"><strong>
{title}
</strong>
</a></p>
<p class="mb-0" style="font-size: 13.6px; color: #1982c4; font-weight: 600; margin-top: 3px;">
{date_str}
</p>
<p class="mb-0" style="font-size: 13.6px; color: #1982c4; font-weight: 600; margin-top: 3px;">
{time_str}
</p>
<p class="mb-0 text-truncate" style="font-size: 13.6px; color: rgba(51, 51, 51, .85); margin-top: 3px;" title="SPORTS DRINK">
SPORTS DRINK: Café &amp; Comedy Club • New Orleans, LA
</p>
</div>
</div>
</div>"""


def _listing_page(cards: list[str]) -> str:
    """Wrap event cards in a minimal OpenDate listing page shell."""
    return f"""<html><body>
<div class="row">
{''.join(cards)}
</div>
</body></html>"""


# ---------------------------------------------------------------------------
# get_data() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_events(monkeypatch):
    """get_data() parses a listing page and returns SportsDrinkPageData."""
    scraper = SportsDrinkScraper(_club())
    html = _listing_page([
        _card_html(
            title="Ian Lara at SPORTS DRINK (Friday, 7:00p)",
            date_str="April 03, 2026",
            time_str="Doors: 6:30 PM - Show: 7:00 PM",
        ),
        _card_html(
            title="Jake Cornell at SPORTS DRINK (Saturday, 9:00p)",
            event_url="https://app.opendate.io/e/jake-cornell-at-sports-drink-saturday-9-00p-april-11-2026-652378",
            date_str="April 11, 2026",
            time_str="Doors: 8:45 PM - Show: 9:00 PM",
        ),
    ])

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return html

    monkeypatch.setattr(SportsDrinkScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(LISTING_URL)

    assert isinstance(result, SportsDrinkPageData)
    assert len(result.event_list) == 2
    titles = {e.title for e in result.event_list}
    assert "Ian Lara at SPORTS DRINK (Friday, 7:00p)" in titles
    assert "Jake Cornell at SPORTS DRINK (Saturday, 9:00p)" in titles


@pytest.mark.asyncio
async def test_get_data_returns_none_on_empty_html(monkeypatch):
    """get_data() returns None when the page returns no HTML."""
    scraper = SportsDrinkScraper(_club())

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return ""

    monkeypatch.setattr(SportsDrinkScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(LISTING_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_when_no_events(monkeypatch):
    """get_data() returns None when the page contains no confirm-card elements."""
    scraper = SportsDrinkScraper(_club())

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return "<html><body><p>No upcoming shows</p></body></html>"

    monkeypatch.setattr(SportsDrinkScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(LISTING_URL)
    assert result is None


# ---------------------------------------------------------------------------
# collect_scraping_targets() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_targets_returns_single_listing_url():
    """collect_scraping_targets() returns only the OpenDate listing URL."""
    scraper = SportsDrinkScraper(_club())
    targets = await scraper.collect_scraping_targets()
    assert len(targets) == 1
    assert "opendate.io/v/sports-drink-1939" in targets[0]


# ---------------------------------------------------------------------------
# SportsDrinkEvent.to_show() unit tests
# ---------------------------------------------------------------------------


def _make_event(
    title: str = "Ian Lara at SPORTS DRINK (Friday, 7:00p)",
    date_str: str = "April 03, 2026",
    time_str: str = "Doors: 6:30 PM - Show: 7:00 PM",
    event_url: str = "https://app.opendate.io/e/ian-lara-at-sports-drink-friday-7-00p-april-03-2026-565468",
) -> SportsDrinkEvent:
    return SportsDrinkEvent(
        title=title,
        date_str=date_str,
        time_str=time_str,
        event_url=event_url,
    )


def test_to_show_returns_show_with_correct_name():
    """to_show() produces a Show with the correct title."""
    event = _make_event(title="Ian Lara at SPORTS DRINK (Friday, 7:00p)")
    show = event.to_show(_club())

    assert show is not None
    assert show.name == "Ian Lara at SPORTS DRINK (Friday, 7:00p)"


def test_to_show_parses_start_datetime():
    """to_show() correctly parses date + show time into 7:00 PM NOLA time."""
    event = _make_event(date_str="April 03, 2026", time_str="Doors: 6:30 PM - Show: 7:00 PM")
    show = event.to_show(_club())

    assert show is not None
    assert show.date.hour == 19
    assert show.date.minute == 0


def test_to_show_creates_opendate_ticket():
    """to_show() creates a ticket pointing to the OpenDate event URL."""
    event_url = "https://app.opendate.io/e/ian-lara-at-sports-drink-friday-7-00p-april-03-2026-565468"
    event = _make_event(event_url=event_url)
    show = event.to_show(_club())

    assert show is not None
    assert len(show.tickets) == 1
    assert show.tickets[0].purchase_url == event_url


def test_to_show_returns_none_when_title_missing():
    """to_show() returns None when the title is empty."""
    event = _make_event(title="")
    show = event.to_show(_club())
    assert show is None


def test_to_show_returns_none_when_event_url_missing():
    """to_show() returns None when the event URL is empty."""
    event = _make_event(event_url="")
    show = event.to_show(_club())
    assert show is None


def test_to_show_returns_none_on_invalid_time():
    """to_show() returns None when the time string cannot be parsed."""
    event = _make_event(time_str="not-a-time")
    show = event.to_show(_club())
    assert show is None


def test_to_show_parses_9pm_show():
    """to_show() correctly parses a 9:00 PM show time."""
    event = _make_event(date_str="April 11, 2026", time_str="Doors: 8:45 PM - Show: 9:00 PM")
    show = event.to_show(_club())

    assert show is not None
    assert show.date.hour == 21
    assert show.date.minute == 0


def test_extractor_parses_title_and_url():
    """Extractor correctly extracts title and event URL from a card."""
    from laughtrack.scrapers.implementations.venues.sports_drink.extractor import (
        SportsDrinkExtractor,
    )

    html = _listing_page([
        _card_html(
            title="Ian Lara at SPORTS DRINK (Friday, 7:00p)",
            event_url="https://app.opendate.io/e/ian-lara-at-sports-drink-friday-7-00p-april-03-2026-565468",
            date_str="April 03, 2026",
            time_str="Doors: 6:30 PM - Show: 7:00 PM",
        )
    ])
    events = SportsDrinkExtractor.extract_events(html)

    assert len(events) == 1
    assert events[0].title == "Ian Lara at SPORTS DRINK (Friday, 7:00p)"
    assert events[0].event_url == "https://app.opendate.io/e/ian-lara-at-sports-drink-friday-7-00p-april-03-2026-565468"
    assert events[0].date_str == "April 03, 2026"
    assert events[0].time_str == "Doors: 6:30 PM - Show: 7:00 PM"


def test_extractor_skips_card_without_stretched_link():
    """Extractor skips cards that have no stretched-link anchor."""
    from laughtrack.scrapers.implementations.venues.sports_drink.extractor import (
        SportsDrinkExtractor,
    )

    bad_card = """
<div class="card confirm-card">
<div class="card-body">
<p class="mb-0">April 03, 2026</p>
<p class="mb-0">Doors: 6:30 PM - Show: 7:00 PM</p>
</div>
</div>"""
    events = SportsDrinkExtractor.extract_events(f"<html><body>{bad_card}</body></html>")
    assert len(events) == 0


def test_extractor_handles_multiple_concurrent_shows():
    """Extractor returns all cards including two shows at the same time on the same date."""
    from laughtrack.scrapers.implementations.venues.sports_drink.extractor import (
        SportsDrinkExtractor,
    )

    html = _listing_page([
        _card_html(
            title="Show A at SPORTS DRINK (Friday, 7:00p)",
            event_url="https://app.opendate.io/e/show-a-april-03-2026-111111",
            date_str="April 03, 2026",
            time_str="Doors: 6:30 PM - Show: 7:00 PM",
        ),
        _card_html(
            title="Show B at SPORTS DRINK (Friday, 9:00p)",
            event_url="https://app.opendate.io/e/show-b-april-03-2026-222222",
            date_str="April 03, 2026",
            time_str="Doors: 8:45 PM - Show: 9:00 PM",
        ),
    ])
    events = SportsDrinkExtractor.extract_events(html)
    assert len(events) == 2, "Both shows on the same date must be extracted"


@pytest.mark.asyncio
async def test_get_data_returns_none_on_extractor_exception(monkeypatch):
    """get_data() returns None and does not propagate when extract_events() raises."""
    from laughtrack.scrapers.implementations.venues.sports_drink.extractor import (
        SportsDrinkExtractor,
    )

    scraper = SportsDrinkScraper(_club())

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return "<html><body>some content</body></html>"

    def raising_extract(html: str):
        raise RuntimeError("parse failure")

    monkeypatch.setattr(SportsDrinkScraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(SportsDrinkExtractor, "extract_events", staticmethod(raising_extract))

    result = await scraper.get_data(LISTING_URL)
    assert result is None


def test_transformation_pipeline_produces_shows():
    """
    Core regression: transformation_pipeline.transform() must return at least one Show
    when given SportsDrinkPageData with real SportsDrinkEvent objects.

    If can_transform() returns False for SportsDrinkEvent (e.g., due to a type mismatch
    between the transformer's generic parameter and the event type), transform()
    silently returns an empty list with no error.
    """
    club = _club()
    scraper = SportsDrinkScraper(club)

    events = [
        _make_event("Ian Lara at SPORTS DRINK (Friday, 7:00p)"),
        _make_event("Jake Cornell at SPORTS DRINK (Saturday, 9:00p)"),
    ]
    page_data = SportsDrinkPageData(event_list=events)

    shows = scraper.transformation_pipeline.transform(page_data)

    assert len(shows) > 0, (
        "transformation_pipeline.transform() returned 0 Shows from SportsDrinkPageData — "
        "check SportsDrinkEventTransformer.can_transform() and that the transformer is "
        "registered with the correct generic type"
    )
    assert all(isinstance(s, Show) for s in shows)


def test_to_show_handles_compact_time_format():
    """to_show() parses compact AM/PM format ('7:00PM' with no space) correctly."""
    event = _make_event(time_str="Doors: 6:30PM - Show: 7:00PM")
    show = event.to_show(_club())

    assert show is not None, "Compact time format 'Show: 7:00PM' should not return None"
    assert show.date.hour == 19
    assert show.date.minute == 0
