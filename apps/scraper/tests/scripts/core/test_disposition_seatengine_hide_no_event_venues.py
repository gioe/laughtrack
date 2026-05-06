"""
Unit tests for the TASK-1954 SeatEngine no-event venue hide script.

The script is loaded via importlib to avoid installing it as a package.
"""

import importlib.util
from pathlib import Path
from types import ModuleType

_SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "scripts" / "core"
_SCRIPT_PATH = _SCRIPTS_DIR / "disposition_seatengine_hide_no_event_venues_2026_05_06.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "disposition_seatengine_hide_no_event_venues_2026_05_06",
        _SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_declares_task_1954_metadata_key_and_five_targets():
    mod = _load_module()

    assert mod._METADATA_KEY == "task_1954_hide"
    assert [target.club_id for target in mod._HIDE_TARGETS] == [63, 518, 520, 586, 589]
    assert [target.source_ids for target in mod._HIDE_TARGETS] == [
        [52],
        [7],
        [112],
        [271],
        [426, 911],
    ]
    assert all(target.rationale for target in mod._HIDE_TARGETS)
