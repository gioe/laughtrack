"""
Unit tests for the TASK-1965 hidden/no-show SeatEngine duplicate disposition.
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
    / "disposition_seatengine_hidden_no_show_duplicates_2026_05_06.py"
)


def _load_module() -> ModuleType:
    loader = importlib.machinery.SourceFileLoader(
        "disposition_seatengine_hidden_no_show_duplicates_2026_05_06",
        str(_SCRIPT_PATH),
    )
    spec = importlib.util.spec_from_loader(
        "disposition_seatengine_hidden_no_show_duplicates_2026_05_06",
        loader,
    )
    m = importlib.util.module_from_spec(spec)
    sys.modules["disposition_seatengine_hidden_no_show_duplicates_2026_05_06"] = m
    loader.exec_module(m)
    return m


def test_task_1965_targets_all_hidden_no_show_duplicate_rows():
    mod = _load_module()

    targets = {
        t.source_id: (t.expected_club_id, t.expected_platform, t.expected_external_id)
        for t in mod._DISABLE_TARGETS
    }

    assert targets == {
        907: (147, "seatengine", "565"),
        330: (147, "seatengine_v3", "e7ea1e53-8a31-48b6-bfe4-fd9672791615"),
        905: (583, "seatengine", "563"),
        158: (583, "seatengine_v3", "58a56237-0902-40c0-8e4b-e592e782aec0"),
    }
    assert mod._METADATA_KEY == "task_1965_disposition"
    assert mod._DISPOSITION_KIND == "hidden_no_show_parallel_duplicate"
