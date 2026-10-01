"""Pipeline smoke tests for the Grisly Pear calendar scraper."""

from datetime import date
import json
from pathlib import Path

import pytest
import time_machine
from bs4 import BeautifulSoup
from laughtrack.scrapers.implementations.venues.grisly_pear.data import GrislyPearEvent
from laughtrack.foundation.infrastructure.http.diagnostics import ScrapeDiagnostics, bind_diagnostics, reset_diagnostics

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
        address="107 MacDougal St" if "Greenwich" in name else "243 W 54th St",
        website="https://www.grislypearstandup.com",
        popularity=0,
        zip_code="10012" if "Greenwich" in name else "10019",
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



_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "docs/audits").is_dir())
_LINEUP = _ROOT / "docs/audits/2026-09-26-missing-lineups/grisly"
_PRICES = _ROOT / "docs/audits/2026-09-27-price-extraction/parent"


def _candidate(show_id):
    rows = json.loads((_PRICES / "grisly-findings.json").read_text())
    row = next(row for row in rows if row["show_id"] == show_id)
    day, clock = GrislyPearExtractor._parse_dated_event_url(row["url"])
    return GrislyPearEvent("Comedy Show", row["url"], day.isoformat(), clock)


def _detail(show_id):
    return (_PRICES / f"grisly-{show_id}.html").read_text()


def test_current_calendar_detail_identity(monkeypatch):
    """Real legacy/current aliases converge; a changed date or venue is rejected."""
    calendar = (_LINEUP / "calendar-current-url-excerpt.html").read_text()
    for club in (_club(), _club("The Grisly Pear Midtown")):
        events = GrislyPearExtractor.extract_events(calendar, base_url=club.scraping_url,
                                                  club_name=club.name, today=date(2026, 9, 26))
        assert len(events) == 1
        detail = (_LINEUP / "6039376-lineup-excerpt.html").read_text() if club.id == 6 else _detail(6395740)
        parsed = GrislyPearExtractor.enrich_detail(events[0], detail, club)
        assert parsed.date == events[0].date
        assert parsed.time == events[0].time
        assert parsed.to_show(club).lineup
        scraper = GrislyPearScraper(club)
        async def fake_fetch(url):
            return calendar if url == club.scraping_url else detail
        monkeypatch.setattr(scraper, "fetch_html", fake_fetch)
        with time_machine.travel("2026-09-26T12:00:00Z", tick=False):
            shows = scraper.scrape()
        assert len(shows) == 1
        assert shows[0].date == parsed.to_show(club).date
        assert shows[0].club_id == club.id
        assert shows[0].lineup
    old = _candidate(6395740)
    current = GrislyPearExtractor.enrich_detail(old, _detail(6395740), _club("The Grisly Pear Midtown"))
    assert current.url.endswith("10-02-26-07-30-pm")
    assert old.date == current.date and old.time == current.time
    with pytest.raises(ValueError, match="start date"):
        GrislyPearExtractor.enrich_detail(_candidate(6331162), _detail(6331162), _club("The Grisly Pear Midtown"))
    with pytest.raises(ValueError, match="physical venue"):
        GrislyPearExtractor.enrich_detail(old, _detail(6395740), _club())


def test_explicit_detail_lineups():
    candidate = _candidate(6150999)
    detail = _detail(6150999)
    event = GrislyPearExtractor.enrich_detail(candidate, detail, _club())
    assert {person.name for person in event.to_show(_club()).lineup} == {"Abby Washuta", "Tina Zhu"}
    assert len(event.performers) == 2
    # Featuring fallback works even when the structured performer field is empty.
    soup = BeautifulSoup(detail, "html.parser")
    script = soup.find("script", type="application/ld+json")
    payload = json.loads(script.string)
    payload[0]["performer"] = []
    script.string = json.dumps(payload)
    event = GrislyPearExtractor.enrich_detail(candidate, str(soup), _club())
    assert {person.name for person in event.to_show(_club()).lineup} == {"Abby Washuta", "Tina Zhu"}
    for node in soup.select(".event-comedians-container"):
        node.decompose()
    event = GrislyPearExtractor.enrich_detail(candidate, str(soup), _club())
    assert event.to_show(_club()).lineup == []  # No title or biography inference.


