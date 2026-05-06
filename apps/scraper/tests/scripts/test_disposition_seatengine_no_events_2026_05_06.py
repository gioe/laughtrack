"""
Unit tests for the TASK-1962 SeatEngine no-events disposition.
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
    / "disposition_seatengine_no_events_2026_05_06.py"
)
_MODULE_NAME = "disposition_seatengine_no_events_2026_05_06"


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


def test_task_1962_targets_only_dead_seatengine_fallback_rows():
    mod = _load_module()

    targets = {
        t.source_id: (t.expected_club_id, t.expected_platform, t.expected_external_id)
        for t in mod._DISABLE_TARGETS
    }

    assert targets == {
        673: (141, "seatengine", "35"),
        651: (207, "seatengine", "4"),
        1114: (463, "seatengine", "438"),
        570: (574, "seatengine", "554"),
    }
    assert mod._METADATA_KEY == "task_1962_disposition"
    assert mod._DISPOSITION_KIND == "fallback_redundant_no_events"
