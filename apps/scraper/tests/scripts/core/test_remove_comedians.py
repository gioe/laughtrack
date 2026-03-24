"""
Unit tests for scripts/core/remove_comedians.py.

The script is loaded via importlib to avoid installing it as a package.
DB functions (get_connection, get_transaction, execute_values) are mocked
with patch.object so tests never hit the real database.
"""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch, call

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "scripts" / "core"
_SCRIPT_PATH = _SCRIPTS_DIR / "remove_comedians.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("remove_comedians", _SCRIPT_PATH)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_mod = _load_module()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _conn_mock(rows=None, rowcount=0):
    """Return (mock_get_conn_fn, mock_cur) for patching get_connection/get_transaction."""
    mock_cur = MagicMock()
    mock_cur.fetchall.return_value = rows or []
    mock_cur.rowcount = rowcount
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_get_conn = MagicMock()
    mock_get_conn.return_value.__enter__.return_value = mock_conn
    return mock_get_conn, mock_cur


# ---------------------------------------------------------------------------
# _load_names_file
# ---------------------------------------------------------------------------

class TestLoadNamesFile:
    def test_basic_lines(self, tmp_path):
        f = tmp_path / "names.txt"
        f.write_text("John Doe\nJane Smith\n")
        assert _mod._load_names_file(str(f)) == ["John Doe", "Jane Smith"]

    def test_ignores_blank_lines(self, tmp_path):
        f = tmp_path / "names.txt"
        f.write_text("\nJohn Doe\n\n")
        assert _mod._load_names_file(str(f)) == ["John Doe"]

    def test_ignores_hash_comments(self, tmp_path):
        f = tmp_path / "names.txt"
        f.write_text("# comment\nJohn Doe\n# another\nJane Smith\n")
        assert _mod._load_names_file(str(f)) == ["John Doe", "Jane Smith"]

    def test_empty_file(self, tmp_path):
        f = tmp_path / "names.txt"
        f.write_text("")
        assert _mod._load_names_file(str(f)) == []

    def test_strips_whitespace(self, tmp_path):
        f = tmp_path / "names.txt"
        f.write_text("  John Doe  \n")
        assert _mod._load_names_file(str(f)) == ["John Doe"]


# ---------------------------------------------------------------------------
# _check_deny_list
# ---------------------------------------------------------------------------

class TestCheckDenyList:
    def test_returns_denied_subset(self):
        mock_get_conn, mock_cur = _conn_mock(rows=[("John Doe",)])
        with patch.object(_mod, 'get_connection', mock_get_conn):
            result = _mod._check_deny_list(["John Doe", "Jane Smith"])
        assert result == {"John Doe"}

    def test_empty_deny_list(self):
        mock_get_conn, mock_cur = _conn_mock(rows=[])
        with patch.object(_mod, 'get_connection', mock_get_conn):
            result = _mod._check_deny_list(["John Doe"])
        assert result == set()

    def test_all_denied(self):
        mock_get_conn, mock_cur = _conn_mock(rows=[("A",), ("B",)])
        with patch.object(_mod, 'get_connection', mock_get_conn):
            result = _mod._check_deny_list(["A", "B"])
        assert result == {"A", "B"}


# ---------------------------------------------------------------------------
# _lookup_comedians
# ---------------------------------------------------------------------------

class TestLookupComedians:
    def test_returns_found_dict(self):
        mock_get_conn, mock_cur = _conn_mock(rows=[("John Doe", "uuid-123", 5)])
        with patch.object(_mod, 'get_connection', mock_get_conn):
            result = _mod._lookup_comedians(["John Doe", "Jane Smith"])
        assert result == {"John Doe": {"uuid": "uuid-123", "lineup_count": 5}}

    def test_empty_names_skips_db(self):
        # Should return immediately without querying the DB.
        with patch.object(_mod, 'get_connection') as mock_gc:
            result = _mod._lookup_comedians([])
        assert result == {}
        mock_gc.assert_not_called()

    def test_not_found_excluded(self):
        mock_get_conn, mock_cur = _conn_mock(rows=[])
        with patch.object(_mod, 'get_connection', mock_get_conn):
            result = _mod._lookup_comedians(["Jane Smith"])
        assert result == {}

    def test_zero_lineup_count(self):
        mock_get_conn, mock_cur = _conn_mock(rows=[("Solo Act", "uuid-999", 0)])
        with patch.object(_mod, 'get_connection', mock_get_conn):
            result = _mod._lookup_comedians(["Solo Act"])
        assert result["Solo Act"]["lineup_count"] == 0


