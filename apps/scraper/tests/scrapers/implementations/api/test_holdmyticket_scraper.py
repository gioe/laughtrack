"""Tests for the HoldMyTicket whitelabel-site scraper."""

from laughtrack.app.scraper_resolver import ScraperResolver
from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.holdmyticket.data import (
    HoldMyTicketPageData,
)
from laughtrack.scrapers.implementations.api.holdmyticket.extractor import (
    HoldMyTicketExtractor,
)
from laughtrack.scrapers.implementations.api.holdmyticket.scraper import (
    HoldMyTicketScraper,
)

_HOST = "quezadas.holdmyticket.com"
_SOURCE_URL = f"https://{_HOST}/"
_API_BASE = "https://holdmyticket.com/api"

# Far-future wall-clock starts (convention #11: avoid test time-bombs).
_FUTURE_START = "2099-07-10 19:00:00"
_FUTURE_START_2 = "2099-07-11 19:00:00"
_FUTURE_START_3 = "2099-07-11 21:30:00"
_PAST_START = "2020-01-01 19:00:00"
_CANCEL_SENTINEL = "0000-00-00 00:00:00"


def _event(event_id: int = 461788, title: str = "Cipha Sounds", start: str = _FUTURE_START,
           repeating: int = 0, **overrides) -> dict:
    row = {
        "id": str(event_id),
        "title": title,
        "start": start,
        "cancel": _CANCEL_SENTINEL,
        "postponed": "n",
        "venue_id": "8819",
        "ticket_url": f"https://tickets.holdmyticket.com/tickets/{event_id}?tc=hmt",
        "repeating_future_events": repeating,
    }
    row.update(overrides)
    return row


def _payload(events: list) -> dict:
    return {"events": events, "status": "ok", "request_number": 1}