@pytest.mark.parametrize("show_id,club_name,expected", [
    (6150999, "The Grisly Pear Greenwich Village", 10.0),
    (6395740, "The Grisly Pear Midtown", 20.0),
    (6039378, "The Grisly Pear Greenwich Village", None),
])
def test_real_purchase_base_prices_and_unavailable_inventory(show_id, club_name, expected):
    event = GrislyPearExtractor.enrich_detail(_candidate(show_id), _detail(show_id), _club(club_name))
    assert event.to_show(_club(club_name)).tickets[0].price == expected
    assert event.price not in {12.37, 23.24}  # Mandatory fees are not base price.


def test_purchase_controls_fallback_never_uses_inclusive_total():
    soup = BeautifulSoup(_detail(6395740), "html.parser")
    for node in soup.select(".breakdown-base-original"):
        node.decompose()
    event = GrislyPearExtractor.enrich_detail(_candidate(6395740), str(soup), _club("The Grisly Pear Midtown"))
    assert event.price == 20.0  # Explicit matched JSON-LD Offer base price.
    script = soup.find("script", type="application/ld+json")
    payload = json.loads(script.string)
    payload[0]["offers"]["price"] = "0.00"
    script.string = json.dumps(payload)
    event = GrislyPearExtractor.enrich_detail(_candidate(6395740), str(soup), _club("The Grisly Pear Midtown"))
    assert event.price is None


@pytest.mark.asyncio
async def test_calendar_aliases_and_detail_failure_block_cleanup(monkeypatch):
    club = _club("The Grisly Pear Midtown")
    scraper = GrislyPearScraper(club)
    old = _candidate(6395740)
    verified = GrislyPearExtractor.enrich_detail(old, _detail(6395740), club)
    wrong = _candidate(6331162)
    def anchor(url):
        return f'<a aria-label="Comedy Show at The Grisly Pear Midtown" href="{url}">Comedy Show</a>'
    calendar = anchor(old.url) + anchor(verified.url) + anchor(wrong.url)
    fetched = []
    async def fake_fetch(url):
        fetched.append(url)
        if url == club.scraping_url:
            return calendar
        return _detail(6331162) if url == wrong.url else _detail(6395740)
    monkeypatch.setattr(scraper, "fetch_html", fake_fetch)
    diagnostics = ScrapeDiagnostics()
    token = bind_diagnostics(diagnostics)
    try:
        with time_machine.travel("2026-09-26T12:00:00Z", tick=False):
            data = await scraper.get_data(club.scraping_url)
    finally:
        reset_diagnostics(token)
    assert len(data.event_list) == 1
    assert data.event_list[0].url == verified.url
    assert diagnostics.fetches_failed == 1
    assert len(fetched) == 4


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["empty", "exception", "conflicting_alias"])
async def test_incomplete_details_are_not_returned_or_reconciled(monkeypatch, failure):
    club = _club("The Grisly Pear Midtown")
    scraper = GrislyPearScraper(club)
    old = _candidate(6395740)
    current = GrislyPearExtractor.enrich_detail(old, _detail(6395740), club)
    calendar = ''.join(f'<a aria-label="Comedy Show Midtown" href="{url}">Show</a>' for url in [old.url, current.url])
    async def fake_fetch(url):
        if url == club.scraping_url:
            return calendar
        if url == old.url:
            return _detail(6395740)
        if failure == "exception":
            raise TimeoutError("detail timeout")
        if failure == "empty":
            return None
        return _detail(6395740).replace('"Tanner Riley"', '"Different Person"').replace('Tanner Riley</a>', 'Different Person</a>')
    monkeypatch.setattr(scraper, "fetch_html", fake_fetch)
    diagnostics = ScrapeDiagnostics()
    token = bind_diagnostics(diagnostics)
    try:
        with time_machine.travel("2026-09-26T12:00:00Z", tick=False):
            data = await scraper.get_data(club.scraping_url)
    finally:
        reset_diagnostics(token)
    assert data.event_list == []
    assert diagnostics.fetches_failed > 0


@pytest.mark.parametrize("suffix,expected", [("10-02-26-12-00-am", "000000"), ("10-02-26-12-00-pm", "120000"), ("10-02-26-07-30-pm?utm=test", "193000")])
def test_current_url_clock_edges(suffix, expected):
    assert GrislyPearExtractor._parse_dated_event_url("https://www.grislypearstandup.com/events/show-" + suffix) == (date(2026, 10, 2), expected)
