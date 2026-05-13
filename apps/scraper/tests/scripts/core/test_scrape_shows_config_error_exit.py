"""Exit-code propagation for unregistered-scraper_key configuration errors.

Guard against TASK-2172 regressing: when a scraping_sources row points at a
scraper_key the runtime registry can't resolve, the per-club run currently
emits a WARN and the script exits 0 with 'Scraped 0 shows', indistinguishable
from a legitimate empty calendar. These tests pin the new contract — the
script exits non-zero whenever any ClubScrapingResult.config_error is True —
so the silent-zero-shows failure mode cannot return.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_repo_root = Path(__file__).resolve().parents[3]
_src_path = _repo_root / "src"
for p in (str(_src_path), str(_repo_root)):
    if p not in sys.path:
        sys.path.insert(0, p)

from laughtrack.core.models.results import ClubScrapingResult  # noqa: E402
from scripts.core import scrape_shows as mod  # noqa: E402


class _DummyScrapingService:
    def __init__(self, results):
        self._results = results
        self.scraped_ids: list[int] = []
        self.scraped_types: list[str] = []
        self.scraped_all = False

    def scrape_single_club(self, club_id=None):
        self.scraped_ids.append(club_id)
        return self._results

    def scrape_by_scraper_type(self, scraper_type=None):
        self.scraped_types.append(scraper_type)
        return self._results

    def scrape_all_clubs(self):
        self.scraped_all = True
        return self._results


class _DummyClubService:
    def __init__(self, club):
        self.club_handler = SimpleNamespace(get_club_by_id=lambda _id: club)

    def find_club_by_name(self, _name):
        return None


def _club(platform: str = "tixr"):
    return SimpleNamespace(
        id=141,
        name="Marion Theatre",
        active_scraping_source=SimpleNamespace(platform=platform),
    )


def _patch(monkeypatch, results, club=None):
    service = _DummyScrapingService(results)
    monkeypatch.setattr(mod, "ScrapingService", lambda: service)
    monkeypatch.setattr(mod, "ClubService", lambda: _DummyClubService(club or _club()))
    monkeypatch.setattr(mod, "ScraperService", lambda: SimpleNamespace())
    monkeypatch.setattr(mod, "MetricsService", lambda: SimpleNamespace())
    monkeypatch.setattr(mod.scraper_proxy_registry, "log_proxy_status", lambda: None)
    monkeypatch.setattr(mod, "validate_eventbrite_token", lambda: None)
    return service


def test_scrape_club_exits_non_zero_when_result_has_config_error(monkeypatch):
    config_err = ClubScrapingResult(
        club_name="Marion Theatre",
        shows=[],
        execution_time=0.0,
        error="no scraper registered for configured key(s) 'patron_ticket': "
              "scraper module may be unmerged on this branch, gitignored, ...",
        club_id=141,
        config_error=True,
    )
    _patch(monkeypatch, [config_err])

    monkeypatch.setattr(sys, "argv", ["scrape_shows.py", "--club-id", "141"])
    with pytest.raises(SystemExit) as excinfo:
        mod.main()

    assert excinfo.value.code == 1


def test_scrape_club_exits_zero_when_no_config_errors(monkeypatch):
    ok_result = ClubScrapingResult(
        club_name="Marion Theatre",
        shows=[],
        execution_time=0.1,
        club_id=141,
    )
    _patch(monkeypatch, [ok_result])

    monkeypatch.setattr(sys, "argv", ["scrape_shows.py", "--club-id", "141"])
    # Successful path returns normally (no SystemExit raised).
    mod.main()


def test_scrape_all_exits_non_zero_when_any_club_has_config_error(monkeypatch):
    ok = ClubScrapingResult(club_name="Healthy Club", shows=[], execution_time=0.1, club_id=1)
    bad = ClubScrapingResult(
        club_name="Bad Key Club",
        shows=[],
        execution_time=0.0,
        error="no scraper registered for configured key(s) 'gone_missing': ...",
        club_id=2,
        config_error=True,
    )
    _patch(monkeypatch, [ok, bad])

    monkeypatch.setattr(sys, "argv", ["scrape_shows.py", "--all"])
    with pytest.raises(SystemExit) as excinfo:
        mod.main()

    assert excinfo.value.code == 1
