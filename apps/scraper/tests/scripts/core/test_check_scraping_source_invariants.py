"""
Unit tests for ``scripts/core/check_scraping_source_invariants.py``.

The script talks to the live scraper DB at runtime; these tests load it as
a module and stub the row-fetchers so the reporting / classification /
exit-code logic is exercised without a database.
"""

import importlib.machinery
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

_SCRAPER_ROOT = Path(__file__).resolve().parents[3]  # apps/scraper/
_SCRIPT_PATH = (
    _SCRAPER_ROOT / "scripts" / "core" / "check_scraping_source_invariants.py"
)
_MODULE_NAME = "check_scraping_source_invariants"


def _load_module() -> ModuleType:
    loader = importlib.machinery.SourceFileLoader(_MODULE_NAME, str(_SCRIPT_PATH))
    spec = importlib.util.spec_from_loader(_MODULE_NAME, loader)
    if spec is None:
        raise AssertionError(f"Could not load spec for {_SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    original = sys.modules.get(_MODULE_NAME)
    try:
        sys.modules[_MODULE_NAME] = module
        loader.exec_module(module)
        return module
    finally:
        if original is None:
            sys.modules.pop(_MODULE_NAME, None)
        else:
            sys.modules[_MODULE_NAME] = original


@pytest.fixture
def mod():
    return _load_module()


def _orphan_row(**overrides):
    row = {
        "club_id": 2287,
        "club_name": "Big Couch",
        "visible": False,
        "status": "active",
        "future_show_count": 81,
        "first_future_show": None,
        "last_future_show": None,
        "first_last_scraped_date": None,
        "last_last_scraped_date": None,
        "last_scraped_by_values": ["eventbrite"],
        "sample_show_page_url": "https://www.eventbrite.com/e/example",
    }
    row.update(overrides)
    return row


def _tour_date_row(**overrides):
    row = {
        "club_id": 9001,
        "club_name": "Stuck Club",
        "city": "Austin",
        "state": "TX",
        "website": "https://stuck.example",
        "visible": True,
        "status": "active",
        "tour_date_created_at": None,
        "tour_date_age_days": 120,
        "enabled_source_count": 1,
    }
    row.update(overrides)
    return row


# ---------------------------------------------------------------------------
# Orphan-future-shows invariant (Invariant 1)
# ---------------------------------------------------------------------------


def test_main_returns_two_when_orphan_future_inventory_exists(mod, monkeypatch, capsys):
    monkeypatch.setattr(mod, "_fetch_orphan_future_show_rows", lambda: [_orphan_row()])
    monkeypatch.setattr(mod, "_fetch_tour_date_only_rows", lambda: [])

    assert mod.main([]) == 2
    captured = capsys.readouterr()
    assert "1 club(s) have future shows but no enabled scraping_sources row" in captured.out
    assert "club=2287" in captured.out
    assert "Big Couch" in captured.out
    assert "future_shows=81" in captured.out
    assert "last_scraped_by=eventbrite" in captured.out


def test_main_returns_zero_when_no_orphan_future_inventory(mod, monkeypatch, capsys):
    monkeypatch.setattr(mod, "_fetch_orphan_future_show_rows", lambda: [])
    monkeypatch.setattr(mod, "_fetch_tour_date_only_rows", lambda: [])

    assert mod.main([]) == 0
    captured = capsys.readouterr()
    assert "No clubs have future shows without an enabled scraping_sources row" in captured.out


def test_main_returns_one_on_db_error(mod, monkeypatch, capsys):
    def _raise():
        raise RuntimeError("connection refused")

    monkeypatch.setattr(mod, "_fetch_orphan_future_show_rows", _raise)
    monkeypatch.setattr(mod, "_fetch_tour_date_only_rows", lambda: [])

    assert mod.main([]) == 1
    captured = capsys.readouterr()
    assert "ERROR: failed to query scraping source invariants" in captured.err
    assert "connection refused" in captured.err


def test_main_json_mode_emits_parseable_payload(mod, monkeypatch, capsys):
    monkeypatch.setattr(mod, "_fetch_orphan_future_show_rows", lambda: [_orphan_row()])
    monkeypatch.setattr(mod, "_fetch_tour_date_only_rows", lambda: [])

    rc = mod.main(["--json"])
    captured = capsys.readouterr()

    assert rc == 2
    payload = json.loads(captured.out)
    assert payload["orphan_future_show_clubs"][0]["club_name"] == "Big Couch"
    assert payload["orphan_future_show_clubs"][0]["future_show_count"] == 81
    assert payload["tour_date_only_clubs"] == {
        "stale_days_threshold": 30,
        "recent_discovery": [],
        "onboarding_review_needed": [],
    }
    assert "future shows but no enabled scraping_sources row" in captured.err


def test_main_json_mode_emits_empty_payload_when_clean(mod, monkeypatch, capsys):
    monkeypatch.setattr(mod, "_fetch_orphan_future_show_rows", lambda: [])
    monkeypatch.setattr(mod, "_fetch_tour_date_only_rows", lambda: [])

    rc = mod.main(["--json"])
    captured = capsys.readouterr()

    assert rc == 0
    payload = json.loads(captured.out)
    assert payload["orphan_future_show_clubs"] == []
    assert payload["tour_date_only_clubs"]["recent_discovery"] == []
    assert payload["tour_date_only_clubs"]["onboarding_review_needed"] == []
    assert "No clubs have future shows without an enabled scraping_sources row" in captured.err


# ---------------------------------------------------------------------------
# Tour_dates-only invariant (Invariant 2)
# ---------------------------------------------------------------------------


def test_classify_tour_date_rows_splits_by_age(mod):
    rows = [
        _tour_date_row(club_id=1, tour_date_age_days=120),
        _tour_date_row(club_id=2, tour_date_age_days=5),
        _tour_date_row(club_id=3, tour_date_age_days=30),  # boundary — at threshold, still recent
        _tour_date_row(club_id=4, tour_date_age_days=31),  # one day past threshold
        _tour_date_row(club_id=5, tour_date_age_days=None),  # missing age — treat as recent
    ]

    recent, stale = mod._classify_tour_date_rows(rows, stale_days=30)

    assert [r["club_id"] for r in stale] == [1, 4]
    assert all(r["classification"] == "onboarding_review_needed" for r in stale)
    assert [r["club_id"] for r in recent] == [2, 3, 5]
    assert all(r["classification"] == "recent_discovery" for r in recent)


def test_main_flags_stale_tour_date_only_clubs(mod, monkeypatch, capsys):
    """A club whose only enabled source is tour_dates older than the threshold trips exit 2."""
    monkeypatch.setattr(mod, "_fetch_orphan_future_show_rows", lambda: [])
    monkeypatch.setattr(
        mod,
        "_fetch_tour_date_only_rows",
        lambda: [
            _tour_date_row(
                club_id=9001,
                club_name="Stuck Club",
                tour_date_age_days=120,
            )
        ],
    )

    rc = mod.main([])
    captured = capsys.readouterr()

    assert rc == 2
    assert "1 active club(s) have only tour_dates enabled and are older than 30 days" in captured.out
    assert "club=9001" in captured.out
    assert "Stuck Club" in captured.out
    assert "tour_dates_age=120d" in captured.out


def test_main_separates_recent_discovery_from_stuck_rows(mod, monkeypatch, capsys):
    """Recent tour_dates discoveries are reported separately and don't trip exit 2."""
    monkeypatch.setattr(mod, "_fetch_orphan_future_show_rows", lambda: [])
    monkeypatch.setattr(
        mod,
        "_fetch_tour_date_only_rows",
        lambda: [
            _tour_date_row(club_id=1, club_name="Fresh Club", tour_date_age_days=3),
        ],
    )

    rc = mod.main([])
    captured = capsys.readouterr()

    assert rc == 0
    # Recent rows surface as an INFO section, not an ERROR section.
    assert "INFO: 1 active club(s) have only tour_dates enabled but are within 30 days" in captured.out
    assert "ERROR:" not in captured.out
    assert "Fresh Club" in captured.out


def test_main_reports_both_sections_when_mixed(mod, monkeypatch, capsys):
    monkeypatch.setattr(mod, "_fetch_orphan_future_show_rows", lambda: [])
    monkeypatch.setattr(
        mod,
        "_fetch_tour_date_only_rows",
        lambda: [
            _tour_date_row(club_id=1, club_name="Stuck One", tour_date_age_days=90),
            _tour_date_row(club_id=2, club_name="Fresh Two", tour_date_age_days=7),
        ],
    )

    rc = mod.main([])
    captured = capsys.readouterr()

    assert rc == 2
    assert "Stuck One" in captured.out
    assert "Fresh Two" in captured.out
    assert "1 active club(s) have only tour_dates enabled and are older than 30 days" in captured.out
    assert "1 active club(s) have only tour_dates enabled but are within 30 days" in captured.out


def test_main_returns_zero_when_no_tour_date_only_clubs(mod, monkeypatch, capsys):
    monkeypatch.setattr(mod, "_fetch_orphan_future_show_rows", lambda: [])
    monkeypatch.setattr(mod, "_fetch_tour_date_only_rows", lambda: [])

    rc = mod.main([])
    captured = capsys.readouterr()

    assert rc == 0
    assert "No active clubs are stuck with only tour_dates as their enabled source." in captured.out


def test_main_honors_custom_stale_days_threshold(mod, monkeypatch, capsys):
    """--stale-days=14 reclassifies a 20-day-old row as stuck."""
    monkeypatch.setattr(mod, "_fetch_orphan_future_show_rows", lambda: [])
    monkeypatch.setattr(
        mod,
        "_fetch_tour_date_only_rows",
        lambda: [_tour_date_row(club_id=1, tour_date_age_days=20)],
    )

    rc = mod.main(["--stale-days", "14"])
    captured = capsys.readouterr()

    assert rc == 2
    assert "older than 14 days" in captured.out


def test_main_json_payload_includes_classified_tour_date_rows(mod, monkeypatch, capsys):
    monkeypatch.setattr(mod, "_fetch_orphan_future_show_rows", lambda: [])
    monkeypatch.setattr(
        mod,
        "_fetch_tour_date_only_rows",
        lambda: [
            _tour_date_row(club_id=1, tour_date_age_days=90),
            _tour_date_row(club_id=2, tour_date_age_days=2),
        ],
    )

    rc = mod.main(["--json"])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 2
    section = payload["tour_date_only_clubs"]
    assert section["stale_days_threshold"] == 30
    assert [r["club_id"] for r in section["onboarding_review_needed"]] == [1]
    assert section["onboarding_review_needed"][0]["classification"] == "onboarding_review_needed"
    assert [r["club_id"] for r in section["recent_discovery"]] == [2]
    assert section["recent_discovery"][0]["classification"] == "recent_discovery"


def test_tour_date_only_query_filters_correctly(mod):
    """SQL guards the discovery loop: only-tour_dates AND active AND visible."""
    query = mod._TOUR_DATE_ONLY_CLUBS_QUERY
    assert "ss.enabled = TRUE" in query
    # Reject clubs that also have a non-tour_dates enabled source.
    assert "has_non_tour_date = FALSE" in query
    # Active visible clubs only — hidden/inactive venues aren't shipped to users.
    assert "COALESCE(c.visible, TRUE) = TRUE" in query
    assert "c.status = 'active'" in query
    # Must surface tour_dates row age so the Python classifier can split rows.
    assert "tour_date_created_at" in query
    assert "tour_date_age_days" in query
