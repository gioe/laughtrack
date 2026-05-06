"""
Unit tests for ``scripts/core/check_duplicate_scraping_priorities.py`` (TASK-1967).

The script talks to the live scraper DB at runtime; these tests load it as
a module and stub ``_fetch_duplicate_rows`` so the grouping / allowlist /
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
    _SCRAPER_ROOT
    / "scripts"
    / "core"
    / "check_duplicate_scraping_priorities.py"
)
_MODULE_NAME = "check_duplicate_scraping_priorities"


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


def _row(*, club_id, priority, source_id, platform, scraper_key="x", external_id=None,
         source_url="https://example.com", club_name="Club", visible=True, metadata=None):
    return {
        "club_id": club_id,
        "club_name": club_name,
        "visible": visible,
        "priority": priority,
        "source_id": source_id,
        "platform": platform,
        "scraper_key": scraper_key,
        "external_id": external_id,
        "source_url": source_url,
        "metadata": metadata or {},
    }


@pytest.fixture
def mod():
    return _load_module()


def test_group_rows_keys_by_club_and_priority(mod):
    rows = [
        _row(club_id=1, priority=0, source_id=10, platform="seatengine"),
        _row(club_id=1, priority=0, source_id=11, platform="custom"),
        _row(club_id=1, priority=1, source_id=12, platform="eventbrite"),
        _row(club_id=2, priority=0, source_id=20, platform="ticketmaster"),
        _row(club_id=2, priority=0, source_id=21, platform="seatengine"),
    ]

    grouped = mod._group_rows(rows)

    assert set(grouped.keys()) == {(1, 0), (1, 1), (2, 0)}
    assert len(grouped[(1, 0)]) == 2
    assert len(grouped[(1, 1)]) == 1
    assert len(grouped[(2, 0)]) == 2


def test_split_grouped_partitions_excepted_keys(mod):
    rows = [
        _row(club_id=1, priority=0, source_id=10, platform="seatengine"),
        _row(club_id=1, priority=0, source_id=11, platform="custom"),
        _row(club_id=2, priority=0, source_id=20, platform="seatengine"),
        _row(club_id=2, priority=0, source_id=21, platform="custom"),
    ]
    grouped = mod._group_rows(rows)

    unexcepted, excepted = mod._split_grouped(grouped, {(2, 0): "rationale"})

    assert set(unexcepted) == {(1, 0)}
    assert set(excepted) == {(2, 0)}
    assert excepted[(2, 0)][0]["club_id"] == 2


def test_main_returns_two_when_unexcepted_duplicates_present(mod, monkeypatch, capsys):
    rows = [
        _row(club_id=80, priority=0, source_id=101, platform="custom",
             scraper_key="uptown_theater", club_name="Uptown Theater"),
        _row(club_id=80, priority=0, source_id=931, platform="seatengine",
             scraper_key="seatengine", external_id="617", club_name="Uptown Theater"),
    ]
    monkeypatch.setattr(mod, "_fetch_duplicate_rows", lambda: rows)
    monkeypatch.setattr(mod, "_INTENTIONAL_EXCEPTIONS", {})

    assert mod.main([]) == 2
    captured = capsys.readouterr()
    assert "1 duplicate (club_id, priority) group(s) found" in captured.out
    assert "club=80" in captured.out
    assert "ss.id=101" in captured.out
    assert "ss.id=931" in captured.out


def test_main_returns_zero_when_only_excepted_duplicates_remain(mod, monkeypatch, capsys):
    rows = [
        _row(club_id=144, priority=0, source_id=485, platform="seatengine_v3",
             external_id="cf2b1561", club_name="The Comedy Studio"),
        _row(club_id=144, priority=0, source_id=943, platform="seatengine",
             external_id="631", club_name="The Comedy Studio"),
    ]
    monkeypatch.setattr(mod, "_fetch_duplicate_rows", lambda: rows)
    monkeypatch.setattr(
        mod,
        "_INTENTIONAL_EXCEPTIONS",
        {(144, 0): "TASK-EXAMPLE: rationale"},
    )

    assert mod.main([]) == 0
    captured = capsys.readouterr()
    assert "No unexcepted duplicate" in captured.out
    assert "1 duplicate group(s) excepted" in captured.out
    assert "TASK-EXAMPLE: rationale" in captured.out


def test_main_returns_zero_when_no_duplicates(mod, monkeypatch, capsys):
    monkeypatch.setattr(mod, "_fetch_duplicate_rows", lambda: [])
    monkeypatch.setattr(mod, "_INTENTIONAL_EXCEPTIONS", {})

    assert mod.main([]) == 0
    captured = capsys.readouterr()
    assert "No unexcepted duplicate" in captured.out


def test_main_returns_one_on_db_error(mod, monkeypatch, capsys):
    def _raise():
        raise RuntimeError("connection refused")

    monkeypatch.setattr(mod, "_fetch_duplicate_rows", _raise)

    assert mod.main([]) == 1
    captured = capsys.readouterr()
    assert "ERROR: failed to query scraping_sources" in captured.err
    assert "connection refused" in captured.err


def test_main_json_mode_emits_parseable_payload(mod, monkeypatch, capsys):
    rows = [
        _row(club_id=308, priority=0, source_id=711, platform="seatengine",
             external_id="105", club_name="Funny Bone Columbus"),
        _row(club_id=308, priority=0, source_id=191, platform="ticketmaster",
             scraper_key="live_nation", external_id="Z7r9jZadLM",
             club_name="Funny Bone Columbus"),
    ]
    monkeypatch.setattr(mod, "_fetch_duplicate_rows", lambda: rows)
    monkeypatch.setattr(mod, "_INTENTIONAL_EXCEPTIONS", {})

    rc = mod.main(["--json"])
    captured = capsys.readouterr()

    assert rc == 2
    payload = json.loads(captured.out)
    assert {g["club_id"] for g in payload["duplicate_groups"]} == {308}
    assert payload["excepted_groups"] == []
    rows_payload = payload["duplicate_groups"][0]["rows"]
    assert {r["source_id"] for r in rows_payload} == {711, 191}
    # Human report still emitted on stderr so JSON callers see the headline.
    assert "duplicate (club_id, priority) group" in captured.err


def test_intentional_exceptions_starts_empty_for_clean_baseline(mod):
    """
    Per TASK-1967 audit, no intentional multi-source priority configurations
    are documented yet — every observed duplicate today is unintentional drift.
    Adding entries should require a rationale referencing the approving task.
    """
    assert mod._INTENTIONAL_EXCEPTIONS == {}


def test_format_row_includes_disposition_context(mod):
    formatted = mod._format_row(_row(
        club_id=1, priority=0, source_id=42, platform="seatengine",
        scraper_key="seatengine", external_id="999",
        source_url="https://example.com/cal",
    ))
    assert "ss.id=42" in formatted
    assert "platform=seatengine" in formatted
    assert "scraper_key=seatengine" in formatted
    assert "external_id=999" in formatted
    assert "source_url=https://example.com/cal" in formatted