def _club(timezone_name: str = "America/Denver", source_url: str = _SOURCE_URL,
          metadata: dict | None = None) -> Club:
    club = Club(
        id=999,
        name="Quezada's Comedy Club & Cantina",
        address="54 Jemez Canyon Dam Rd",
        website=_SOURCE_URL,
        popularity=0,
        zip_code="87004",
        phone_number="",
        visible=True,
        timezone=timezone_name,
        city="Santa Ana Pueblo",
        state="NM",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="custom",
        scraper_key="holdmyticket",
        source_url=source_url,
        metadata=metadata or {},
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _feed_router(pages: dict[int, dict], repeating: dict[int, dict] | None = None):
    """Build a fake fetch_json routing feed pages and repeating expansions."""
    repeating = repeating or {}

    async def fake_fetch_json(url, **kwargs):
        for page, payload in pages.items():
            if url == f"{_API_BASE}/public/events/nearby/api_key/anon/page/{page}/whitelabel/{_HOST}":
                return payload
        for event_id, payload in repeating.items():
            if url == f"{_API_BASE}/public/events/repeating/id/{event_id}/whitelabel/{_HOST}":
                return payload
        return _payload([])

    return fake_fetch_json


# ---- registry / targets --------------------------------------------------

def test_registry_resolves_holdmyticket_key():
    assert ScraperResolver().get("holdmyticket") is HoldMyTicketScraper


async def test_collect_targets_returns_source_url():
    scraper = HoldMyTicketScraper(_club())
    assert await scraper.collect_scraping_targets() == [_SOURCE_URL]


async def test_collect_targets_empty_on_invalid_source_url():
    scraper = HoldMyTicketScraper(_club(source_url="not-a-url"))
    assert await scraper.collect_scraping_targets() == []


# ---- extractor -----------------------------------------------------------

def test_extract_raw_events_validates_entries():
    payload = _payload([
        _event(event_id=1, title="Good"),
        {"id": None, "title": "No Id", "start": _FUTURE_START},
        {"id": "abc", "title": "Non-numeric Id", "start": _FUTURE_START},
        _event(event_id=2, title="  "),
        _event(event_id=3, start=""),
        _event(event_id=4, cancel="2026-07-01 12:00:00"),
        _event(event_id=5, postponed="y"),
    ])
    raw = HoldMyTicketExtractor.extract_raw_events(payload)
    assert [r["id"] for r in raw] == ["1"]


def test_extract_raw_events_accepts_expansion_entries_without_flags():
    """Repeating-expansion entries lack cancel/postponed/venue fields."""
    payload = _payload([
        {"id": "461789", "title": "Cipha Sounds", "start": _FUTURE_START_2,
         "ticket_url": "https://tickets.holdmyticket.com/tickets/461789?tc=hmt"},
    ])
    raw = HoldMyTicketExtractor.extract_raw_events(payload)
    assert [r["id"] for r in raw] == ["461789"]


def test_extract_raw_events_non_dict_payload_returns_empty():
    assert HoldMyTicketExtractor.extract_raw_events([]) == []
    assert HoldMyTicketExtractor.extract_raw_events({"events": "nope"}) == []


def test_to_events_drops_past_and_malformed_starts():
    raw = HoldMyTicketExtractor.extract_raw_events(_payload([
        _event(event_id=1, start=_FUTURE_START),
        _event(event_id=2, start=_PAST_START),
        _event(event_id=3, start="July 10th 2099"),
    ]))
    events = HoldMyTicketExtractor.to_events(raw, "America/Denver")
    assert [e.event_id for e in events] == [1]


def test_to_events_falls_back_to_canonical_ticket_url():
    raw = HoldMyTicketExtractor.extract_raw_events(_payload([
        _event(event_id=7, ticket_url=""),
    ]))
    events = HoldMyTicketExtractor.to_events(raw, "America/Denver")
    assert events[0].ticket_url == "https://tickets.holdmyticket.com/tickets/7"


# ---- event.to_show -------------------------------------------------------

def test_event_to_show_uses_venue_wall_clock_in_club_tz():
    raw = HoldMyTicketExtractor.extract_raw_events(_payload([_event()]))
    events = HoldMyTicketExtractor.to_events(raw, "America/Denver")
    show = events[0].to_show(_club())
    assert show is not None
    assert show.name == "Cipha Sounds"
    assert show.date.tzinfo is not None
    # Wall-clock start is kept as-is in the club timezone.
    assert (show.date.year, show.date.hour, show.date.minute) == (2099, 19, 0)
    assert len(show.tickets) == 1
    assert show.tickets[0].purchase_url == (
        "https://tickets.holdmyticket.com/tickets/461788?tc=hmt"
    )


# ---- get_data (fetch_json mocked) ----------------------------------------

async def test_get_data_expands_repeating_series_and_dedups(monkeypatch):
    """A head with 2 repeats expands via the repeating endpoint; the head's own
    entry in the expansion (and a sibling head also present in the feed) dedup
    by event id."""
    scraper = HoldMyTicketScraper(_club())
    head = _event(event_id=461788, repeating=2)
    sibling_head = _event(event_id=461787, start=_FUTURE_START_3)
    expansion = _payload([
        {"id": "461788", "title": "Cipha Sounds", "start": _FUTURE_START},
        {"id": "461789", "title": "Cipha Sounds", "start": _FUTURE_START_2},
        {"id": "461787", "title": "Cipha Sounds", "start": _FUTURE_START_3},
    ])
    monkeypatch.setattr(
        scraper, "fetch_json",
        _feed_router({0: _payload([head, sibling_head])}, {461788: expansion}),
    )
    page = await scraper.get_data(_SOURCE_URL)
    assert isinstance(page, HoldMyTicketPageData)
    assert sorted(e.event_id for e in page.event_list) == [461787, 461788, 461789]


async def test_get_data_paginates_until_empty_page(monkeypatch):
    scraper = HoldMyTicketScraper(_club())
    monkeypatch.setattr(
        scraper, "fetch_json",
        _feed_router({
            0: _payload([_event(event_id=1)]),
            1: _payload([_event(event_id=2, title="Second Page")]),
            2: _payload([]),
        }),
    )
    page = await scraper.get_data(_SOURCE_URL)
    assert sorted(e.event_id for e in page.event_list) == [1, 2]


async def test_get_data_metadata_venue_filter_drops_other_venues(monkeypatch):
    scraper = HoldMyTicketScraper(_club(metadata={"holdmyticket_venue_id": "8819"}))
    monkeypatch.setattr(
        scraper, "fetch_json",
        _feed_router({0: _payload([
            _event(event_id=1),
            _event(event_id=2, venue_id="1234"),
        ])}),
    )
    page = await scraper.get_data(_SOURCE_URL)
    assert [e.event_id for e in page.event_list] == [1]


async def test_get_data_empty_feed_returns_none(monkeypatch):
    scraper = HoldMyTicketScraper(_club())
    monkeypatch.setattr(scraper, "fetch_json", _feed_router({0: _payload([])}))
    assert await scraper.get_data(_SOURCE_URL) is None


async def test_get_data_survives_repeating_fetch_failure(monkeypatch):
    """A failed expansion keeps the head showtime instead of dropping the run."""
    scraper = HoldMyTicketScraper(_club())
    head = _event(event_id=461788, repeating=2)

    async def fake_fetch_json(url, **kwargs):
        if "/public/events/nearby/" in url:
            page = int(url.split("/page/")[1].split("/")[0])
            return _payload([head]) if page == 0 else _payload([])
        raise RuntimeError("boom")

    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)
    page = await scraper.get_data(_SOURCE_URL)
    assert [e.event_id for e in page.event_list] == [461788]
