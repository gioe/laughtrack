"""
Unit tests for ``scripts/core/check_scraping_source_invariants.py``.

The script talks to the live scraper DB at runtime; these tests load it as
a module and stub the row-fetchers so the reporting / exit-code logic is
exercised without a database.
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


from datetime import datetime, timedelta, timezone

AS_OF = datetime(2026, 9, 27, 12, tzinfo=timezone.utc)


def _row(**overrides):
    row = {
        "club_id": 2287,
        "club_name": "Example",
        "visible": True,
        "status": "active",
        "future_show_count": 4,
        "last_last_scraped_date": None,
        "last_aggregate_scraped_date": None,
    }
    row.update(overrides)
    return row


@pytest.mark.parametrize(
    "key",
    [
        "ticketmaster_national",
        "next_stop_comedy",
        "ticket_tailor",
        "pabst_theater_group",
        "comedian_websites",
    ],
)
def test_recent_aggregate_provenance_is_coverage(mod, key):
    assert mod.is_aggregate_covered(
        {"last_scraped_by": key, "last_scraped_date": AS_OF}, AS_OF
    )


def test_eventbrite_requires_organizer_provenance(mod):
    row = {"last_scraped_by": "eventbrite", "last_scraped_date": AS_OF}
    assert not mod.is_aggregate_covered(row, AS_OF)
    assert mod.is_aggregate_covered({**row, "scraped_by_organizer_id": 42}, AS_OF)


@pytest.mark.parametrize(
    "stamp",
    [
        None,
        "bad",
        AS_OF - timedelta(days=8),
        AS_OF + timedelta(seconds=1),
        AS_OF.replace(tzinfo=None),
    ],
)
def test_aggregate_key_without_recent_valid_timestamp_is_not_coverage(mod, stamp):
    assert not mod.is_aggregate_covered(
        {"last_scraped_by": "ticketmaster_national", "last_scraped_date": stamp}, AS_OF
    )


def test_retired_key_and_generic_future_inventory_do_not_establish_coverage(mod):
    assert not mod.is_aggregate_covered(
        {"last_scraped_by": "eventbrite_national", "last_scraped_date": AS_OF}, AS_OF
    )
    assert not mod.is_aggregate_covered({"date": AS_OF + timedelta(days=10)}, AS_OF)


def test_recency_boundary_and_serialized_timestamp(mod):
    stamp = AS_OF - timedelta(days=7)
    assert mod.is_aggregate_covered(
        {"last_scraped_by": "next_stop_comedy", "last_scraped_date": stamp.isoformat()},
        AS_OF,
    )
    assert not mod.is_aggregate_covered(
        {
            "last_scraped_by": "next_stop_comedy",
            "last_scraped_date": stamp - timedelta(microseconds=1),
        },
        AS_OF,
    )


def test_classification_separates_indirect_unknown_fresh_and_unknown_stale(mod):
    rows = [
        _row(club_id=1, last_aggregate_scraped_date=AS_OF),
        _row(club_id=2, last_last_scraped_date=AS_OF),
        _row(club_id=3),
        _row(club_id=4, future_show_count=0, last_aggregate_scraped_date=AS_OF),
        _row(club_id=5, visible=False),
        _row(club_id=6, status="closed"),
    ]
    report = mod.build_report(rows, AS_OF)
    assert len(report["no_direct_source_clubs"]) == 6
    assert [r["club_id"] for r in report["aggregate_covered_clubs"]] == [1, 4]
    assert [r["club_id"] for r in report["recently_written_unknown_source_clubs"]] == [
        2
    ]
    assert [r["club_id"] for r in report["review_required_clubs"]] == [3]
    assert [r["club_id"] for r in report["orphan_future_show_clubs"]] == [3, 5, 6]


def test_fresh_direct_write_does_not_refresh_stale_aggregate_evidence(mod):
    report = mod.build_report(
        [
            _row(
                last_aggregate_scraped_date=AS_OF - timedelta(days=8),
                last_last_scraped_date=AS_OF,
            )
        ],
        AS_OF,
    )
    assert report["aggregate_covered_clubs"] == []
    assert report["review_required_clubs"] == []
    assert report["recently_written_unknown_source_clubs"]


def test_report_whitelist_drops_urls_and_metadata(mod):
    report = mod.build_report(
        [
            _row(
                website="https://user:secret@host",
                sample_show_page_url="https://host/?api_key=secret",
                metadata={"password": "secret"},
            )
        ],
        AS_OF,
    )
    assert "secret" not in json.dumps(report, default=str)


@pytest.mark.parametrize(
    "rows,expected",
    [
        ([], 0),
        ([_row()], 2),
        ([_row(visible=False)], 0),
        ([_row(future_show_count=0)], 2),
    ],
)
def test_exit_codes_and_json(mod, monkeypatch, capsys, rows, expected):
    monkeypatch.setattr(mod, "_fetch_orphan_future_show_rows", lambda: rows)
    monkeypatch.setattr(mod, "_fetch_active_no_source_rows", lambda: [])
    assert mod.main(["--json"]) == expected
    output = capsys.readouterr()
    report = json.loads(output.out)
    assert len(report["no_direct_source_clubs"]) == len(rows)
    assert "INFO:" in output.err
    assert "cannot ingest" not in output.err


def test_fresh_unknown_write_does_not_fail_cli(mod, monkeypatch, capsys):
    monkeypatch.setattr(
        mod,
        "_fetch_orphan_future_show_rows",
        lambda: [_row(last_last_scraped_date=datetime.now(timezone.utc))],
    )
    monkeypatch.setattr(mod, "_fetch_active_no_source_rows", lambda: [])
    assert mod.main([]) == 0
    assert "1 have other recent writes" in capsys.readouterr().out


def test_db_errors_do_not_leak_connection_details(mod, monkeypatch, capsys):
    def fail():
        raise RuntimeError("postgresql://user:secret@host")

    monkeypatch.setattr(mod, "_fetch_orphan_future_show_rows", fail)
    assert mod.main([]) == 1
    error = capsys.readouterr().err
    assert "RuntimeError" in error
    assert "secret" not in error


@pytest.mark.parametrize("days", ["0", "-1", "366"])
def test_invalid_coverage_days_rejected(mod, days):
    with pytest.raises(SystemExit):
        mod.main(["--coverage-days", days])


def test_queries_consider_past_persisted_evidence_and_export_no_urls(mod):
    for query in (mod._ORPHAN_FUTURE_SHOWS_QUERY, mod._ACTIVE_NO_SOURCE_QUERY):
        assert "LEFT JOIN shows s ON s.club_id = c.id" in query
        assert "s.scraped_by_organizer_id IS NOT NULL" in query
        assert "MAX(s.last_scraped_date) FILTER" in query
        assert (
            "WHERE s.date > NOW()" in query
        )  # only aggregate FILTER, not join restriction
        assert "ss.enabled = TRUE" in query
        assert "show_page_url" not in query
        assert "c.website" not in query
        assert "source_url" not in query
    assert "c.visible = TRUE" in mod._ACTIVE_NO_SOURCE_QUERY


def test_query_session_is_readonly_and_bounded(mod, monkeypatch):
    from unittest.mock import MagicMock

    connection = MagicMock()
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.description = [("club_id",), ("club_name",)]
    cursor.fetchall.return_value = [(1, "Example")]
    manager = MagicMock()
    manager.__enter__.return_value = connection
    monkeypatch.setattr(mod, "get_connection", lambda **kwargs: manager)
    assert mod._fetch_rows("SELECT 1") == [{"club_id": 1, "club_name": "Example"}]
    connection.set_session.assert_called_once_with(readonly=True)
    assert cursor.execute.call_args_list[0].args == (
        "SET LOCAL statement_timeout = '60s'",
    )
