"""End-to-end tests for TicketleapScraper (listing → detail pipeline)."""

from __future__ import annotations

import importlib.util
import json
from typing import List

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.implementations.ticketleap.scraper import TicketleapScraper


@pytest.fixture
def club() -> Club:
    return Club(
        id=837,
        name="Mesquite St. Comedy Club",
        address="617 Mesquite Street",
        website="https://www.mesquitestreet.com",
        scraping_url="https://events.ticketleap.com/events/funny",
        popularity=0,
        zip_code="78401",
        phone_number="",
        visible=True,
        timezone="America/Chicago",
        city="Corpus Christi",
        state="TX",
        scraper="ticketleap",
    )


def _listing_html(event_ids: List[int]) -> str:
    payload = json.dumps(
        {
            "event": "orglisting_page_view",
            "listing_slug": "funny",
            "event_ids": event_ids,
            "display_type": "grid",
        }
    )
    return (
        "<html><body><script>"
        f"window.dataLayer=window.dataLayer||[];window.dataLayer.push({payload});"
        "</script></body></html>"
    )


def _detail_html(
    event_id: int,
    name: str,
    start: str,
    location_name: str = "MESQUITE ST COMEDY CLUB DOWNTOWN",
) -> str:
    ld = {
        "@context": "http://schema.org",
        "@type": "Event",
        "name": name,
        "url": f"https://events.ticketleap.com/tickets/funny/{name.lower().replace(' ', '-')}",
        "startDate": start,
        "endDate": start,
        "offers": [
            {
                "@type": "Offer",
                "name": "General Admission",
                "price": "25.00",
                "priceCurrency": "USD",
                "availability": "InStock",
                "url": f"https://events.ticketleap.com/tickets/funny/{event_id}",
            }
        ],
        "location": {
            "@type": "Place",
            "name": location_name,
            "address": {
                "@type": "PostalAddress",
                "streetAddress": "617 Mesquite street",
                "addressLocality": "Corpus Christi",
                "addressRegion": "TX",
                "postalCode": "78401",
                "addressCountry": "US",
            },
        },
    }
    return (
        f'<html><body><script type="application/ld+json">{json.dumps(ld)}</script>'
        "</body></html>"
    )


@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_detail_urls(monkeypatch, club):
    s = TicketleapScraper(club)

    async def fake_js_fetch(url):
        assert url == "https://events.ticketleap.com/events/funny"
        return _listing_html([111, 222, 333])

    monkeypatch.setattr(s, "_fetch_html_with_js", fake_js_fetch)

    targets = await s.collect_scraping_targets()
    assert targets == [
        "https://events.ticketleap.com/event/111",
        "https://events.ticketleap.com/event/222",
        "https://events.ticketleap.com/event/333",
    ]


@pytest.mark.asyncio
async def test_collect_scraping_targets_empty_when_no_ids(monkeypatch, club):
    s = TicketleapScraper(club)

    async def fake_js_fetch(url):
        return "<html><body>No events here.</body></html>"

    monkeypatch.setattr(s, "_fetch_html_with_js", fake_js_fetch)
    assert await s.collect_scraping_targets() == []


@pytest.mark.asyncio
async def test_collect_scraping_targets_empty_when_js_fetch_returns_none(monkeypatch, club):
    """If Playwright is unavailable or times out, _fetch_html_with_js returns None."""
    s = TicketleapScraper(club)

    async def fake_js_fetch(url):
        return None

    monkeypatch.setattr(s, "_fetch_html_with_js", fake_js_fetch)
    assert await s.collect_scraping_targets() == []


@pytest.mark.asyncio
async def test_collect_scraping_targets_empty_when_missing_url(monkeypatch, club):
    club.scraping_url = ""
    s = TicketleapScraper(club)
    assert await s.collect_scraping_targets() == []


@pytest.mark.asyncio
async def test_get_data_extracts_single_event(monkeypatch, club):
    s = TicketleapScraper(club)

    async def fake_fetch(url, **kwargs):
        return _detail_html(111, "Craig Conant", "2026-04-11T19:30:00-05:00")

    monkeypatch.setattr(s, "fetch_html", fake_fetch)
    data = await s.get_data("https://events.ticketleap.com/event/111")
    assert data is not None
    assert len(data.event_list) == 1
    event = data.event_list[0]
    assert event.name == "Craig Conant"
    assert event.location.name == "MESQUITE ST COMEDY CLUB DOWNTOWN"
    assert event.offers and event.offers[0].price == "25.00"


@pytest.mark.asyncio
async def test_get_data_returns_none_when_no_json_ld(monkeypatch, club):
    s = TicketleapScraper(club)

    async def fake_fetch(url, **kwargs):
        return "<html><body>No JSON-LD here.</body></html>"

    monkeypatch.setattr(s, "fetch_html", fake_fetch)
    assert await s.get_data("https://events.ticketleap.com/event/999") is None