# ---------------------------------------------------------------------------
# _print_status_table
# ---------------------------------------------------------------------------

class TestPrintStatusTable:
    def test_found_shows_lineup_count(self, capsys):
        _mod._print_status_table(
            ["John Doe"],
            set(),
            {"John Doe": {"uuid": "u1", "lineup_count": 7}},
        )
        out = capsys.readouterr().out
        assert "FOUND" in out
        assert "7" in out

    def test_not_in_db_status(self, capsys):
        _mod._print_status_table(["Jane Smith"], set(), {})
        out = capsys.readouterr().out
        assert "NOT IN DB" in out

    def test_already_denied_status(self, capsys):
        _mod._print_status_table(["John Doe"], {"John Doe"}, {})
        out = capsys.readouterr().out
        assert "ALREADY DENIED" in out

    def test_mixed_statuses(self, capsys):
        _mod._print_status_table(
            ["Found One", "Missing One", "Denied One"],
            {"Denied One"},
            {"Found One": {"uuid": "u1", "lineup_count": 3}},
        )
        out = capsys.readouterr().out
        assert "FOUND" in out
        assert "NOT IN DB" in out
        assert "ALREADY DENIED" in out


# ---------------------------------------------------------------------------
# _confirm_delete
# ---------------------------------------------------------------------------

class TestConfirmDelete:
    def test_deletes_found_comedians(self, capsys):
        mock_get_txn, mock_cur = _conn_mock(rowcount=2)
        with patch.object(_mod, 'get_transaction', mock_get_txn), \
             patch.object(_mod, 'execute_values') as mock_ev:
            _mod._confirm_delete(
                ["John Doe"],
                set(),
                {"John Doe": {"uuid": "uuid-123", "lineup_count": 3}},
            )
        sql_calls = [str(c) for c in mock_cur.execute.call_args_list]
        assert any("lineup_items" in c for c in sql_calls)
        assert any("comedians" in c for c in sql_calls)
        mock_ev.assert_called_once()

    def test_not_in_db_still_added_to_deny_list(self, capsys):
        mock_get_txn, mock_cur = _conn_mock(rowcount=0)
        with patch.object(_mod, 'get_transaction', mock_get_txn), \
             patch.object(_mod, 'execute_values') as mock_ev:
            _mod._confirm_delete(["Jane Smith"], set(), {})
        # No DELETE statements — nothing found in DB.
        sql_calls = [str(c) for c in mock_cur.execute.call_args_list]
        assert not any("DELETE" in c for c in sql_calls)
        # Deny list insert should still happen.
        mock_ev.assert_called_once()
        deny_rows = mock_ev.call_args[0][2]
        assert any(r[0] == "Jane Smith" for r in deny_rows)

    def test_already_denied_skipped(self):
        mock_get_txn, mock_cur = _conn_mock(rowcount=0)
        with patch.object(_mod, 'get_transaction', mock_get_txn), \
             patch.object(_mod, 'execute_values') as mock_ev:
            _mod._confirm_delete(["John Doe"], {"John Doe"}, {})
        # names_to_process is empty — no deny list insert.
        mock_ev.assert_not_called()

    def test_deny_rows_contain_all_non_denied_names(self):
        mock_get_txn, mock_cur = _conn_mock(rowcount=1)
        with patch.object(_mod, 'get_transaction', mock_get_txn), \
             patch.object(_mod, 'execute_values') as mock_ev:
            _mod._confirm_delete(
                ["Found One", "Missing One", "Denied One"],
                {"Denied One"},
                {"Found One": {"uuid": "u1", "lineup_count": 2}},
            )
        deny_rows = mock_ev.call_args[0][2]
        names_in_deny = [r[0] for r in deny_rows]
        assert "Found One" in names_in_deny
        assert "Missing One" in names_in_deny
        assert "Denied One" not in names_in_deny


