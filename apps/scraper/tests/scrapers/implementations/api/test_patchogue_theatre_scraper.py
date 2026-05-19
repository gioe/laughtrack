"""Tests for the Patchogue Theatre (Bowery → OvationTix Performance) scraper."""

from __future__ import annotations

from typing import Dict

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.ovationtix import OvationTixEvent
from laughtrack.scrapers.implementations.api.patchogue_theatre.extractor import (
    event_from_performance_response,
    extract_performance_ids,
    is_comedy_relevant,
)
from laughtrack.scrapers.implementations.api.patchogue_theatre.scraper import (
    PatchogueTheatreScraper,
)


BOWERY_URL = "https://www.bowerypresents.com/venues/patchogue-theatre"
CLIENT_ID = "34780"


def _club() -> Club:
    club = Club(
        id=2577,
        name="Patchogue Theatre for the Performing Arts",
        address="71 E Main St, Patchogue, NY 11772",
        website="https://www.patchoguetheatre.org",
        popularity=0,
        zip_code="11772",
        phone_number="",
        visible=True,
        timezone="America/New_York",
        city="Patchogue",
        state="NY",
    )
    club.active_scraping_source = ScrapingSource(
        id=9001,
        club_id=club.id,
        platform="ovationtix",
        scraper_key="patchogue_theatre",
        source_url=BOWERY_URL,
        ovationtix_id=CLIENT_ID,
        priority=0,
        enabled=True,
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


# --------------------------------------------------------------------------
# extract_performance_ids
# --------------------------------------------------------------------------

def test_extract_performance_ids_handles_direct_performance_links():
    html = """
    <a href="https://ci.ovationtix.com/34780/performance/11795830">Leslie Jones</a>
    <a href="https://ci.ovationtix.com/34780/performance/11805262">Ben Bankas</a>
    """
    ids = extract_performance_ids(html, client_id=CLIENT_ID)
    assert ids == ["11795830", "11805262"]


def test_extract_performance_ids_handles_production_query_form():
    html = (
        "buy=https://ci.ovationtix.com/34780/production/1272458?performanceId=11795830 "
        "alt=https://ci.ovationtix.com/34780/production/1275146?performanceId=11805262"
    )
    ids = extract_performance_ids(html, client_id=CLIENT_ID)
    assert ids == ["11795830", "11805262"]


def test_extract_performance_ids_dedupes_and_preserves_order():
    html = (
        '<a href="https://ci.ovationtix.com/34780/performance/11795830">A</a>'
        '<a href="https://ci.ovationtix.com/34780/performance/11805262">B</a>'
        '<a href="https://ci.ovationtix.com/34780/performance/11795830">A again</a>'
    )
    ids = extract_performance_ids(html, client_id=CLIENT_ID)
    assert ids == ["11795830", "11805262"]


def test_extract_performance_ids_rejects_foreign_client_ids():
    """Bowery may surface unrelated venues on adjacent panels — the extractor
    must only emit links belonging to the configured client."""
    html = (
        '<a href="https://ci.ovationtix.com/34780/performance/11795830">Patchogue</a>'
        '<a href="https://ci.ovationtix.com/99999/performance/22222222">Other venue</a>'
    )
    ids = extract_performance_ids(html, client_id=CLIENT_ID)
    assert ids == ["11795830"]


def test_extract_performance_ids_returns_empty_for_unrelated_html():
    assert extract_performance_ids("<html><body>No tickets here</body></html>", CLIENT_ID) == []


# --------------------------------------------------------------------------
# is_comedy_relevant
# --------------------------------------------------------------------------

LESLIE_JONES_DESC = (
    "<p>Leslie Jones is a three-time Primetime Emmy nominee as well as a writer's "
    "Guild Award and NAACP Award nominee. She is best known for her work on "
    "SATURDAY NIGHT LIVE as a writer and cast member. As a stand-up comedian "
    "she headlines arenas across the country.</p>"
)
LITTLE_SHOP_DESC = (
    "<p>Little Shop of Horrors is a black comedy musical about a meek floral "
    "assistant and a man-eating plant. Music by Alan Menken.</p>"
)


@pytest.mark.parametrize(
    "name,desc,expected",
    [
        ("Leslie Jones: I'm Hot Tour", LESLIE_JONES_DESC, True),
        ("Ben Bankas", "An evening of stand-up with comedian Ben Bankas.", True),
        ("Amy Grant: The Me That Remains Tour", "Christian music legend on tour.", False),
        ("Little Shop of Horrors", LITTLE_SHOP_DESC, False),
        ("Blue Öyster Cult", "Rock band on tour.", False),
        # name-only signal still passes
        ("An Evening of Stand-Up", None, True),
        # blank input
        (None, None, False),
        ("", "", False),
    ],
)
def test_is_comedy_relevant(monkeypatch, name, desc, expected):
    monkeypatch.setattr(
        "laughtrack.scrapers.implementations.api.patchogue_theatre.extractor._get_known_comedian_names",
        lambda: (),
    )

    assert is_comedy_relevant(name, desc) is expected


def test_is_comedy_relevant_matches_known_comedian_name(monkeypatch):
    monkeypatch.setattr(
        "laughtrack.scrapers.implementations.api.patchogue_theatre.extractor._get_known_comedian_names",
        lambda: ("Trevor Noah",),
    )

    assert is_comedy_relevant("Trevor Noah Live in Patchogue", "One night only.") is True


def test_is_comedy_relevant_does_not_match_unrelated_known_comedian(monkeypatch):
    monkeypatch.setattr(
        "laughtrack.scrapers.implementations.api.patchogue_theatre.extractor._get_known_comedian_names",
        lambda: ("Trevor Noah",),
    )

    assert is_comedy_relevant("Amy Grant: The Me That Remains Tour", "Christian music legend.") is False
    assert is_comedy_relevant("Little Shop of Horrors", LITTLE_SHOP_DESC) is False


# --------------------------------------------------------------------------
# event_from_performance_response
# --------------------------------------------------------------------------

def _performance_payload() -> Dict:
    return {
        "clientId": 34780,
        "id": 11795830,
        "startDate": "2026-10-08 20:00",
        "ticketsAvailable": True,
        "availableToPurchaseOnWeb": True,
        "production": {
            "id": 1272458,
            "clientId": 34780,
            "productionName": "Leslie Jones: I'm Hot Tour",
            "description": LESLIE_JONES_DESC,
        },
        "sections": [
            {
                "ticketGroupName": "Orchestra",
                "ticketTypeViews": [
                    {"name": "Adult", "price": 89.50},
                    {"name": "VIP", "price": 199.00},
                ],
            },
        ],
    }


def test_event_from_performance_response_builds_full_event():
    event = event_from_performance_response(_performance_payload(), client_id=CLIENT_ID)
    assert isinstance(event, OvationTixEvent)
    assert event.production_id == "1272458"
    assert event.performance_id == "11795830"
    assert event.production_name == "Leslie Jones: I'm Hot Tour"
    assert event.start_date == "2026-10-08 20:00"
    assert event.tickets_available is True
    assert event.event_url == (
        "https://ci.ovationtix.com/34780/production/1272458?performanceId=11795830"
    )
    assert event.description == LESLIE_JONES_DESC
    assert len(event.sections) == 1
    assert event.sections[0]["ticketTypeViews"][0]["price"] == 89.50


def test_event_from_performance_response_marks_sold_out_when_not_purchasable():
    payload = _performance_payload()
    payload["availableToPurchaseOnWeb"] = False
    event = event_from_performance_response(payload, client_id=CLIENT_ID)
    assert event is not None
    assert event.tickets_available is False


def test_event_from_performance_response_returns_none_when_required_fields_missing():
    payload = _performance_payload()
    payload["production"] = {}  # no production id
    assert event_from_performance_response(payload, client_id=CLIENT_ID) is None

    payload = _performance_payload()
    payload["startDate"] = None
    assert event_from_performance_response(payload, client_id=CLIENT_ID) is None


def test_event_to_show_emits_two_tickets_with_section_names():
    event = event_from_performance_response(_performance_payload(), client_id=CLIENT_ID)
    show = event.to_show(_club(), enhanced=False)
    assert show is not None
    assert show.name == "Leslie Jones: I'm Hot Tour"
    assert len(show.tickets) == 2
    assert show.tickets[0].type == "Orchestra - Adult"
    assert show.tickets[0].price == 89.50
    assert show.tickets[1].type == "Orchestra - VIP"


# --------------------------------------------------------------------------
# Scraper end-to-end via monkeypatched fetch + session
# --------------------------------------------------------------------------

class _FakeResponse:
    def __init__(self, payload: Dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _FakeSession:
    def __init__(self, payloads_by_perf: Dict[str, Dict]):
        self._payloads = payloads_by_perf
        self.calls = []

    async def get(self, url, headers=None):
        self.calls.append(url)
        for perf_id, payload in self._payloads.items():
            if f"Performance({perf_id})" in url:
                return _FakeResponse(payload)
        return _FakeResponse({}, status_code=404)


@pytest.mark.asyncio
async def test_scraper_returns_only_comedy_events_for_known_perf_set(monkeypatch):
    bowery_html = (
        '<a href="https://ci.ovationtix.com/34780/performance/11795830">Leslie Jones</a>'
        '<a href="https://ci.ovationtix.com/34780/performance/11805262">Ben Bankas</a>'
        '<a href="https://ci.ovationtix.com/34780/performance/11796941">Amy Grant</a>'
        '<a href="https://ci.ovationtix.com/34780/performance/11810284">Little Shop</a>'
    )
    payloads = {
        "11795830": _performance_payload(),  # Leslie Jones — comedy
        "11805262": {
            "id": 11805262,
            "startDate": "2026-09-26 20:00",
            "ticketsAvailable": True,
            "availableToPurchaseOnWeb": True,
            "production": {
                "id": 1275146,
                "productionName": "Ben Bankas",
                "description": "Stand-up comedian Ben Bankas live in Patchogue.",
            },
            "sections": [],
        },
        "11796941": {  # Amy Grant — music, must be filtered out
            "id": 11796941,
            "startDate": "2026-06-21 19:00",
            "ticketsAvailable": True,
            "availableToPurchaseOnWeb": True,
            "production": {
                "id": 1272686,
                "productionName": "Amy Grant: The Me That Remains Tour",
                "description": "Christian music legend on tour.",
            },
            "sections": [],
        },
        "11810284": {  # Little Shop — has "comedy" but no stand-up vocabulary
            "id": 11810284,
            "startDate": "2026-08-30 19:00",
            "ticketsAvailable": True,
            "availableToPurchaseOnWeb": True,
            "production": {
                "id": 1276199,
                "productionName": "Little Shop of Horrors",
                "description": LITTLE_SHOP_DESC,
            },
            "sections": [],
        },
    }

    async def fake_fetch_html(self, url, headers=None):
        assert url == BOWERY_URL
        return bowery_html

    fake_session = _FakeSession(payloads)

    async def fake_get_session(self):
        return fake_session

    monkeypatch.setattr(PatchogueTheatreScraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(PatchogueTheatreScraper, "get_session", fake_get_session)

    scraper = PatchogueTheatreScraper(_club())
    page = await scraper.get_data(BOWERY_URL)

    assert page is not None
    names = sorted(e.production_name for e in page.event_list)
    assert names == ["Ben Bankas", "Leslie Jones: I'm Hot Tour"]
    # Sanity: every performance was probed so the filter runs after the fetch
    assert len(fake_session.calls) == 4


@pytest.mark.asyncio
async def test_scraper_returns_none_when_bowery_has_no_links(monkeypatch):
    async def fake_fetch_html(self, url, headers=None):
        return "<html>no events listed</html>"

    monkeypatch.setattr(PatchogueTheatreScraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(
        PatchogueTheatreScraper,
        "get_session",
        lambda self: (_ for _ in ()).throw(AssertionError("should not fetch API")),
    )

    scraper = PatchogueTheatreScraper(_club())
    assert await scraper.get_data(BOWERY_URL) is None


def test_scraper_raises_without_required_source_config():
    club = _club()
    club.active_scraping_source = ScrapingSource(
        id=9001,
        club_id=club.id,
        platform="ovationtix",
        scraper_key="patchogue_theatre",
        source_url=BOWERY_URL,
        ovationtix_id=None,  # missing client id
    )
    club.scraping_sources = [club.active_scraping_source]
    with pytest.raises(ValueError, match="ovationtix_id"):
        PatchogueTheatreScraper(club)


@pytest.mark.asyncio
async def test_discover_urls_raises_when_source_url_is_empty():
    club = _club()
    club.active_scraping_source = ScrapingSource(
        id=9001,
        club_id=club.id,
        platform="ovationtix",
        scraper_key="patchogue_theatre",
        source_url="",
        ovationtix_id=CLIENT_ID,
    )
    club.scraping_sources = [club.active_scraping_source]
    scraper = PatchogueTheatreScraper(club)
    with pytest.raises(ValueError, match="source_url"):
        await scraper.discover_urls()
