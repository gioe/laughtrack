"""Reviewed Big Pine products are source-scoped, and never a clean empty feed."""

import json
from copy import deepcopy
from pathlib import Path
from unittest.mock import AsyncMock

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.foundation.infrastructure.http.diagnostics import ScrapeDiagnostics, bind_diagnostics, reset_diagnostics
from laughtrack.scrapers.implementations.api.seatengine.scraper import SeatEngineScraper
from laughtrack.utilities.domain.scraper.result import ScrapingResultProcessor

AUDIT = Path(__file__).resolve().parents[5] / "docs/audits/2026-10-05-big-pine-inventory"
PLAN = json.loads((AUDIT / "plan.json").read_text())
NATIVE = json.loads((AUDIT / "native.json").read_text())


def scraper(configured=True):
    club = Club(
        id=573 if configured else 999,
        name="Big Pine Comedy Festival",
        address="51 E Boston St",
        website="https://www.bigpinecomedyfestival.org",
        popularity=0,
        zip_code="85225",
        phone_number="",
        visible=True,
        timezone="America/Phoenix",
    )
    club.active_scraping_source = ScrapingSource(
        id=360 if configured else 999,
        club_id=club.id,
        platform="seatengine",
        scraper_key="seatengine",
        external_id="553" if configured else "999",
        source_url=club.website,
        metadata={"exclude_title_patterns": PLAN["exclude_title_patterns"]} if configured else {},
    )
    club.scraping_sources = [club.active_scraping_source]
    return SeatEngineScraper(club)


def test_all_nineteen_audited_products_are_excluded():
    events = [row["data"] for row in NATIVE["details"]]
    assert len(events) == 19
    assert scraper()._filter_title_patterns(events) == []


def test_genuine_performances_and_festival_pass_survive():
    titles = [
        "BIG PINE COMEDY FESTIVAL PRESENTS: DULCÉ SLOAN",
        "CACTUS COMEDY HOUR",
        "BIG PINE COMEDY FESTIVAL PASS",
        "Summer Camp Comedy Showcase",
        "EPK Review: Live Stand-up",
    ]
    events = [{"event": {"name": title}} for title in titles]
    assert scraper()._filter_title_patterns(events) == events


def test_unconfigured_seatengine_account_is_unchanged():
    events = deepcopy(NATIVE["events"])
    assert scraper(False)._filter_title_patterns(events) == events


def test_live_products_all_filtered_without_authorizing_reconciliation():
    instance = scraper()
    instance.seatengine_client.fetch_events = AsyncMock(return_value=deepcopy(NATIVE["events"]))
    result = instance.scrape_with_result()
    assert result.num_shows == 0
    assert result.fetches_ok == 1 and result.fetches_failed == 0
    assert result.items_before_filter == len(NATIVE["events"]) == 17
    assert not ScrapingResultProcessor._is_clean_for_reconciliation(result)


def test_only_dropped_items_are_added_before_base_counts_kept():
    diagnostics = ScrapeDiagnostics()
    token = bind_diagnostics(diagnostics)
    try:
        events = [NATIVE["events"][0], {"event": {"name": "Live Comedy"}}]
        kept = scraper()._filter_title_patterns(events)
        assert len(kept) == 1
        assert diagnostics.items_before_filter == 1
        diagnostics.add_items_before_filter(len(kept))
        assert diagnostics.items_before_filter == 2
    finally:
        reset_diagnostics(token)
