"""
Unit tests for the New York Comedy Club single-venue-subdomain path.

The shared newyorkcomedyclub.com/calendar lists all three NYC venues, so the
scraper filters JSON-LD events by matching each event's street against the
club's address. A dedicated location subdomain (e.g.
stamford.newyorkcomedyclub.com) lists only that venue's shows, but its rendered
cards carry no street (the rendered path only knows the three NYC venues), so
the address filter would drop everything. get_data() detects the single-venue
case (all JSON-LD events share one street matching the club) and returns the
JSON-LD events directly, skipping the filter. The multi-venue calendar still
filters per venue.
"""

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.venues.new_york_comedy_club.scraper import (
    NewYorkComedyClubScraper,
)


def _club(address: str, source_url: str) -> Club:
    club = Club(
        id=99,
        name="NYCC Test",
        address=address,
        website="https://newyorkcomedyclub.com",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )
    club.active_scraping_source = ScrapingSource(
        id=1, club_id=club.id, platform="custom", scraper_key="new_york_comedy_club", source_url=source_url
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _event_json_ld(name: str, street: str, locality: str, slug: str) -> str:
    return (
        '{"@context":"https://schema.org","@type":"ComedyEvent","name":"%s",'
        '"startDate":"2027-01-10T20:00:00-05:00",'
        '"location":{"@type":"Place","name":"%s","address":{"@type":"PostalAddress",'
        '"streetAddress":"%s","addressLocality":"%s","addressRegion":"NY","postalCode":"10001"}},'
        '"url":"https://stamford.newyorkcomedyclub.com/events/%s",'
        '"offers":{"@type":"Offer","price":"25","priceCurrency":"USD",'
        '"url":"https://stamford.newyorkcomedyclub.com/events/%s"}}'
        % (name, locality, street, locality, slug, slug)
    )


def _page(*event_json: str) -> str:
    blocks = "\n".join(
        f'<script type="application/ld+json">{ev}</script>' for ev in event_json
    )
    return f"<html><head>{blocks}</head><body></body></html>"


@pytest.mark.asyncio
async def test_single_venue_subdomain_returns_all_without_filter(monkeypatch):
    """A dedicated subdomain (one street matching the club) returns every event."""
    html = _page(
        _event_json_ld("Stamford Show A", "230 Tresser Blvd", "Stamford", "a"),
        _event_json_ld("Stamford Show B", "230 Tresser Blvd", "Stamford", "b"),
    )
    club = _club("230 Tresser Blvd, Stamford, CT 06901", "https://stamford.newyorkcomedyclub.com/calendar")
    scraper = NewYorkComedyClubScraper(club)

    async def fake_fetch_html(url):
        return html

    monkeypatch.setattr(scraper, "fetch_html", fake_fetch_html)

    data = await scraper.get_data("https://stamford.newyorkcomedyclub.com/calendar")
    assert data is not None
    assert len(data.event_list) == 2


@pytest.mark.asyncio
async def test_multi_venue_calendar_still_filters_by_address(monkeypatch):
    """The shared calendar (multiple streets) keeps the per-venue address filter."""
    html = _page(
        _event_json_ld("Stamford Show", "230 Tresser Blvd", "Stamford", "s"),
        _event_json_ld("Midtown Show", "241 East 24th Street", "New York", "m"),
    )
    club = _club("230 Tresser Blvd, Stamford, CT 06901", "https://newyorkcomedyclub.com/calendar")
    scraper = NewYorkComedyClubScraper(club)

    async def fake_fetch_html(url):
        return html

    monkeypatch.setattr(scraper, "fetch_html", fake_fetch_html)

    data = await scraper.get_data("https://newyorkcomedyclub.com/calendar")
    assert data is not None
    assert len(data.event_list) == 1
    assert data.event_list[0].name == "Stamford Show"
