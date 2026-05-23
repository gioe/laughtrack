"""
Unit tests for the TASK-2402 Tixr suffixed-ticket cleanup script.
"""

import importlib.machinery
import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType

_SCRAPER_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = (
    _SCRAPER_ROOT
    / "scripts"
    / "core"
    / "cleanup_stale_tixr_suffixed_ticket_rows_2026_05_22.py"
)


def _load_module() -> ModuleType:
    loader = importlib.machinery.SourceFileLoader(
        "cleanup_stale_tixr_suffixed_ticket_rows_2026_05_22",
        str(_SCRIPT_PATH),
    )
    spec = importlib.util.spec_from_loader(
        "cleanup_stale_tixr_suffixed_ticket_rows_2026_05_22",
        loader,
    )
    m = importlib.util.module_from_spec(spec)
    sys.modules["cleanup_stale_tixr_suffixed_ticket_rows_2026_05_22"] = m
    loader.exec_module(m)
    return m


def test_task_2402_suffix_regex_matches_tixr_day_time_tiers():
    mod = _load_module()

    pattern = re.compile(mod.PERFORMANCE_TIME_SUFFIX_SQL_RE, re.IGNORECASE)

    assert pattern.search("General Admission - Friday 7:30pm")
    assert pattern.search("Golden Circle – Sat 9pm")
    assert pattern.search("VIP Seating — Thursday 10 PM")
    assert not pattern.search("General Admission")
    assert not pattern.search("Friday Night General Admission")
    assert not pattern.search("General Admission - Friday 13pm")
    assert not pattern.search("General Admission - Friday 7:99pm")


def test_task_2402_delete_sql_requires_same_show_bare_replacement():
    mod = _load_module()

    assert "WHERE bare.show_id = t.show_id" in mod.DELETE_SQL
    assert "bare.type = regexp_replace(t.type" in mod.DELETE_SQL
    assert "suffixed.has_bare_replacement" in mod.DELETE_SQL
    assert "ILIKE '%%tixr.com%%'" in mod.TIXR_TICKET_SCOPE_SQL
    assert mod.TARGET_CLUB_ID == 171
