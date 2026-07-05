"""Tests for the Patchogue Theatre (Bowery → OvationTix Performance) scraper."""

from __future__ import annotations

from typing import Dict

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.ovationtix import OvationTixEvent
from laughtrack.scrapers.implementations.api.patchogue_theatre.extractor import (
    event_from_performance_response,
    extract_aeg_feed_urls,
    extract_performance_ids,
    is_comedy_relevant,
    performance_ids_from_aeg_feed,
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
        "startDate": "2099-10-08 20:00",
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
    assert event.start_date == "2099-10-08 20:00"
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
    def __init__(self, payloads_by_perf: Dict[str, Dict], feeds_by_url: Dict[str, Dict] = None):
        self._payloads = payloads_by_perf
        self._feeds = feeds_by_url or {}
        self.calls = []

    async def get(self, url, headers=None):
        self.calls.append(url)
        if url in self._feeds:
            return _FakeResponse(self._feeds[url])
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
            "startDate": "2099-09-26 20:00",
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
            "startDate": "2099-08-30 19:00",
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
async def test_scraper_returns_none_when_page_has_no_feeds_or_links(monkeypatch):
    """A page with neither an AEG feed reference nor a legacy inline OvationTix
    link yields no performances — and no OvationTix Performance() call is made."""
    async def fake_fetch_html(self, url, headers=None):
        return "<html>no events listed</html>"

    fake_session = _FakeSession({})

    async def fake_get_session(self):
        return fake_session

    monkeypatch.setattr(PatchogueTheatreScraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(PatchogueTheatreScraper, "get_session", fake_get_session)

    scraper = PatchogueTheatreScraper(_club())
    assert await scraper.get_data(BOWERY_URL) is None
    # No AEG feed URL and no inline link → nothing to fetch.
    assert fake_session.calls == []


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


# --------------------------------------------------------------------------
# AEG feed discovery (Bowery migrated off inline OvationTix links in 2026)
# --------------------------------------------------------------------------

AEG_FEED_URL = (
    "https://aegwebprod.blob.core.windows.net/json/resources/8/events/"
    "7301mbln09/events.json"
)


def test_extract_aeg_feed_urls_dedupes_and_preserves_order():
    html = (
        f'<script>var a="{AEG_FEED_URL}";</script>'
        '<link href="https://aegwebprod.blob.core.windows.net/json/resources/8/'
        'events/208lbnmkq5/events.json">'
        f'<img data-src="{AEG_FEED_URL}">'  # duplicate of the first
    )
    urls = extract_aeg_feed_urls(html)
    assert urls == [
        AEG_FEED_URL,
        "https://aegwebprod.blob.core.windows.net/json/resources/8/events/"
        "208lbnmkq5/events.json",
    ]


def test_extract_aeg_feed_urls_returns_empty_when_absent():
    assert extract_aeg_feed_urls("<html><body>no feed here</body></html>") == []


def _aeg_event(headliner: str, perf_id: str, client_id: str = CLIENT_ID) -> Dict:
    return {
        "eventId": perf_id,
        "title": {"headlinersText": headliner, "eventTitleText": headliner},
        "eventDateTimeISO": "2099-09-26T20:00:00-04:00",
        "ticketing": {
            "ticketURL": f"https://ci.ovationtix.com/{client_id}/performance/{perf_id}",
            "url": f"https://ci.ovationtix.com/{client_id}/performance/{perf_id}",
            "eventUrl": "https://www.axs.com/events/123/tickets",
        },
        "venue": {"venueId": "124771", "title": "Patchogue Theatre"},
    }


def test_performance_ids_from_aeg_feed_filters_by_client_and_dedupes():
    feed = {
        "events": [
            _aeg_event("Ben Bankas", "11805262"),
            _aeg_event("Leslie Jones", "11795830"),
            _aeg_event("Some Other Venue Act", "22222222", client_id="99999"),
            _aeg_event("Ben Bankas again", "11805262"),  # duplicate perf id
        ]
    }
    assert performance_ids_from_aeg_feed(feed, CLIENT_ID) == ["11805262", "11795830"]


def test_performance_ids_from_aeg_feed_handles_url_fallback_and_bad_shapes():
    feed = {
        "events": [
            {"ticketing": {"url": "https://ci.ovationtix.com/34780/performance/777"}},
            {"ticketing": {}},  # no link
            {"no_ticketing": True},  # missing key
            "not-a-dict",  # junk
        ]
    }
    assert performance_ids_from_aeg_feed(feed, CLIENT_ID) == ["777"]
    assert performance_ids_from_aeg_feed({}, CLIENT_ID) == []
    assert performance_ids_from_aeg_feed({"events": "nope"}, CLIENT_ID) == []


@pytest.mark.asyncio
async def test_scraper_discovers_via_aeg_feed_and_filters_comedy(monkeypatch):
    """The Bowery page now references an AEG feed instead of inline links; the
    scraper must read perf IDs from the feed, then comedy-filter on the
    per-performance OvationTix payloads (whose descriptions remain rich)."""
    bowery_html = f'<html><body><script>feed="{AEG_FEED_URL}"</script></body></html>'

    feed = {
        "events": [
            _aeg_event("Leslie Jones", "11795830"),
            _aeg_event("Ben Bankas", "11805262"),
            _aeg_event("Amy Grant", "11796941"),
            _aeg_event("Little Shop of Horrors", "11810284"),
        ]
    }
    payloads = {
        "11795830": _performance_payload(),  # Leslie Jones — comedy
        "11805262": {
            "id": 11805262,
            "startDate": "2099-09-26 20:00",
            "ticketsAvailable": True,
            "availableToPurchaseOnWeb": True,
            "production": {
                "id": 1275146,
                "productionName": "Ben Bankas",
                "description": "Stand-up comedian Ben Bankas live in Patchogue.",
            },
            "sections": [],
        },
        "11796941": {  # Amy Grant — music, filtered out
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
        "11810284": {  # Little Shop — "comedy" but no stand-up vocabulary
            "id": 11810284,
            "startDate": "2099-08-30 19:00",
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

    fake_session = _FakeSession(payloads, feeds_by_url={AEG_FEED_URL: feed})

    async def fake_get_session(self):
        return fake_session

    monkeypatch.setattr(PatchogueTheatreScraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(PatchogueTheatreScraper, "get_session", fake_get_session)
    # Force keyword-only comedy detection so the test does not depend on the DB
    # comedian list.
    monkeypatch.setattr(
        "laughtrack.scrapers.implementations.api.patchogue_theatre.extractor._get_known_comedian_names",
        lambda: (),
    )

    scraper = PatchogueTheatreScraper(_club())
    page = await scraper.get_data(BOWERY_URL)

    assert page is not None
    names = sorted(e.production_name for e in page.event_list)
    assert names == ["Ben Bankas", "Leslie Jones: I'm Hot Tour"]
    # The AEG feed was fetched, then each discovered performance was probed.
    assert AEG_FEED_URL in fake_session.calls
    assert sum("Performance(" in c for c in fake_session.calls) == 4


@pytest.mark.asyncio
async def test_scraper_falls_back_to_inline_links_when_no_aeg_feed(monkeypatch):
    """If a Bowery page carries no AEG feed reference but still has legacy inline
    ci.ovationtix.com links, discovery must fall back to the inline-link scrape
    and probe those performances — no AEG feed fetch occurs."""
    bowery_html = (
        '<html><body>'
        '<a href="https://ci.ovationtix.com/34780/performance/11795830">Leslie Jones</a>'
        '</body></html>'
    )
    payloads = {"11795830": _performance_payload()}

    async def fake_fetch_html(self, url, headers=None):
        return bowery_html

    fake_session = _FakeSession(payloads)  # no feeds registered

    async def fake_get_session(self):
        return fake_session

    monkeypatch.setattr(PatchogueTheatreScraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(PatchogueTheatreScraper, "get_session", fake_get_session)

    scraper = PatchogueTheatreScraper(_club())
    page = await scraper.get_data(BOWERY_URL)

    assert page is not None
    assert [e.production_name for e in page.event_list] == ["Leslie Jones: I'm Hot Tour"]
    # Fallback path: no AEG blob was fetched, only the OvationTix performance.
    assert not any("aegwebprod" in c for c in fake_session.calls)
    assert any("Performance(11795830)" in c for c in fake_session.calls)
