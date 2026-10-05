"""Reviewed SeatEngine account occurrences route without guessing locations."""

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from laughtrack.core.clients.seatengine.client import SeatEngineClient
from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.foundation.infrastructure.http.diagnostics import ScrapeDiagnostics, bind_diagnostics, reset_diagnostics
from laughtrack.scrapers.implementations.api.seatengine.scraper import SeatEngineScraper


def venue(ident, timezone_name="America/New_York"):
    return Club(
        id=ident,
        name=f"Venue {ident}",
        address="123 Verified St",
        website="https://physical.example",
        popularity=0,
        zip_code="10001",
        phone_number="",
        visible=True,
        timezone=timezone_name,
    )


def source_club(account=618, enabled=True):
    club = venue(613)
    club.active_scraping_source = ScrapingSource(
        id=259,
        club_id=613,
        platform="seatengine",
        scraper_key="seatengine",
        seatengine_id=account,
        source_url="https://producer.example",
        enabled=enabled,
        metadata={
            "seatengine_venue_routes": {
                "account_id": str(account),
                "producer_id": 72,
                "routes": {
                    "101": {
                        "start_date_time": "2026-11-01T20:00:00-05:00",
                        "club_id": 9001,
                        "disposition": "route",
                        "reason": "Verified event address",
                    },
                    "102": {
                        "start_date_time": "2026-11-01T20:00:00-05:00",
                        "club_id": 613,
                        "disposition": "route",
                        "reason": "Verified same venue",
                    },
                },
            }
        },
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def event(ident=101, when="2026-11-01T20:00:00-05:00"):
    return {
        "id": ident,
        "start_date_time": when,
        "inventories": [{"price": 2500}],
        "event": {"name": "Verified Comedy", "description": "Performer biography", "talents": [], "labels": []},
    }


def client(club=None):
    result = SeatEngineClient(club or source_club())
    result.venue_website = "https://producer.example"
    result.routing_clubs = {9001: venue(9001, "America/Chicago"), 613: result.club}
    return result


def test_route_preserves_account_urls_price_instant_and_producer():
    show = client().create_show(event())
    assert show.club_id == 9001
    assert show.date.astimezone(timezone.utc) == datetime(2026, 11, 2, 1, tzinfo=timezone.utc)
    assert show.show_page_url == show.tickets[0].purchase_url == "https://producer.example/shows/101"
    assert show.tickets[0].price == 25
    assert show.production_company_id == show.scraped_by_organizer_id == 72


def test_verified_same_venue_stays_and_unconfigured_sources_unchanged():
    c = client()
    assert c.create_show(event(102)).club_id == 613
    c.club.active_scraping_source.metadata = {}
    show = c.create_show(event())
    assert show.club_id == 613 and show.production_company_id is None


@pytest.mark.parametrize("change", ["unknown", "time", "account", "hold", "missing_club", "malformed", "disabled"])
def test_unresolved_route_is_held_and_marks_incomplete(change):
    c = client()
    payload = event()
    config = c.club.source_metadata["seatengine_venue_routes"]
    if change == "unknown":
        payload["id"] = 999
    elif change == "time":
        payload["start_date_time"] = "2026-11-02T20:00:00-05:00"
    elif change == "account":
        config["account_id"] = "422"
    elif change == "hold":
        config["routes"]["101"] = {"disposition": "hold", "reason": "Conflicting entrance addresses"}
    elif change == "missing_club":
        c.routing_clubs = {}
    elif change == "malformed":
        c.club.source_metadata["seatengine_venue_routes"] = None
    else:
        c.club.active_scraping_source.enabled = False
    diagnostics = ScrapeDiagnostics()
    token = bind_diagnostics(diagnostics)
    try:
        assert c.create_show(payload) is None
        assert diagnostics.scrape_errors
    finally:
        reset_diagnostics(token)


@pytest.mark.parametrize("cancellation_location", ["show", "event"])
def test_naive_reviewed_time_uses_destination_timezone_and_cancellation_is_held(cancellation_location):
    c = client()
    c.club.source_metadata["seatengine_venue_routes"]["routes"]["101"]["start_date_time"] = "2026-11-01T20:00:00"
    payload = event(when="2026-11-01T20:00:00")
    show = c.create_show(payload)
    assert show.date.astimezone(timezone.utc) == datetime(2026, 11, 2, 2, tzinfo=timezone.utc)
    cancelled = payload if cancellation_location == "show" else payload["event"]
    cancelled["cancelled_at"] = "2026-10-05T12:00:00Z"
    assert c.create_show(payload) is None
    assert "cancelled" in c.routing_errors[-1]


@pytest.mark.parametrize("when", ["2026-11-01T01:30:00", "2026-03-08T02:30:00"])
def test_ambiguous_or_nonexistent_naive_wall_time_is_held(when):
    c = client()
    c.club.source_metadata["seatengine_venue_routes"]["routes"]["101"]["start_date_time"] = when
    assert c.create_show(event(when=when)) is None


def test_live_laugh_tonight_nested_cancellation_is_not_recreated():
    # Public projection of account424/show370667 captured 2026-10-05.
    # Root cancelled_at is absent; SeatEngine stores it on the parent event.
    payload = event(370667, "2026-05-31T20:00:00-04:00")
    payload["event"].update(
        id=136528,
        name="Henry Coleman @ Laugh Factory Chicago",
        cancelled_at="2026-05-27T14:47:00Z",
    )
    c = client(source_club(account=424))
    c.club.source_metadata["seatengine_venue_routes"]["routes"] = {
        "370667": {
            "start_date_time": payload["start_date_time"],
            "club_id": 168,
            "disposition": "route",
            "reason": "Verified Laugh Factory event location; historical cancellation must remain",
        }
    }
    c.routing_clubs = {168: venue(168, "America/Chicago")}
    assert "cancelled_at" not in payload
    assert c.create_show(payload) is None
    assert "cancelled" in c.routing_errors[-1]


@pytest.mark.parametrize("club_id,account", [(613, 618), (447, 422), (469, 444)])
def test_pinned_organizer_audit_routes_verified_rows_and_holds_unknowns(club_id, account):
    audit = Path(__file__).resolve().parents[5] / "docs/audits/2026-09-28-organizer-venues"
    filename = "lets-shoppe/per-show.json" if club_id == 469 else "yardbird-alameda/per-show.json"
    rows = [row for row in json.loads((audit / filename).read_text())["shows"] if row["club_id"] == club_id]
    c = client(source_club(account))
    c.club.id = club_id
    routes = c.club.source_metadata["seatengine_venue_routes"]["routes"]
    routes.clear()
    c.routing_clubs = {club_id: c.club}
    destinations = {}
    for row in rows:
        ident = row.get("platform_show_id", row.get("source_show_id"))
        if row["classification"] == "unknown":
            routes[ident] = {"disposition": "hold", "reason": row["reason"]}
            continue
        label = row.get("event_venue") or row["actual_location"]["name"]
        dest_id = (
            club_id if row["classification"] == "correct" else destinations.setdefault(label, 9001 + len(destinations))
        )
        c.routing_clubs[dest_id] = venue(dest_id)
        c.routing_clubs[dest_id].name = label
        routes[ident] = {
            "disposition": "route",
            "reason": row["reason"],
            "club_id": dest_id,
            "start_date_time": row["date"],
        }
    for row in rows:
        ident = row.get("platform_show_id", row.get("source_show_id"))
        payload = event(int(ident), row["date"])
        payload["event"]["name"] = row["name"]
        show = c.create_show(payload)
        if row["classification"] == "unknown":
            assert show is None
        else:
            assert show.club_id == routes[ident]["club_id"]
            assert show.date == datetime.fromisoformat(row["date"])
            assert show.production_company_id == show.scraped_by_organizer_id == 72


def test_partial_routing_result_prevents_reconciliation(monkeypatch):
    from laughtrack.utilities.domain.scraper.result import ScrapingResultProcessor

    scraper = SeatEngineScraper(source_club())
    scraper.seatengine_client.routing_clubs = {9001: venue(9001)}

    def scrape():
        good = scraper.seatengine_client.create_show(event())
        assert scraper.seatengine_client.create_show(event(999)) is None
        return [good]

    monkeypatch.setattr(scraper, "scrape", scrape)
    result = scraper.scrape_with_result()
    assert len(result.shows) == 1
    assert "routing incomplete" in result.error
    result.fetches_ok = 1
    assert not ScrapingResultProcessor._is_clean_for_reconciliation(result)


@pytest.mark.asyncio
async def test_pipeline_loads_destinations_once_and_disabled_account_never_fetches(monkeypatch):
    from laughtrack.core.entities.club.handler import ClubHandler

    calls = []
    monkeypatch.setattr(
        ClubHandler, "get_physical_clubs_by_ids", lambda self, ids: calls.append(ids) or [venue(9001), venue(613)]
    )
    scraper = SeatEngineScraper(source_club())
    scraper.seatengine_client.fetch_events = AsyncMock(return_value=[event(), event(102)])
    page = await scraper.get_data("618")
    assert {show.club_id for show in scraper.transform_data(page, "618")} == {613, 9001}
    assert calls == [[613, 9001]]
    disabled = SeatEngineScraper(source_club(account=424, enabled=False))
    disabled.seatengine_client.fetch_events = AsyncMock(return_value=[event()])
    assert not (await disabled.get_data("424")).event_list
    disabled.seatengine_client.fetch_events.assert_not_called()
