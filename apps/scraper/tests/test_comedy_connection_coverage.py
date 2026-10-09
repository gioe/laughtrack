"""Native Comedy Connection RSC contract; SeatEngine is no longer its calendar."""

import json
from copy import deepcopy
from unittest.mock import AsyncMock

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
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