@pytest.mark.asyncio
async def test_get_data_swallows_exceptions_and_returns_none(monkeypatch, club):
    s = TicketleapScraper(club)

    async def boom(url, **kwargs):
        raise RuntimeError("timeout")

    monkeypatch.setattr(s, "fetch_html", boom)
    assert await s.get_data("https://events.ticketleap.com/event/999") is None


@pytest.mark.asyncio
async def test_full_pipeline_produces_shows(monkeypatch, club):
    """Exercise collect_scraping_targets → get_data → transform path end to end."""
    s = TicketleapScraper(club)

    listing = _listing_html([111, 222])
    detail_by_id = {
        "https://events.ticketleap.com/event/111": _detail_html(
            111, "Craig Conant", "2026-04-11T19:30:00-05:00"
        ),
        "https://events.ticketleap.com/event/222": _detail_html(
            222, "David Koechner live", "2026-04-24T19:00:00-05:00"
        ),
    }

    async def fake_js_fetch(url):
        assert url == "https://events.ticketleap.com/events/funny"
        return listing

    async def fake_fetch(url, **kwargs):
        return detail_by_id[url]

    monkeypatch.setattr(s, "_fetch_html_with_js", fake_js_fetch)
    monkeypatch.setattr(s, "fetch_html", fake_fetch)

    shows = await s.scrape_async()
    assert len(shows) == 2
    names = {show.name for show in shows}
    assert names == {"Craig Conant", "David Koechner live"}
    for show in shows:
        assert show.club_id == club.id
        assert show.date is not None


@pytest.mark.asyncio
async def test_multi_location_drift_is_logged(monkeypatch, club):
    """When events span >1 location.name, scrape_async logs the drift tally."""
    import laughtrack.scrapers.implementations.ticketleap.scraper as scraper_mod

    s = TicketleapScraper(club)

    listing = _listing_html([111, 222, 333])
    detail_by_id = {
        "https://events.ticketleap.com/event/111": _detail_html(
            111, "Craig Conant", "2099-04-11T19:30:00-05:00"
        ),
        "https://events.ticketleap.com/event/222": _detail_html(
            222,
            "Southside Show",
            "2099-04-24T19:00:00-05:00",
            location_name="MESQUITE ST COMEDY CLUB SOUTHSIDE",
        ),
        "https://events.ticketleap.com/event/333": _detail_html(
            333,
            "Another Southside",
            "2099-05-01T19:00:00-05:00",
            location_name="MESQUITE ST COMEDY CLUB SOUTHSIDE",
        ),
    }

    async def fake_js_fetch(url):
        return listing

    async def fake_fetch(url, **kwargs):
        return detail_by_id[url]

    monkeypatch.setattr(s, "_fetch_html_with_js", fake_js_fetch)
    monkeypatch.setattr(s, "fetch_html", fake_fetch)

    info_calls: list[str] = []
    original_info = scraper_mod.Logger.info

    def capture_info(message, *args, **kwargs):
        info_calls.append(message)
        return original_info(message, *args, **kwargs)

    monkeypatch.setattr(scraper_mod.Logger, "info", capture_info)

    await s.scrape_async()

    drift_logs = [m for m in info_calls if "TicketLeap multi-location detected" in m]
    assert len(drift_logs) == 1, f"expected 1 drift log, got {drift_logs}"
    assert "MESQUITE ST COMEDY CLUB DOWNTOWN" in drift_logs[0]
    assert "MESQUITE ST COMEDY CLUB SOUTHSIDE" in drift_logs[0]


@pytest.mark.asyncio
async def test_single_location_does_not_log_drift(monkeypatch, club):
    """When all events share one location.name, no drift log is emitted."""
    import laughtrack.scrapers.implementations.ticketleap.scraper as scraper_mod

    s = TicketleapScraper(club)

    listing = _listing_html([111, 222])
    detail_by_id = {
        "https://events.ticketleap.com/event/111": _detail_html(
            111, "Craig Conant", "2099-04-11T19:30:00-05:00"
        ),
        "https://events.ticketleap.com/event/222": _detail_html(
            222, "David Koechner live", "2099-04-24T19:00:00-05:00"
        ),
    }

    async def fake_js_fetch(url):
        return listing

    async def fake_fetch(url, **kwargs):
        return detail_by_id[url]

    monkeypatch.setattr(s, "_fetch_html_with_js", fake_js_fetch)
    monkeypatch.setattr(s, "fetch_html", fake_fetch)

    info_calls: list[str] = []
    original_info = scraper_mod.Logger.info

    def capture_info(message, *args, **kwargs):
        info_calls.append(message)
        return original_info(message, *args, **kwargs)

    monkeypatch.setattr(scraper_mod.Logger, "info", capture_info)

    await s.scrape_async()

    drift_logs = [m for m in info_calls if "TicketLeap multi-location detected" in m]
    assert drift_logs == []
