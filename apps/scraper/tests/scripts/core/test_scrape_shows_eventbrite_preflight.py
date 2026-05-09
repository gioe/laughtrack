"""Tests for scrape_shows Eventbrite token preflight routing."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

_repo_root = Path(__file__).resolve().parents[3]
_src_path = _repo_root / "src"
for p in (str(_src_path), str(_repo_root)):
    if p not in sys.path:
        sys.path.insert(0, p)

from scripts.core import scrape_shows as mod  # noqa: E402


class _DummyScrapingService:
    def __init__(self):
        self.scraped_ids: list[int] = []
        self.scraped_types: list[str] = []

    def scrape_single_club(self, club_id=None):
        self.scraped_ids.append(club_id)

    def scrape_by_scraper_type(self, scraper_type=None):
        self.scraped_types.append(scraper_type)


class _DummyClubService:
    def __init__(self, club):
        self.club_handler = SimpleNamespace(get_club_by_id=lambda club_id: club)

    def find_club_by_name(self, _name):
        raise AssertionError("find_club_by_name should not be used for --club-id")


def _club_with_platform(platform: str):
    return SimpleNamespace(
        id=141,
        name="Improv Asylum",
        active_scraping_source=SimpleNamespace(platform=platform),
    )


def _patch_common_services(monkeypatch, club):
    scraping_service = _DummyScrapingService()
    monkeypatch.setattr(mod, "ScrapingService", lambda: scraping_service)
    monkeypatch.setattr(mod, "ClubService", lambda: _DummyClubService(club))
    monkeypatch.setattr(mod, "ScraperService", lambda: SimpleNamespace())
    monkeypatch.setattr(mod, "MetricsService", lambda: SimpleNamespace())
    monkeypatch.setattr(mod.scraper_proxy_registry, "log_proxy_status", lambda: None)
    return scraping_service


def test_club_id_non_eventbrite_source_skips_eventbrite_token_validation(monkeypatch):
    scraping_service = _patch_common_services(monkeypatch, _club_with_platform("tixr"))

    def fail_if_called():
        raise AssertionError("non-Eventbrite club should not validate Eventbrite token")

    monkeypatch.setattr(mod, "validate_eventbrite_token", fail_if_called)

    monkeypatch.setattr(sys, "argv", ["scrape_shows.py", "--club-id", "141"])
    mod.main()

    assert scraping_service.scraped_ids == [141]


def test_club_id_eventbrite_source_validates_eventbrite_token(monkeypatch):
    _patch_common_services(monkeypatch, _club_with_platform("eventbrite"))
    calls = []
    monkeypatch.setattr(mod, "validate_eventbrite_token", lambda: calls.append("validated"))

    monkeypatch.setattr(sys, "argv", ["scrape_shows.py", "--club-id", "141"])
    mod.main()

    assert calls == ["validated"]


def test_eventbrite_prefixed_scraper_type_validates_eventbrite_token(monkeypatch):
    scraping_service = _patch_common_services(monkeypatch, _club_with_platform("tixr"))
    calls = []
    monkeypatch.setattr(mod, "validate_eventbrite_token", lambda: calls.append("validated"))

    monkeypatch.setattr(sys, "argv", ["scrape_shows.py", "--scraper-type", "eventbrite_national"])
    mod.main()

    assert calls == ["validated"]
    assert scraping_service.scraped_types == ["eventbrite_national"]
