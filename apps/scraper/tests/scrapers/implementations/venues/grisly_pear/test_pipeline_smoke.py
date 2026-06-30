"""Pipeline smoke tests for the Grisly Pear calendar scraper."""

from datetime import date

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.venues.grisly_pear.extractor import (
    GrislyPearExtractor,
)
from laughtrack.scrapers.implementations.venues.grisly_pear.scraper import (
    GrislyPearScraper,
)


_CALENDAR_HTML = """
<html><body>
  <a aria-label="View 8PM Comedy Show at The Grisly Pear Greenwich Village"
     href="/events/8pm-comedy-show-at-the-grisly-pear-greenwich-village-2099-07-01200000">
    <img alt="8PM Comedy Show at The Grisly Pear Greenwich Village">
  </a>
  <a aria-label="View 7:30PM Comedy Show at The Grisly Pear Midtown"
     href="/events/7-30pm-comedy-show-at-the-grisly-pear-midtown-2099-07-01193000">
    <img alt="7:30PM Comedy Show at The Grisly Pear Midtown">
  </a>
  <a aria-label="View Midnight Comedy Show at Grisly Pear Classic"
     href="/events/midnight-comedy-show-at-grisly-pear-classic-2099-07-01235900">
    <img alt="Midnight Comedy Show at Grisly Pear Classic">
  </a>
  <a aria-label="View Old Show"
     href="/events/old-show-at-the-grisly-pear-midtown-2026-06-01200000">
    Old Show
  </a>
  <a aria-label="View Undated Show" href="/events/undated-show">Undated</a>
</body></html>
"""


def _club(name: str = "The Grisly Pear Greenwich Village") -> Club:
    club = Club(
        id=6 if "Greenwich" in name else 7,
        name=name,
        address="107 MacDougal St",
        website="https://www.grislypearstandup.com",
        popularity=0,
        zip_code="10012",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="custom",
        scraper_key="grisly_pear",
        source_url="https://www.grislypearstandup.com/calendar",
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def test_extract_events_keeps_future_greenwich_and_classic_links():
    events = GrislyPearExtractor.extract_events(
        _CALENDAR_HTML,
        base_url="https://www.grislypearstandup.com/calendar",
        club_name="The Grisly Pear Greenwich Village",
        today=date(2026, 6, 30),
    )

    assert [event.name for event in events] == [
        "8PM Comedy Show at The Grisly Pear Greenwich Village",
        "Midnight Comedy Show at Grisly Pear Classic",
    ]
    assert all(event.url.startswith("https://www.grislypearstandup.com/events/") for event in events)


def test_extract_events_keeps_future_midtown_links_only():
    events = GrislyPearExtractor.extract_events(
        _CALENDAR_HTML,
        base_url="https://www.grislypearstandup.com/calendar",
        club_name="The Grisly Pear Midtown",
        today=date(2026, 6, 30),
    )

    assert [event.name for event in events] == [
        "7:30PM Comedy Show at The Grisly Pear Midtown",
    ]


def test_to_show_uses_slug_datetime_and_fallback_ticket():
    event = GrislyPearExtractor.extract_events(
        _CALENDAR_HTML,
        base_url="https://www.grislypearstandup.com/calendar",
        club_name="The Grisly Pear Greenwich Village",
        today=date(2026, 6, 30),
    )[0]

    show = event.to_show(_club())

    assert show is not None
    assert show.name == "8PM Comedy Show at The Grisly Pear Greenwich Village"
    assert show.date.isoformat() == "2099-07-01T20:00:00-04:00"
    assert show.show_page_url == event.url
    assert len(show.tickets) == 1
    assert show.tickets[0].purchase_url == event.url
    assert show.tickets[0].price is None


def test_scraper_transforms_listing_html_without_detail_fetch(monkeypatch):
    scraper = GrislyPearScraper(_club())

    async def fake_fetch_html(url):
        assert url == "https://www.grislypearstandup.com/calendar"
        return _CALENDAR_HTML

    monkeypatch.setattr(scraper, "fetch_html", fake_fetch_html)

    shows = scraper.scrape()

    assert len(shows) == 2
    assert [show.name for show in shows] == [
        "8PM Comedy Show at The Grisly Pear Greenwich Village",
        "Midnight Comedy Show at Grisly Pear Classic",
    ]