# ---------------------------------------------------------------------------
# main() — integration
# ---------------------------------------------------------------------------

class TestMain:
    def test_no_names_exits_1(self, capsys):
        with patch('sys.argv', ['script']):
            result = _mod.main()
        assert result == 1

    def test_all_already_denied_exits_0(self, capsys):
        with patch('sys.argv', ['script', '--name', 'John Doe']), \
             patch.object(_mod, '_check_deny_list', return_value={"John Doe"}):
            result = _mod.main()
        assert result == 0
        out = capsys.readouterr().out
        assert "already in the deny list" in out

    def test_dry_run_does_not_call_confirm(self, capsys):
        with patch('sys.argv', ['script', '--name', 'John Doe']), \
             patch.object(_mod, '_check_deny_list', return_value=set()), \
             patch.object(_mod, '_lookup_comedians',
                          return_value={"John Doe": {"uuid": "u1", "lineup_count": 2}}), \
             patch.object(_mod, '_print_status_table'), \
             patch.object(_mod, '_confirm_delete') as mock_delete:
            result = _mod.main()
        assert result == 0
        mock_delete.assert_not_called()

    def test_confirm_calls_confirm_delete(self):
        with patch('sys.argv', ['script', '--name', 'John Doe', '--confirm']), \
             patch.object(_mod, '_check_deny_list', return_value=set()), \
             patch.object(_mod, '_lookup_comedians',
                          return_value={"John Doe": {"uuid": "u1", "lineup_count": 2}}), \
             patch.object(_mod, '_print_status_table'), \
             patch.object(_mod, '_confirm_delete') as mock_delete:
            result = _mod.main()
        assert result == 0
        mock_delete.assert_called_once()

    def test_names_file_parsed(self, tmp_path):
        f = tmp_path / "names.txt"
        f.write_text("John Doe\n# comment\n\nJane Smith\n")
        with patch('sys.argv', ['script', '--names-file', str(f)]), \
             patch.object(_mod, '_check_deny_list', return_value=set()), \
             patch.object(_mod, '_lookup_comedians', return_value={}), \
             patch.object(_mod, '_print_status_table') as mock_table:
            _mod.main()
        names_arg = mock_table.call_args[0][0]
        assert "John Doe" in names_arg
        assert "Jane Smith" in names_arg

    def test_deduplicates_names(self):
        with patch('sys.argv', ['script', '--name', 'John Doe', '--name', 'John Doe']), \
             patch.object(_mod, '_check_deny_list', return_value=set()) as mock_check, \
             patch.object(_mod, '_lookup_comedians', return_value={}), \
             patch.object(_mod, '_print_status_table'):
            _mod.main()
        # Only one unique name passed to deny-list check.
        names_passed = mock_check.call_args[0][0]
        assert names_passed.count("John Doe") == 1

    def test_preflight_uses_all_names_before_lookup(self):
        """_check_deny_list is called before _lookup_comedians (criteria 2057)."""
        call_order = []
        with patch('sys.argv', ['script', '--name', 'John Doe']), \
             patch.object(_mod, '_check_deny_list',
                          side_effect=lambda n: call_order.append('deny') or set()) as mock_check, \
             patch.object(_mod, '_lookup_comedians',
                          side_effect=lambda n: call_order.append('lookup') or {}) as mock_lookup, \
             patch.object(_mod, '_print_status_table'):
            _mod.main()
        assert call_order.index('deny') < call_order.index('lookup')
