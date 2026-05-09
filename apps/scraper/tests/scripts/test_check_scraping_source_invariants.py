"""
Unit tests for ``scripts/core/check_scraping_source_invariants.py``.

The script talks to the live scraper DB at runtime; these tests load it as
a module and stub ``_fetch_orphan_future_show_rows`` so the reporting /
exit-code logic is exercised without a database.
"""

import importlib.machinery
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

_SCRAPER_ROOT = Path(__file__).resolve().parents[2]  # apps/scraper/
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


def _row(**overrides):
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


def test_main_returns_two_when_orphan_future_inventory_exists(mod, monkeypatch, capsys):
    monkeypatch.setattr(mod, "_fetch_orphan_future_show_rows", lambda: [_row()])

    assert mod.main([]) == 2
    captured = capsys.readouterr()
    assert "1 club(s) have future shows but no enabled scraping_sources row" in captured.out
    assert "club=2287" in captured.out
    assert "Big Couch" in captured.out
    assert "future_shows=81" in captured.out
    assert "last_scraped_by=eventbrite" in captured.out


def test_main_returns_zero_when_no_orphan_future_inventory(mod, monkeypatch, capsys):
    monkeypatch.setattr(mod, "_fetch_orphan_future_show_rows", lambda: [])

    assert mod.main([]) == 0
    captured = capsys.readouterr()
    assert "No clubs have future shows without an enabled scraping_sources row" in captured.out


def test_main_returns_one_on_db_error(mod, monkeypatch, capsys):
    def _raise():
        raise RuntimeError("connection refused")

    monkeypatch.setattr(mod, "_fetch_orphan_future_show_rows", _raise)

    assert mod.main([]) == 1
    captured = capsys.readouterr()
    assert "ERROR: failed to query scraping source invariants" in captured.err
    assert "connection refused" in captured.err


def test_main_json_mode_emits_parseable_payload(mod, monkeypatch, capsys):
    monkeypatch.setattr(mod, "_fetch_orphan_future_show_rows", lambda: [_row()])

    rc = mod.main(["--json"])
    captured = capsys.readouterr()

    assert rc == 2
    payload = json.loads(captured.out)
    assert payload["orphan_future_show_clubs"][0]["club_name"] == "Big Couch"
    assert payload["orphan_future_show_clubs"][0]["future_show_count"] == 81
    assert "future shows but no enabled scraping_sources row" in captured.err


def test_main_json_mode_emits_empty_list_when_clean(mod, monkeypatch, capsys):
    monkeypatch.setattr(mod, "_fetch_orphan_future_show_rows", lambda: [])

    rc = mod.main(["--json"])
    captured = capsys.readouterr()

    assert rc == 0
    assert json.loads(captured.out) == {"orphan_future_show_clubs": []}
    assert "No clubs have future shows without an enabled scraping_sources row" in captured.err
