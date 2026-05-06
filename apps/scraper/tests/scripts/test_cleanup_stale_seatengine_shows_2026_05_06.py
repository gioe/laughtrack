"""
Unit tests for the TASK-1955 stale SeatEngine future-show cleanup.
"""

import importlib.machinery
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

_SCRAPER_ROOT = Path(__file__).resolve().parents[2]  # apps/scraper/
_SCRIPT_PATH = (
    _SCRAPER_ROOT
    / "scripts"
    / "core"
    / "cleanup_stale_seatengine_shows_2026_05_06.py"
)


def _load_module() -> ModuleType:
    loader = importlib.machinery.SourceFileLoader(
        "cleanup_stale_seatengine_shows_2026_05_06",
        str(_SCRIPT_PATH),
    )
    spec = importlib.util.spec_from_loader(
        "cleanup_stale_seatengine_shows_2026_05_06",
        loader,
    )
    m = importlib.util.module_from_spec(spec)
    sys.modules["cleanup_stale_seatengine_shows_2026_05_06"] = m
    loader.exec_module(m)
    return m


def test_task_1955_targets_stale_future_inventory_for_both_disabled_sources():
    mod = _load_module()

    targets = {
        t.club_id: (
            t.club_name,
            t.source_id,
            t.expected_external_id,
            t.disposition_kind,
            t.delete_future_shows,
        )
        for t in mod._CLEANUP_TARGETS
    }

    assert targets == {
        63: (
            "TK's",
            52,
            "514",
            "delete_stale_future_shows",
            True,
        ),
        82: (
            "Wicked Funny Comedy Club North Andover",
            146,
            "487",
            "delete_stale_future_shows",
            True,
        ),
    }
    assert mod._METADATA_KEY == "task_1955_show_cleanup"
    assert mod._STALE_LAST_SCRAPED_CUTOFF == "2026-03-26T23:59:59+00:00"


def test_existing_metadata_stamp_is_preserved_when_rerun_has_no_rows_to_delete():
    mod = _load_module()

    meta = {
        mod._METADATA_KEY: {
            "kind": "delete_stale_future_shows",
            "deleted_future_show_count": 94,
        }
    }

    assert mod._needs_metadata_update(meta, stale_future=0) is False
