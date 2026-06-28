"""Tests for the WellAttended (Next.js RSC) platform scraper."""

import json

from laughtrack.app.scraper_resolver import ScraperResolver
from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.wellattended.data import WellAttendedPageData
from laughtrack.scrapers.implementations.api.wellattended.extractor import (
    WellAttendedExtractor,
)
from laughtrack.scrapers.implementations.api.wellattended.scraper import WellAttendedScraper

_ROOT = "https://theatreofdreams.wellattended.com/"
_ORIGIN = "https://theatreofdreams.wellattended.com"

# Far-future occurrences (convention #11) — UTC instants ~7:30 PM America/Denver.
_FUTURE_A = "2099-08-08T01:30:00.000Z"
_FUTURE_B = "2099-08-09T01:30:00.000Z"
_PAST = "2020-01-01T01:30:00.000Z"


def _push(inner: str) -> str:
    """Wrap raw RSC chunk text into a self.__next_f.push([1,"..."]) call."""
    return f"self.__next_f.push([1,{json.dumps(inner)}])"


def _occ(
    oid: str,
    title: str,
    start_iso: str,
    *,
    deleted: bool = False,
    shown: bool = True,
    nested: bool = False,
) -> str:
    """One occurrence object as RSC-flight JSON text.

    ``nested=True`` inserts an empty ``"meta":{}`` BEFORE ``thingTitle`` to
    exercise the enclosing-object finder (a naive rfind('{') lands on the nested
    ``{}`` and extracts nothing — the live Chipper Lowell page had this shape).
    """
    head = '{"_id":"%s",' % oid
    if nested:
        head += '"meta":{},'
    return (
        head
        + '"thingId":"T1","thingTitle":"%s","start":"$D%s",'
        % (title, start_iso)
        + '"timezone":"America/Denver","soldCount":0,"remainingCapacity":80,'
        + '"shouldBeShown":%s,"deleted":%s,"slug":"%s"}'
        % ("true" if shown else "false", "true" if deleted else "false", oid)
    )


def _tier(classification: str, price_cents: int) -> str:
    return '{"classification":"%s","price":%d,"thingId":"T1"}' % (classification, price_cents)


def _detail_html(occ_objects: list, tiers: list | None = None) -> str:
    # `tiers if tiers is not None` — an empty list must stay empty (a `tiers or
    # [...]` default would resurrect the defaults for the no-price test).
    tiers = tiers if tiers is not None else [_tier("General Admission", 2500), _tier("VIP", 5000)]
    occ_chunk = '0:["$","div",null,{"occurrences":[' + ",".join(occ_objects) + "]}]"
    tier_chunk = '1:["$","div",null,{"tiers":[' + ",".join(tiers) + "]}]"
    return (
        "<html><body>"
        f"<script>{_push(occ_chunk)}</script>"
        f"<script>{_push(tier_chunk)}</script>"
        "</body></html>"
    )


_LISTING_HTML = """
<html><body>
  <a href="/events/david-deeble-comedy-juggler-magician">David</a>
  <a href="/events/chipper-lowell-comedy-magic-collide">Chipper</a>
  <a href="/events/david-deeble-comedy-juggler-magician">David again (dupe)</a>
  <a href="/about">not an event</a>
</body></html>
"""


