"""Tests for PalmBeachImprovScraper and Kravis calendar extraction."""

import json
from unittest.mock import patch

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.palm_beach_improv import (
    PalmBeachImprovEvent,
    _parse_kravis_datetime,
)
from laughtrack.scrapers.implementations.venues.palm_beach_improv.data import (
    PalmBeachImprovPageData,
)
from laughtrack.scrapers.implementations.venues.palm_beach_improv.extractor import (
    PalmBeachImprovExtractor,
)
from laughtrack.scrapers.implementations.venues.palm_beach_improv.scraper import (
    PalmBeachImprovScraper,
)


LISTING_URL = "https://www.kravis.org/performance-calendar/improv/"
EVENT_URL = "https://www.kravis.org/events/kevin-nealon/"


def _club() -> Club:
    club = Club(
        id=379,
        name="Palm Beach Improv",
        address="701 Okeechobee Boulevard",
        website="https://www.kravis.org/performance-calendar/improv/",
        popularity=0,
        zip_code="33401",
        phone_number="",
        visible=True,
        timezone="America/New_York",
        city="West Palm Beach",
        state="FL",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="custom",
        scraper_key="palm_beach_improv",
        source_url=LISTING_URL,
        external_id=None,
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _ajax_response() -> str:
    payload = {
        "data": {
            "performances": [
                {
                    "id": 1,
                    "title": "KEVIN NEALON",
                    "thumbnail": "https://www.kravis.org/nealon.webp",
                    "dates": [
                        {"date": "Fri, May 08 2026 @ 7:30pm"},
                        {"date": "Sat, May 09 2026 @ 7:30pm"},
                    ],
                    "link": EVENT_URL,
                    "location": "Helen K. Persson Hall",
                },
                {
                    "id": 2,
                    "title": "GISELLE",
                    "dates": [{"date": "Sun, May 10 2026 @ 2:00pm"}],
                    "link": "https://www.kravis.org/events/ballet-palm-beach-presents-giselle/",
                    "location": "Alexander W. Dreyfoos Concert Hall",
                },
            ]
        }
    }
    return f"<html><body><pre>{json.dumps(payload)}</pre></body></html>"


def test_parse_ajax_response_extracts_performances():
    performances = PalmBeachImprovExtractor.parse_ajax_response(_ajax_response())

    assert len(performances) == 2
    assert performances[0]["title"] == "KEVIN NEALON"


def test_detail_page_is_improv_matches_page_text():
    html = "<html><body><main><h1>Kevin Nealon</h1><p>Palm Beach Improv at the Kravis Center</p></main></body></html>"

    assert PalmBeachImprovExtractor.detail_page_is_improv(html)


def test_detail_page_is_improv_ignores_navigation_text():
    html = """
    <html>
      <body>
        <nav><a href="/performance-calendar/improv/">Palm Beach Improv at the Kravis Center</a></nav>
        <main><h1>A Midsummer Night's Dream</h1><p>Ballet Florida presents.</p></main>
      </body>
    </html>
    """

    assert not PalmBeachImprovExtractor.detail_page_is_improv(html)


def test_events_from_performances_expands_dates():
    performances = PalmBeachImprovExtractor.parse_ajax_response(_ajax_response())
    events = PalmBeachImprovExtractor.events_from_performances([performances[0]])

    assert len(events) == 2
    assert events[0].title == "KEVIN NEALON"
    assert events[0].event_url == EVENT_URL


def test_event_to_show_parses_kravis_datetime():
    event = PalmBeachImprovEvent(
        title="KEVIN NEALON",
        date_str="Fri, May 08 2026 @ 7:30pm",
        event_url=EVENT_URL,
        location="Helen K. Persson Hall",
    )

    show = event.to_show(_club())

    assert show is not None
    assert show.name == "KEVIN NEALON"
    assert show.date.hour == 19
    assert show.date.minute == 30
    assert show.room == "Helen K. Persson Hall"
    assert show.tickets[0].purchase_url == EVENT_URL


def test_event_to_show_returns_none_for_malformed_date_str():
    # Missing AM/PM marker — does not match either _DATE_FORMATS pattern.
    # Without this guard, a Kravis format change would silently zero out the
    # venue: every performance's to_show would return None and be dropped.
    event = PalmBeachImprovEvent(
        title="KEVIN NEALON",
        date_str="Fri, May 08 2026 @ 7:30",
        event_url=EVENT_URL,
        location="Helen K. Persson Hall",
    )

    assert event.to_show(_club()) is None


def test_parse_kravis_datetime_warns_and_falls_back_for_unknown_timezone():
    # Per TASK-1908 (commit 8d44f66d), a typo'd / blank-but-non-empty
    # clubs.timezone must not silently zero out the venue. _parse_kravis_datetime
    # warns and falls back to America/New_York instead of returning None.
    with patch(
        "laughtrack.core.entities.event.palm_beach_improv.Logger"
    ) as mock_logger:
        result = _parse_kravis_datetime(
            "Fri, May 08 2026 @ 7:30pm", "America/Bogus_Made_Up"
        )

    assert result is not None
    assert result.tzinfo is not None
    assert result.tzinfo.zone == "America/New_York"
    assert result.hour == 19
    assert result.minute == 30
    mock_logger.warn.assert_called_once()
    assert "America/Bogus_Made_Up" in mock_logger.warn.call_args[0][0]


@pytest.mark.asyncio
async def test_get_data_filters_to_detail_pages_with_improv(monkeypatch):
    scraper = PalmBeachImprovScraper(_club())

    async def fake_fetch_html_with_js(self, url: str) -> str:
        if "admin-ajax.php" in url:
            return _ajax_response()
        if url == EVENT_URL:
            return "<html><body><main>Palm Beach Improv at the Kravis Center</main></body></html>"
        return "<html><body><main>Not an Improv page</main></body></html>"

    monkeypatch.setattr(
        PalmBeachImprovScraper,
        "_fetch_html_with_js",
        fake_fetch_html_with_js,
    )

    result = await scraper.get_data("https://www.kravis.org/wp-admin/admin-ajax.php")

    assert isinstance(result, PalmBeachImprovPageData)
    assert len(result.event_list) == 2
    assert {event.title for event in result.event_list} == {"KEVIN NEALON"}


def test_looks_like_improv_candidate_matches_comedy_keyword():
    performance = {
        "title": "Stand-Up Comedy Night",
        "location": "Alexander W. Dreyfoos Concert Hall",
    }

    assert PalmBeachImprovExtractor.looks_like_improv_candidate(performance)


def test_looks_like_improv_candidate_matches_persson_hall_location():
    performance = {
        "title": "KEVIN NEALON",
        "location": "Helen K. Persson Hall",
        "link": "https://www.kravis.org/events/kevin-nealon/",
    }

    assert PalmBeachImprovExtractor.looks_like_improv_candidate(performance)


def test_looks_like_improv_candidate_rejects_unrelated_performance():
    performance = {
        "title": "GISELLE",
        "location": "Alexander W. Dreyfoos Concert Hall",
        "link": "https://www.kravis.org/events/ballet-palm-beach-presents-giselle/",
    }

    assert not PalmBeachImprovExtractor.looks_like_improv_candidate(performance)


@pytest.mark.asyncio
async def test_get_data_skips_detail_fetch_for_non_candidates(monkeypatch):
    scraper = PalmBeachImprovScraper(_club())
    fetched_urls: list[str] = []

    async def fake_fetch_html_with_js(self, url: str) -> str:
        fetched_urls.append(url)
        if "admin-ajax.php" in url:
            return _ajax_response()
        if url == EVENT_URL:
            return "<html><body><main>Palm Beach Improv at the Kravis Center</main></body></html>"
        return "<html><body><main>Not an Improv page</main></body></html>"

    monkeypatch.setattr(
        PalmBeachImprovScraper,
        "_fetch_html_with_js",
        fake_fetch_html_with_js,
    )

    await scraper.get_data("https://www.kravis.org/wp-admin/admin-ajax.php")

    # KEVIN NEALON's detail page must be fetched (Persson Hall), but the
    # Dreyfoos-Hall non-comedy event must be skipped without a fetch.
    assert EVENT_URL in fetched_urls
    assert (
        "https://www.kravis.org/events/ballet-palm-beach-presents-giselle/"
        not in fetched_urls
    )


@pytest.mark.asyncio
async def test_get_data_returns_none_when_no_improv_events(monkeypatch):
    scraper = PalmBeachImprovScraper(_club())

    async def fake_fetch_html_with_js(self, url: str) -> str:
        if "admin-ajax.php" in url:
            return _ajax_response()
        return "<html><body><main>Not an Improv page</main></body></html>"

    monkeypatch.setattr(
        PalmBeachImprovScraper,
        "_fetch_html_with_js",
        fake_fetch_html_with_js,
    )

    result = await scraper.get_data("https://www.kravis.org/wp-admin/admin-ajax.php")

    assert result is None
