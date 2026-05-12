from __future__ import annotations

import sys
import types
import asyncio
from datetime import timedelta
from pathlib import Path
from typing import Any

_repo_root = Path(__file__).resolve().parents[3]
_src_path = _repo_root / "src"
for _p in (str(_src_path), str(_repo_root)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from scripts.core import scrape_comedian_websites as script_mod  # noqa: E402
from laughtrack.scrapers.implementations.api.comedian_websites import scraper as scraper_mod  # noqa: E402


class _FakeComedianHandler:
    def __init__(self, rows: list[dict[str, Any]]):
        self.rows = rows
        self.calls: list[tuple[str, tuple[Any, ...] | None]] = []

    def execute_with_cursor(
        self,
        query: str,
        params: tuple[Any, ...] | None = None,
        return_results: bool = False,
    ) -> list[dict[str, Any]]:
        self.calls.append((query, params))
        assert return_results is True
        return self.rows


def _scraper_with_rows(rows: list[dict[str, Any]]) -> scraper_mod.ComedianWebsiteScraper:
    scraper = object.__new__(scraper_mod.ComedianWebsiteScraper)
    scraper._comedian_handler = _FakeComedianHandler(rows)
    return scraper


def test_selection_uses_existing_scraping_urls_for_never_scraped_and_stale_records(monkeypatch):
    rows = [
        {
            "uuid": "never",
            "name": "Never Scraped",
            "website": "https://never.example",
            "website_scraping_url": "https://never.example/tour",
            "website_last_scraped": None,
        },
        {
            "uuid": "stale",
            "name": "Stale Scraped",
            "website": "https://stale.example",
            "website_scraping_url": "https://stale.example/shows",
            "website_last_scraped": "2026-04-01T00:00:00+00:00",
        },
    ]
    scraper = _scraper_with_rows(rows)

    class ExplodingBraveSearchClient:
        def __init__(self):
            raise AssertionError("scrape backfill must not invoke Brave discovery")

    monkeypatch.setitem(
        sys.modules,
        "laughtrack.core.clients.brave.search",
        types.SimpleNamespace(BraveSearchClient=ExplodingBraveSearchClient),
    )

    selected = scraper._get_comedians_for_scraping()

    assert [row["uuid"] for row in selected] == ["never", "stale"]
    query, params = scraper._comedian_handler.calls[0]
    assert params is None
    assert "website_scraping_url IS NOT NULL" in query
    assert "website_last_scraped IS NULL" in query
    assert "website_last_scraped < NOW() - INTERVAL '7 days'" in query
    assert "brave" not in query.lower()


def test_selection_limit_applies_after_never_scraped_and_stale_records_are_selected():
    rows = [
        {"uuid": "never", "name": "Never", "website_last_scraped": None},
        {"uuid": "stale", "name": "Stale", "website_last_scraped": "2026-04-01T00:00:00+00:00"},
        {"uuid": "older", "name": "Older", "website_last_scraped": "2026-03-01T00:00:00+00:00"},
    ]
    scraper = _scraper_with_rows(rows)

    selected = scraper._get_comedians_for_scraping(limit=2)

    assert [row["uuid"] for row in selected] == ["never", "stale"]


def test_run_summary_counts_eligible_never_scraped_success_empty_and_errors():
    rows = [
        {"uuid": "never", "website_last_scraped": None},
        {"uuid": "stale", "website_last_scraped": "2026-04-01T00:00:00+00:00"},
        {"uuid": "error", "website_last_scraped": "2026-04-02T00:00:00+00:00"},
    ]
    outcomes = [
        scraper_mod.ComedianWebsiteScrapeOutcome("Never", "success", venue_count=2),
        scraper_mod.ComedianWebsiteScrapeOutcome("Stale", "empty"),
        scraper_mod.ComedianWebsiteScrapeOutcome("Error", "error"),
    ]

    summary = scraper_mod.ComedianWebsiteScraper._build_run_summary(rows, outcomes)

    assert summary.total_eligible == 3
    assert summary.never_scraped == 1
    assert summary.stale == 2
    assert summary.scraped_successfully == 1
    assert summary.empty == 1
    assert summary.errors == 1
    assert summary.venues_discovered == 2


def test_platform_extractors_return_event_count_for_success_classification(monkeypatch):
    scraper = object.__new__(scraper_mod.ComedianWebsiteScraper)
    scraper._club = types.SimpleNamespace(name="Comedian Websites")
    scraper.logger_context = {}

    async def fake_extract_event_count(**_kwargs):
        return 3

    monkeypatch.setattr(
        scraper_mod.SquarespaceExtractorForComedian,
        "extract_event_count",
        fake_extract_event_count,
    )
    monkeypatch.setattr(scraper, "_update_scrape_metadata", lambda *_args: None)
    monkeypatch.setattr(scraper, "_update_scraping_url_confidence", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(scraper, "_update_confidence", lambda *_args, **_kwargs: None)

    event_count = asyncio.run(
        scraper._try_squarespace(
            {"uuid": "comic"},
            scraper_mod.Comedian(name="Tour Comic", uuid="comic"),
            "https://comic.example/tour",
            "https://comic.example",
            "<html></html>",
        )
    )

    assert event_count == 3


def test_json_ld_venue_upsert_receives_comedian_discovery_metadata():
    scraper = object.__new__(scraper_mod.ComedianWebsiteScraper)
    scraper._club_handler = types.SimpleNamespace(upsert_for_tour_date_venue=lambda venue: types.SimpleNamespace(id=77))
    scraper._club = types.SimpleNamespace(name="Comedian Websites")
    scraper.logger_context = {}

    event = types.SimpleNamespace(
        start_date=scraper_mod.datetime.now(tz=scraper_mod.timezone.utc) + timedelta(days=30),
        url="https://comic.example/shows/venue-night",
        location=types.SimpleNamespace(
            name="Venue Night",
            address=types.SimpleNamespace(
                address_locality="Austin",
                address_region="TX",
                postal_code="78701",
                address_country="US",
            ),
        ),
    )
    captured = []
    scraper._club_handler.upsert_for_tour_date_venue = lambda venue: captured.append(venue) or types.SimpleNamespace(id=77)

    count = scraper._extract_venues_from_events(
        [event],
        scraper_mod.Comedian(name="Tour Comic", uuid="comic"),
        "https://comic.example/tour",
    )

    assert count == 1
    assert captured[0]["discovery_metadata"] == {
        "source": "comedian_websites",
        "comedian_refs": [{"uuid": "comic", "name": "Tour Comic"}],
        "sample_urls": ["https://comic.example/tour"],
        "event_urls": ["https://comic.example/shows/venue-night"],
        "platform_hints": ["json_ld"],
    }


def test_script_prints_operator_facing_run_summary(capsys):
    summary = scraper_mod.ComedianWebsiteScrapeRunSummary(
        total_eligible=3,
        never_scraped=1,
        stale=2,
        scraped_successfully=1,
        empty=1,
        errors=1,
        venues_discovered=2,
    )

    script_mod.print_run_summary(summary)

    captured = capsys.readouterr()
    assert "total eligible: 3" in captured.out
    assert "never scraped: 1" in captured.out
    assert "scraped successfully: 1" in captured.out
    assert "empty: 1" in captured.out
    assert "errors: 1" in captured.out
