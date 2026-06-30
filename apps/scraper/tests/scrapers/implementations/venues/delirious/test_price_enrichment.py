"""
Price-enrichment tests for the Delirious Comedy Club (FriendlySky) scraper.

Covers the extractor parse helpers (extract_package_hash / extract_min_price)
and the scraper's _enrich_prices 2-call chain (pkgs → firstPage) wired through
get_data, including graceful degradation to a price-less ticket on failure.
"""

import pytest

from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.implementations.venues.delirious.extractor import (
    DeliriousExtractor,
)
from laughtrack.scrapers.implementations.venues.delirious.scraper import (
    DeliriousComedyClubScraper,
)

API_URL = (
    "https://tickets.deliriouscomedyclub.com"
    "/rest/events/$EKR?_branch=findByDomainNameOrHashId&_s=1"
)


def _club() -> Club:
    return Club(
        id=407,
        name="Delirious Comedy Club",
        address="450 Fremont St, Las Vegas, NV 89101",
        website="https://deliriouscomedyclub.com",
        popularity=0,
        zip_code="89101",
        phone_number="",
        visible=True,
        timezone="America/Los_Angeles",
    )


def _games_envelope() -> dict:
    return {
        "data": {
            "games": [
                {
                    "hashId": "GAME1",
                    "name": "Comedian One, Comedian Two",
                    "begDate": "2099-07-23",
                    "begTime": "20:00",
                    "venueName": "Delirious Comedy Club",
                    "status": "Y",
                    "urlName": "delirious-comedy-club",
                    "hashEventId": "EKR",
                },
                {
                    "hashId": "GAME2",
                    "name": "Headliner Three",
                    "begDate": "2099-07-24",
                    "begTime": "20:00",
                    "venueName": "Delirious Comedy Club",
                    "status": "Y",
                    "urlName": "delirious-comedy-club",
                    "hashEventId": "EKR",
                },
            ]
        }
    }


def _pkgs_envelope(pkg_hash="PKG1") -> dict:
    return {"data": {"hashId": pkg_hash}}


def _firstpage_envelope(prices=(59.95, 39.95, 49.95)) -> dict:
    return {
        "data": {
            "targetPkgItems": [
                {"item": {"price": p, "prices": [{"pricingDetailsDto": {"totalPrice": p + 5}}]}}
                for p in prices
            ]
        }
    }


# ---------------------------------------------------------------------------
# Extractor parse-helper unit tests
# ---------------------------------------------------------------------------


def test_extract_package_hash_returns_data_hash_id():
    assert DeliriousExtractor.extract_package_hash(_pkgs_envelope("PKGABC")) == "PKGABC"


def test_extract_package_hash_none_on_missing_data():
    assert DeliriousExtractor.extract_package_hash({"data": {}}) is None
    assert DeliriousExtractor.extract_package_hash({}) is None
    assert DeliriousExtractor.extract_package_hash(None) is None
    assert DeliriousExtractor.extract_package_hash({"data": {"hashId": ""}}) is None


def test_extract_min_price_returns_min_face_price():
    assert DeliriousExtractor.extract_min_price(_firstpage_envelope((59.95, 39.95, 49.95))) == 39.95


def test_extract_min_price_handles_string_prices():
    env = {"data": {"targetPkgItems": [{"item": {"price": "49.95"}}, {"item": {"price": "39.95"}}]}}
    assert DeliriousExtractor.extract_min_price(env) == 39.95


def test_extract_min_price_skips_non_numeric_and_missing():
    env = {
        "data": {
            "targetPkgItems": [
                {"item": {"price": None}},
                {"item": {}},
                {"not_item": 1},
                {"item": {"price": "n/a"}},
                {"item": {"price": 42.0}},
            ]
        }
    }
    assert DeliriousExtractor.extract_min_price(env) == 42.0


def test_extract_min_price_none_on_empty_or_malformed():
    assert DeliriousExtractor.extract_min_price({"data": {"targetPkgItems": []}}) is None
    assert DeliriousExtractor.extract_min_price({"data": {}}) is None
    assert DeliriousExtractor.extract_min_price({}) is None
    assert DeliriousExtractor.extract_min_price(None) is None


# ---------------------------------------------------------------------------
# Scraper enrichment integration tests
# ---------------------------------------------------------------------------


def _route_fetch(monkeypatch, scraper, *, pkgs=None, firstpage=None, calls=None):
    """Patch scraper.fetch_json to route by URL across the games/pkgs/firstpage chain."""

    async def fake_fetch_json(url, **kwargs):
        if calls is not None:
            calls.append(url)
        if "/rest/events/" in url:
            return _games_envelope()
        if "/rest/pkgs" in url:
            return pkgs(url) if callable(pkgs) else (pkgs if pkgs is not None else _pkgs_envelope())
        if "/firstPage" in url:
            return firstpage(url) if callable(firstpage) else (firstpage if firstpage is not None else _firstpage_envelope())
        return None

    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)


@pytest.mark.asyncio
async def test_get_data_threads_min_price_onto_events(monkeypatch):
    scraper = DeliriousComedyClubScraper(_club())
    _route_fetch(monkeypatch, scraper)

    result = await scraper.get_data(API_URL)

    assert result is not None
    assert len(result.event_list) == 2
    assert all(e.price == 39.95 for e in result.event_list)
    # Price survives into the Show ticket.
    show = result.event_list[0].to_show(_club())
    assert show is not None
    assert show.tickets[0].price == 39.95


@pytest.mark.asyncio
async def test_get_data_runs_two_call_chain_per_event(monkeypatch):
    scraper = DeliriousComedyClubScraper(_club())
    calls = []
    _route_fetch(monkeypatch, scraper, calls=calls)

    await scraper.get_data(API_URL)

    pkgs_calls = [c for c in calls if "/rest/pkgs" in c]
    firstpage_calls = [c for c in calls if "/firstPage" in c]
    # One pkgs + one firstPage per event (2 events).
    assert len(pkgs_calls) == 2
    assert len(firstpage_calls) == 2
    # The pkgs call carries the per-event game hash.
    assert any("hashGameId=GAME1" in c for c in pkgs_calls)
    assert any("hashGameId=GAME2" in c for c in pkgs_calls)
    # The firstPage call carries the package hash recovered from pkgs.
    assert all("hashPkgId=PKG1" in c for c in firstpage_calls)


@pytest.mark.asyncio
async def test_get_data_degrades_to_none_when_pkgs_missing(monkeypatch):
    scraper = DeliriousComedyClubScraper(_club())
    _route_fetch(monkeypatch, scraper, pkgs={"data": {}})

    result = await scraper.get_data(API_URL)

    assert result is not None
    assert len(result.event_list) == 2
    assert all(e.price is None for e in result.event_list)


@pytest.mark.asyncio
async def test_get_data_degrades_to_none_on_fetch_exception(monkeypatch):
    scraper = DeliriousComedyClubScraper(_club())

    async def fake_fetch_json(url, **kwargs):
        if "/rest/events/" in url:
            return _games_envelope()
        raise RuntimeError("internal SPA endpoint blocked")

    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)

    assert result is not None
    assert len(result.event_list) == 2
    assert all(e.price is None for e in result.event_list)


@pytest.mark.asyncio
async def test_get_data_respects_concurrency_env(monkeypatch):
    monkeypatch.setenv("DELIRIOUS_PRICE_CONCURRENCY", "1")
    scraper = DeliriousComedyClubScraper(_club())
    _route_fetch(monkeypatch, scraper)

    result = await scraper.get_data(API_URL)

    assert result is not None
    assert all(e.price == 39.95 for e in result.event_list)
