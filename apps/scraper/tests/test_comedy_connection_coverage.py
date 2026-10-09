"""Native Comedy Connection RSC contract; SeatEngine is no longer its calendar."""

import json
from copy import deepcopy
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.comedian.model import Comedian
from laughtrack.core.entities.show.handler import ShowHandler
from laughtrack.scrapers.implementations.venues.comedy_connection.extractor import ComedyConnectionExtractor
from laughtrack.scrapers.implementations.venues.comedy_connection.scraper import ComedyConnectionScraper
from laughtrack.utilities.domain.show.utils import ShowUtils

ROOT = "https://www.ricomedyconnection.com"
DETAIL = ROOT + "/events/michael-longfellow-2026"
SHOWS = [
    {
        "id": 21838,
        "startDate": "2026-10-09T23:00:00Z",
        "status": "on-sale",
        "ticketUrl": "https://events.tixologi.com/event/12821/tickets?isPunchup=true",
    },
    {
        "id": 21839,
        "startDate": "2026-10-10T01:30:00Z",
        "status": "sold-out",
        "ticketUrl": "https://events.tixologi.com/event/12822/tickets?isPunchup=true",
    },
]


def page(shows=None, **event_changes):
    event = {
        "slug": "michael-longfellow-2026",
        "name": "Michael Longfellow",
        "shows": deepcopy(SHOWS if shows is None else shows),
        **event_changes,
    }
    flight = "9:" + json.dumps(
        ["$", "$L1", None, {"event": event, "relatedEvents": [{"name": "Unrelated", "shows": [{"id": 999}]}]}]
    )
    # The browser stream can split the event object across push boundaries.
    middle = len(flight) // 2
    scripts = "".join(
        "<script>self.__next_f.push([1," + json.dumps(part) + "])</script>"
        for part in (flight[:middle], flight[middle:])
    )
    graph = {
        "@graph": [
            {
                "@type": "ComedyEvent",
                "@id": DETAIL + "#show-" + str(s["id"]),
                "offers": {"price": "25"},
                "performer": {"name": "Michael Longfellow"},
            }
            for s in SHOWS
        ]
    }
    return scripts + '<script type="application/ld+json">' + json.dumps(graph) + "</script>"


@pytest.fixture
def scraper():
    club = Club(
        id=217,
        name="Comedy Connection",
        address="39 Warren Avenue",
        website=ROOT,
        popularity=0,
        zip_code="02914",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )
    source = ScrapingSource(
        club_id=217, platform="custom", scraper_key="comedy_connection", source_url=ROOT + "/events"
    )
    club.active_scraping_source = source
    club.scraping_sources = [source]
    return ComedyConnectionScraper(club)


def test_actual_ticket_links_multishow_and_sold_out_retention(scraper):
    events = ComedyConnectionExtractor.extract_events(page(), DETAIL)
    shows = [e.to_show(scraper.club, enhanced=False) for e in events]
    assert len(shows) == 2
    assert [(s.date.hour, s.date.minute) for s in shows] == [(19, 0), (21, 30)]
    assert [s.tickets[0].purchase_url for s in shows] == [s["ticketUrl"] for s in SHOWS]
    assert shows[1].tickets[0].sold_out is True
    assert shows[0].tickets[0].price == 25
    assert [c.name for c in shows[0].lineup] == ["Michael Longfellow"]
    repeated = [
        e.to_show(scraper.club, enhanced=False) for e in ComedyConnectionExtractor.extract_events(page(), DETAIL)
    ]
    assert len(ShowUtils.deduplicate_shows(shows + repeated)) == 2


@pytest.mark.parametrize(
    "title, performer, false_match",
    [
        ("Andre De Freitas", "André de Freitas", "Andre De"),
        ("Jerry Wayne Longmire", "Jerry Wayne Longmire", "Jerry Wayne"),
        ("One Funny Lisa Marie", "Lisa Marie", "One Funny"),
        ("Sarper Guven", "Sarper Güven", "Sarper Guven"),
    ],
)
def test_explicit_performer_prevents_persistence_title_substring_additions(scraper, title, performer, false_match):
    event = ComedyConnectionExtractor.extract_events(page(name=title), DETAIL)[0]
    event.performers = [performer]
    show = event.to_show(scraper.club)
    assert show.infer_lineup_from_title is False
    ShowHandler._process_comedian_additions(None, [show], {title: [Comedian(name=false_match)]})
    assert len(show.lineup) == 1
    assert show.lineup[0].name == Comedian(name=performer).name


def test_missing_structured_performer_keeps_title_fallback(scraper):
    event = ComedyConnectionExtractor.extract_events(page(), DETAIL)[0]
    event.performers = []
    show = event.to_show(scraper.club)
    assert show.infer_lineup_from_title is True
    ShowHandler._process_comedian_additions(None, [show], {show.name: [Comedian(name="Michael Longfellow")]})
    assert [c.name for c in show.lineup] == ["Michael Longfellow"]


