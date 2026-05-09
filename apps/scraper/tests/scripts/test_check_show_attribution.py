"""
Unit tests for ``scripts/core/check_show_attribution.py``.

The script talks to the live scraper DB at runtime; these tests load it as
a module and stub ``_fetch_orphan_rows`` so the reporting / exit-code
logic is exercised without a database.
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
    _SCRAPER_ROOT / "scripts" / "core" / "check_show_attribution.py"
)
_MODULE_NAME = "check_show_attribution"


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


def test_main_returns_two_when_orphan_attribution_values_exist(mod, monkeypatch, capsys):
    monkeypatch.setattr(
        mod,
        "_fetch_orphan_rows",
        lambda: [
            {"scraper_key": "live_naion", "show_count": 42},  # typo of live_nation
            {"scraper_key": "retired_scraper", "show_count": 5},
        ],
    )

    assert mod.main([]) == 2
    captured = capsys.readouterr()
    assert "2 shows.last_scraped_by value(s) missing" in captured.out
    assert "live_naion" in captured.out
    assert "retired_scraper" in captured.out
    assert "show_count=42" in captured.out


def test_main_returns_zero_when_no_orphans(mod, monkeypatch, capsys):
    monkeypatch.setattr(mod, "_fetch_orphan_rows", lambda: [])

    assert mod.main([]) == 0
    captured = capsys.readouterr()
    assert "All shows.last_scraped_by values are present" in captured.out


def test_main_returns_one_on_db_error(mod, monkeypatch, capsys):
    def _raise():
        raise RuntimeError("connection refused")

    monkeypatch.setattr(mod, "_fetch_orphan_rows", _raise)

    assert mod.main([]) == 1
    captured = capsys.readouterr()
    assert "ERROR: failed to query show attribution orphans" in captured.err
    assert "connection refused" in captured.err


def test_main_json_mode_emits_parseable_payload(mod, monkeypatch, capsys):
    monkeypatch.setattr(
        mod,
        "_fetch_orphan_rows",
        lambda: [
            {"scraper_key": "typo_scraper", "show_count": 12},
        ],
    )

    rc = mod.main(["--json"])
    captured = capsys.readouterr()

    assert rc == 2
    payload = json.loads(captured.out)
    assert payload["orphans"][0]["scraper_key"] == "typo_scraper"
    assert payload["orphans"][0]["show_count"] == 12
    assert "shows.last_scraped_by value(s) missing" in captured.err
