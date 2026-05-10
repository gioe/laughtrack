"""
Unit tests for ``scripts/core/audit_stale_scraper_keys.py``.

The script talks to the live scraper DB at runtime; these tests load it as
a module and stub database access so reporting, exit codes, and query shape
are exercised without a database.
"""

import importlib.machinery
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

_SCRAPER_ROOT = Path(__file__).resolve().parents[2]  # apps/scraper/
_SCRIPT_PATH = _SCRAPER_ROOT / "scripts" / "core" / "audit_stale_scraper_keys.py"
_MODULE_NAME = "audit_stale_scraper_keys"


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
        "scraper_key": "eventbrite",
        "enabled_source_count": 3,
        "recent_show_count": 0,
        "most_recent_scrape": None,
    }
    row.update(overrides)
    return row


def test_main_returns_two_when_stale_keys_exist(mod, monkeypatch, capsys):
    seen = {}

    def _fetch(days):
        seen["days"] = days
        return [_row()]

    monkeypatch.setattr(mod, "_fetch_stale_key_rows", _fetch)

    assert mod.main([]) == 2
    captured = capsys.readouterr()
    assert seen == {"days": 7}
    assert "1 enabled scraper_key value(s)" in captured.out
    assert "last 7 day(s)" in captured.out
    assert "eventbrite" in captured.out
    assert "enabled_sources=3" in captured.out


def test_main_uses_custom_days_window(mod, monkeypatch, capsys):
    seen = {}

    def _fetch(days):
        seen["days"] = days
        return []

    monkeypatch.setattr(mod, "_fetch_stale_key_rows", _fetch)

    assert mod.main(["--days", "14"]) == 0
    captured = capsys.readouterr()
    assert seen == {"days": 14}
    assert "last 14 day(s)" in captured.out


def test_main_rejects_non_positive_days(mod):
    with pytest.raises(SystemExit) as exc:
        mod.main(["--days", "0"])

    assert exc.value.code == 2


def test_main_returns_one_on_db_error(mod, monkeypatch, capsys):
    def _raise(days):
        raise RuntimeError(f"connection refused for {days}")

    monkeypatch.setattr(mod, "_fetch_stale_key_rows", _raise)

    assert mod.main(["--days", "3"]) == 1
    captured = capsys.readouterr()
    assert "ERROR: failed to query stale scraper keys" in captured.err
    assert "RuntimeError: connection refused for 3" in captured.err


def test_main_json_mode_emits_parseable_payload(mod, monkeypatch, capsys):
    monkeypatch.setattr(
        mod,
        "_fetch_stale_key_rows",
        lambda days: [_row(scraper_key="prekindle", enabled_source_count=2)],
    )

    rc = mod.main(["--days", "21", "--json"])
    captured = capsys.readouterr()

    assert rc == 2
    payload = json.loads(captured.out)
    assert payload["days"] == 21
    assert payload["stale_scraper_keys"][0]["scraper_key"] == "prekindle"
    assert payload["stale_scraper_keys"][0]["enabled_source_count"] == 2
    assert "last 21 day(s)" in captured.err


def test_main_json_mode_emits_empty_list_when_clean(mod, monkeypatch, capsys):
    monkeypatch.setattr(mod, "_fetch_stale_key_rows", lambda days: [])

    rc = mod.main(["--json"])
    captured = capsys.readouterr()

    assert rc == 0
    assert json.loads(captured.out) == {"days": 7, "stale_scraper_keys": []}
    assert "Every enabled scraper_key has last_scraped_by activity" in captured.err


def test_fetch_query_detects_enabled_keys_with_no_recent_activity(mod, monkeypatch):
    calls = {}

    class FakeCursor:
        description = [
            ("scraper_key",),
            ("enabled_source_count",),
            ("recent_show_count",),
            ("most_recent_scrape",),
        ]

        def execute(self, query, params):
            calls["query"] = query
            calls["params"] = params

        def fetchall(self):
            return [("eventbrite", 3, 0, None)]

        def close(self):
            calls["closed"] = True

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return FakeCursor()

    monkeypatch.setattr(mod, "get_connection", lambda: FakeConnection())

    rows = mod._fetch_stale_key_rows(9)

    assert rows == [
        {
            "scraper_key": "eventbrite",
            "enabled_source_count": 3,
            "recent_show_count": 0,
            "most_recent_scrape": None,
        }
    ]
    assert calls["params"] == (9,)
    assert "FROM scraping_sources ss" in calls["query"]
    assert "WHERE ss.enabled = TRUE" in calls["query"]
    assert "FROM shows s" in calls["query"]
    assert "s.last_scraped_date >= NOW() - (%s * INTERVAL '1 day')" in calls["query"]
    assert "LEFT JOIN recent_activity" in calls["query"]
    assert "WHERE ra.scraper_key IS NULL" in calls["query"]
    assert calls["closed"] is True