@pytest.mark.asyncio
async def test_native_truncated_jsonld_performer_uses_verified_source_override(scraper, monkeypatch):
    html = (Path(__file__).parent / "fixtures" / "comedy_connection_andre.html").read_text()
    url = ROOT + "/events/andre-de-freitas-2026"
    raw = ComedyConnectionExtractor.extract_events(html, url)
    assert raw[0].name == "Andre De Freitas"
    assert raw[0].performers == ["Andre De"]  # Actual upstream JSON-LD defect.
    scraper.club.active_scraping_source.metadata = {"performer_overrides": {"Andre De Freitas": ["André de Freitas"]}}
    monkeypatch.setattr(scraper, "fetch_html", AsyncMock(return_value=html))
    data = await scraper.get_data(url)
    show = data.event_list[0].to_show(scraper.club)
    ShowHandler._process_comedian_additions(None, [show], {show.name: [Comedian(name="Andre De")]})
    assert [c.name for c in show.lineup] == ["André de Freitas"]
    assert show.tickets[0].purchase_url == raw[0].ticket_url
    unaffected = ComedyConnectionExtractor.extract_events(page(), DETAIL, {"Andre De Freitas": ["André de Freitas"]})
    assert unaffected[0].performers == ["Michael Longfellow"]


@pytest.mark.parametrize("overrides", [{"Andre De Freitas": "Andre"}, {"Andre De Freitas": []}])
def test_malformed_performer_override_fails(overrides):
    with pytest.raises(ValueError, match="performer overrides"):
        ComedyConnectionExtractor.extract_events(page(), DETAIL, overrides)


@pytest.mark.parametrize(
    "timestamp, hour, offset",
    [
        ("2026-11-01T05:30:00Z", 1, -4),
        ("2026-11-01T06:30:00Z", 1, -5),
        ("2027-02-06T00:00:00Z", 19, -5),
    ],
)
def test_utc_timestamp_preserves_dst_and_year(scraper, timestamp, hour, offset):
    show = deepcopy(SHOWS[0])
    show["startDate"] = timestamp
    result = ComedyConnectionExtractor.extract_events(page([show]), DETAIL)[0].to_show(scraper.club, enhanced=False)
    assert result.date.hour == hour
    assert result.date.utcoffset().total_seconds() == offset * 3600
    assert result.date.year == int(timestamp[:4])


@pytest.mark.parametrize("change", [{"ticketUrl": ""}, {"startDate": "2026-10-09T19:00:00"}, {"id": None}])
def test_incomplete_performance_fails_instead_of_returning_partial(change):
    second = {**SHOWS[1], **change}
    with pytest.raises((ValueError, KeyError)):
        ComedyConnectionExtractor.extract_events(page([SHOWS[0], second]), DETAIL)


def test_missing_primary_event_and_unexpected_empty_fail():
    with pytest.raises(ValueError):
        ComedyConnectionExtractor.extract_events(page(slug="another-event"), DETAIL)
    with pytest.raises(ValueError):
        ComedyConnectionExtractor.extract_events(page([]), DETAIL)
    assert ComedyConnectionExtractor.extract_events(page([], allShowsEnded=True), DETAIL) == []


@pytest.mark.asyncio
async def test_calendar_discovers_all_unique_local_series(scraper, monkeypatch):
    html = (
        '<a href="/events/michael-longfellow-2026">First</a>'
        '<a href="/events/anthony-rodia-2027">Later</a>'
        '<a href="/events/michael-longfellow-2026">Duplicate</a>'
        '<a href="https://other.example/events/no">Other venue</a>'
    )
    flight = "9:" + json.dumps({"events": [{"slug": "michael-longfellow-2026"}, {"slug": "anthony-rodia-2027"}]})
    html += "<script>self.__next_f.push([1," + json.dumps(flight) + "])</script>"
    monkeypatch.setattr(scraper, "fetch_html", AsyncMock(return_value=html))
    assert await scraper.collect_scraping_targets() == [DETAIL, ROOT + "/events/anthony-rodia-2027"]
    monkeypatch.setattr(scraper, "fetch_html", AsyncMock(return_value="<html>Broken calendar</html>"))
    with pytest.raises(ValueError):
        await scraper.collect_scraping_targets()

    monkeypatch.setattr(
        scraper,
        "fetch_html",
        AsyncMock(return_value=html.replace('<a href="/events/anthony-rodia-2027">Later</a>', "")),
    )
    with pytest.raises(ValueError, match="full event payload"):
        await scraper.collect_scraping_targets()