def _club(timezone: str = "America/Denver") -> Club:
    club = Club(
        id=999,
        name="Theatre of Dreams",
        address="735 Park St",
        website="https://www.amazingshows.com/",
        popularity=0,
        zip_code="80109",
        phone_number="",
        visible=True,
        timezone=timezone,
        city="Castle Rock",
        state="CO",
    )
    club.active_scraping_source = ScrapingSource(
        id=1, club_id=club.id, platform="custom", scraper_key="wellattended", source_url=_ROOT
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


# ---- registry / slugs ----------------------------------------------------

def test_registry_resolves_wellattended_key():
    assert ScraperResolver().get("wellattended") is WellAttendedScraper


def test_extract_event_slugs_unique_in_order():
    slugs = WellAttendedExtractor.extract_event_slugs(_LISTING_HTML)
    assert slugs == [
        "david-deeble-comedy-juggler-magician",
        "chipper-lowell-comedy-magic-collide",
    ]


def test_extract_event_slugs_empty():
    assert WellAttendedExtractor.extract_event_slugs("") == []
    assert WellAttendedExtractor.extract_event_slugs("<a href='/about'>x</a>") == []


# ---- occurrence extraction ----------------------------------------------

def test_extract_occurrences_two_future_nights_with_price():
    html = _detail_html([
        _occ("o1", "David Future", _FUTURE_A),
        _occ("o2", "David Future", _FUTURE_B),
    ])
    events = WellAttendedExtractor.extract_event_occurrences(html, _ORIGIN, "david")
    assert [e.start_time_utc for e in events] == [_FUTURE_A, _FUTURE_B]
    assert all(e.title == "David Future" for e in events)
    assert all(e.timezone == "America/Denver" for e in events)
    assert all(e.show_page_url == f"{_ORIGIN}/events/david" for e in events)
    assert all(e.price == 25.0 for e in events)  # min tier 2500 cents


def test_extract_occurrences_handles_nested_object_before_key():
    """Enclosing-object finder: an occurrence with a nested {} before thingTitle."""
    html = _detail_html([_occ("o1", "Nested Show", _FUTURE_A, nested=True)])
    events = WellAttendedExtractor.extract_event_occurrences(html, _ORIGIN, "x")
    assert len(events) == 1
    assert events[0].title == "Nested Show"
    assert events[0].start_time_utc == _FUTURE_A


def test_extract_occurrences_drops_past_deleted_hidden_and_dedupes():
    html = _detail_html([
        _occ("future", "Keep", _FUTURE_A),
        _occ("future", "Keep", _FUTURE_A),          # exact dupe (_id+start)
        _occ("past", "Old", _PAST),                  # past
        _occ("del", "Deleted", _FUTURE_B, deleted=True),
        _occ("hidden", "Hidden", _FUTURE_B, shown=False),
    ])
    events = WellAttendedExtractor.extract_event_occurrences(html, _ORIGIN, "x")
    assert len(events) == 1
    assert events[0].title == "Keep"


def test_extract_occurrences_empty_flight():
    assert WellAttendedExtractor.extract_event_occurrences("<html></html>", _ORIGIN, "x") == []


def test_extract_occurrences_no_tier_price_is_none():
    html = _detail_html([_occ("o1", "No Price", _FUTURE_A)], tiers=[])
    events = WellAttendedExtractor.extract_event_occurrences(html, _ORIGIN, "x")
    assert events[0].price is None


# ---- to_show -------------------------------------------------------------

def test_to_show_localizes_utc_to_club_tz():
    import pytz

    html = _detail_html([_occ("o1", "Show", _FUTURE_A)])
    event = WellAttendedExtractor.extract_event_occurrences(html, _ORIGIN, "slug")[0]
    show = event.to_show(_club())
    assert show is not None
    assert show.name == "Show"
    # Localized to America/Denver and tz-aware; assert the preserved UTC instant
    # rather than the local wall-clock hour (pytz's far-future DST table makes the
    # 2099 MDT-vs-MST wall clock fragile, but the instant is exact either way).
    assert show.date.tzinfo is not None
    assert show.date.astimezone(pytz.utc) == pytz.utc.localize(
        __import__("datetime").datetime(2099, 8, 8, 1, 30)
    )
    assert show.tickets and show.tickets[0].purchase_url == f"{_ORIGIN}/events/slug"
    assert show.tickets[0].price == 25.0


# ---- get_data (fetch_html mocked) ----------------------------------------

def _fetch_map(mapping: dict):
    async def _fetch(url: str):
        return mapping.get(url, "")
    return _fetch


async def test_get_data_end_to_end(monkeypatch):
    scraper = WellAttendedScraper(_club())
    detail = _detail_html([_occ("o1", "David Future", _FUTURE_A), _occ("o2", "David Future", _FUTURE_B)])
    listing = '<a href="/events/david">x</a>'
    monkeypatch.setattr(
        scraper, "fetch_html",
        _fetch_map({_ROOT: listing, f"{_ORIGIN}/events/david": detail}),
    )
    page = await scraper.get_data(_ROOT)
    assert isinstance(page, WellAttendedPageData)
    assert len(page.event_list) == 2


async def test_get_data_none_on_empty_listing(monkeypatch):
    scraper = WellAttendedScraper(_club())
    monkeypatch.setattr(scraper, "fetch_html", _fetch_map({_ROOT: ""}))
    assert await scraper.get_data(_ROOT) is None


async def test_get_data_none_when_no_slugs(monkeypatch):
    scraper = WellAttendedScraper(_club())
    monkeypatch.setattr(scraper, "fetch_html", _fetch_map({_ROOT: "<a href='/about'>x</a>"}))
    assert await scraper.get_data(_ROOT) is None


async def test_get_data_none_when_no_upcoming_occurrences(monkeypatch):
    scraper = WellAttendedScraper(_club())
    detail = _detail_html([_occ("past", "Old", _PAST)])
    monkeypatch.setattr(
        scraper, "fetch_html",
        _fetch_map({_ROOT: '<a href="/events/x">x</a>', f"{_ORIGIN}/events/x": detail}),
    )
    assert await scraper.get_data(_ROOT) is None
