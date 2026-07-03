import importlib.machinery
import importlib.util
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

_SCRAPER_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _SCRAPER_ROOT / "bin" / "neon-cost-diagnostics"


def _load_module() -> ModuleType:
    loader = importlib.machinery.SourceFileLoader("neon_cost_diagnostics", str(_SCRIPT))
    spec = importlib.util.spec_from_loader("neon_cost_diagnostics", loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


_mod = _load_module()


def test_diagnostic_sections_cover_rows_calls_and_execution_time():
    section_names = [name for name, _sql in _mod.SECTION_QUERIES]

    assert section_names == [
        "top_total_rows",
        "top_avg_rows_per_call",
        "top_calls",
        "top_total_exec_time",
    ]
    assert all("pg_stat_statements" in sql for _name, sql in _mod.SECTION_QUERIES)
    assert any("ORDER BY rows DESC" in sql for _name, sql in _mod.SECTION_QUERIES)
    assert any("ORDER BY avg_rows_per_call DESC" in sql for _name, sql in _mod.SECTION_QUERIES)
    assert any("ORDER BY calls DESC" in sql for _name, sql in _mod.SECTION_QUERIES)
    assert any("ORDER BY total_exec_time DESC" in sql for _name, sql in _mod.SECTION_QUERIES)


def test_run_diagnostics_prints_reset_note_and_truncates_query_text():
    long_query = "SELECT " + ("x" * 100)
    rows_by_execute = [
        [(1,)],
        [(long_query, 3, 30, 10)],
        [(long_query, 3, 30, 10)],
        [(long_query, 3, 30, 10)],
        [(long_query, 3, 30, 10, 5)],
    ]
    cur = MagicMock()
    cur.description = [
        ("query",),
        ("calls",),
        ("total_rows",),
        ("avg_rows_per_call",),
    ]

    def execute_side_effect(_sql, _params=()):
        cur.fetchall.return_value = rows_by_execute.pop(0)
        if not rows_by_execute:
            cur.description = [
                ("query",),
                ("calls",),
                ("total_rows",),
                ("total_exec_time_ms",),
                ("mean_exec_time_ms",),
            ]

    cur.execute.side_effect = execute_side_effect
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur

    result = _mod.run_diagnostics(conn, limit=1, max_query_chars=40)

    assert "stats can reset when compute restarts or scales to zero" in result["note"]
    assert set(result["sections"]) == set(name for name, _sql in _mod.SECTION_QUERIES)
    assert result["sections"]["top_total_rows"][0]["query"].endswith("...")
    assert len(result["sections"]["top_total_rows"][0]["query"]) == 40
    assert all(call.args[1] == (1,) for call in cur.execute.call_args_list[1:])
