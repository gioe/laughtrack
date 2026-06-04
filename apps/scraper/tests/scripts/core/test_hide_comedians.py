"""
Unit tests for scripts/core/hide_comedians.py.

Replaces the deleted test_remove_comedians.py suite (removed in TASK-2638
review-fix commit bf6a2d87c) with coverage of the new visible-flag path
per docs/comedian-visible-consolidation.md Decision 1.

The script is loaded via importlib so it does not have to be installed as
a package. DB functions (get_connection, get_transaction, execute_values)
are mocked with patch.object so tests never hit the real database.
"""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "scripts" / "core"
_SCRIPT_PATH = _SCRIPTS_DIR / "hide_comedians.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("hide_comedians", _SCRIPT_PATH)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_mod = _load_module()


def _conn_mock(rows=None, rowcount=0):
    """Return (mock_get_conn_fn, mock_cur) for patching get_connection/get_transaction."""
    mock_cur = MagicMock()
    mock_cur.fetchall.return_value = rows or []
    mock_cur.rowcount = rowcount
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__exit__.return_value = False
    # Two-deep context: with get_connection() as conn: with conn.cursor() as cur:
    mock_cur_cm = MagicMock()
    mock_cur_cm.__enter__.return_value = mock_cur
    mock_cur_cm.__exit__.return_value = False
    mock_conn.cursor.return_value = mock_cur_cm
    mock_get_conn = MagicMock()
    mock_get_conn.return_value.__enter__.return_value = mock_conn
    mock_get_conn.return_value.__exit__.return_value = False
    return mock_get_conn, mock_cur


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


class TestCheckDenyList:
    def test_returns_denied_subset(self):
        mock_get_conn, _ = _conn_mock(rows=[("John Doe",)])
        with patch.object(_mod, 'get_connection', mock_get_conn):
            result = _mod._check_deny_list(["John Doe", "Jane Smith"])
        assert result == {"John Doe"}

    def test_empty_deny_list(self):
        mock_get_conn, _ = _conn_mock(rows=[])
        with patch.object(_mod, 'get_connection', mock_get_conn):
            result = _mod._check_deny_list(["John Doe"])
        assert result == set()

    def test_all_denied(self):
        mock_get_conn, _ = _conn_mock(rows=[("A",), ("B",)])
        with patch.object(_mod, 'get_connection', mock_get_conn):
            result = _mod._check_deny_list(["A", "B"])
        assert result == {"A", "B"}


class TestLookupComedians:
    def test_returns_found_dict_with_visible_true(self):
        # visible=True (currently visible comedian) reported in the dict.
        mock_get_conn, _ = _conn_mock(rows=[("John Doe", "uuid-123", True, 5)])
        with patch.object(_mod, 'get_connection', mock_get_conn):
            result = _mod._lookup_comedians(["John Doe", "Jane Smith"])
        assert result == {
            "John Doe": {"uuid": "uuid-123", "visible": True, "lineup_count": 5}
        }

    def test_returns_visible_false_for_already_hidden(self):
        # visible=False rows must surface so _classify can route ALREADY HIDDEN.
        mock_get_conn, _ = _conn_mock(rows=[("Hidden Comic", "uuid-h", False, 0)])
        with patch.object(_mod, 'get_connection', mock_get_conn):
            result = _mod._lookup_comedians(["Hidden Comic"])
        assert result["Hidden Comic"]["visible"] is False

    def test_empty_names_skips_db(self):
        with patch.object(_mod, 'get_connection') as mock_gc:
            result = _mod._lookup_comedians([])
        assert result == {}
        mock_gc.assert_not_called()

    def test_not_found_excluded(self):
        mock_get_conn, _ = _conn_mock(rows=[])
        with patch.object(_mod, 'get_connection', mock_get_conn):
            result = _mod._lookup_comedians(["Jane Smith"])
        assert result == {}


class TestClassify:
    def test_already_denied_wins_over_found(self):
        # If a name is in the deny set, ALREADY DENIED is returned even if
        # the comedians row also exists — the deny check runs first.
        found = {"X": {"uuid": "u", "visible": True, "lineup_count": 0}}
        assert _mod._classify("X", {"X"}, found) == "ALREADY DENIED"

    def test_visible_when_found_and_visible_true(self):
        found = {"X": {"uuid": "u", "visible": True, "lineup_count": 3}}
        assert _mod._classify("X", set(), found) == "VISIBLE"

    def test_already_hidden_when_visible_false(self):
        found = {"X": {"uuid": "u", "visible": False, "lineup_count": 3}}
        assert _mod._classify("X", set(), found) == "ALREADY HIDDEN"

    def test_not_in_db_when_unmatched(self):
        assert _mod._classify("X", set(), {}) == "NOT IN DB"


class TestPrintStatusTable:
    def test_visible_row(self, capsys):
        _mod._print_status_table(
            ["John Doe"],
            set(),
            {"John Doe": {"uuid": "u", "visible": True, "lineup_count": 7}},
        )
        out = capsys.readouterr().out
        assert "VISIBLE" in out
        assert "7" in out

    def test_already_hidden_row(self, capsys):
        _mod._print_status_table(
            ["Hidden Comic"],
            set(),
            {"Hidden Comic": {"uuid": "u", "visible": False, "lineup_count": 0}},
        )
        out = capsys.readouterr().out
        assert "ALREADY HIDDEN" in out

    def test_not_in_db_row(self, capsys):
        _mod._print_status_table(["Jane Smith"], set(), {})
        out = capsys.readouterr().out
        assert "NOT IN DB" in out

    def test_already_denied_row(self, capsys):
        _mod._print_status_table(["John Doe"], {"John Doe"}, {})
        out = capsys.readouterr().out
        assert "ALREADY DENIED" in out


class TestConfirmHide:
    def test_visible_row_issues_update_visible_false_not_delete(self, capsys):
        """Criterion 8642: VISIBLE rows flip via UPDATE comedians SET visible=false (no DELETE)."""
        mock_get_txn, mock_cur = _conn_mock(rowcount=1)
        with patch.object(_mod, 'get_transaction', mock_get_txn), \
             patch.object(_mod, 'execute_values') as mock_ev:
            _mod._confirm_hide(
                ["John Doe"],
                set(),
                {"John Doe": {"uuid": "uuid-123", "visible": True, "lineup_count": 3}},
            )
        sql_calls = [str(c) for c in mock_cur.execute.call_args_list]
        assert any("UPDATE comedians" in c and "visible = false" in c for c in sql_calls), (
            f"expected UPDATE comedians SET visible=false; got {sql_calls!r}"
        )
        assert not any("DELETE" in c for c in sql_calls), (
            f"hide path must not DELETE; got {sql_calls!r}"
        )
        # No NOT IN DB names → execute_values must NOT fire.
        mock_ev.assert_not_called()

    def test_visible_row_binds_uuid_to_update(self):
        """UPDATE must target the comedian's uuid, not its name."""
        mock_get_txn, mock_cur = _conn_mock(rowcount=1)
        with patch.object(_mod, 'get_transaction', mock_get_txn), \
             patch.object(_mod, 'execute_values'):
            _mod._confirm_hide(
                ["John Doe"],
                set(),
                {"John Doe": {"uuid": "uuid-123", "visible": True, "lineup_count": 3}},
            )
        update_call = next(
            c for c in mock_cur.execute.call_args_list
            if "UPDATE comedians" in str(c)
        )
        assert update_call.args[1] == (["uuid-123"],)

    def test_not_in_db_inserts_into_deny_list_with_on_conflict_do_nothing(self):
        """Criterion 8643: NOT IN DB names hit comedian_deny_list with ON CONFLICT DO NOTHING."""
        mock_get_txn, mock_cur = _conn_mock(rowcount=0)
        with patch.object(_mod, 'get_transaction', mock_get_txn), \
             patch.object(_mod, 'execute_values') as mock_ev:
            _mod._confirm_hide(["Jane Smith"], set(), {})
        # No UPDATE — nothing matched in comedians.
        sql_calls = [str(c) for c in mock_cur.execute.call_args_list]
        assert not any("UPDATE comedians" in c for c in sql_calls)
        # Deny-list insert via execute_values with ON CONFLICT DO NOTHING.
        mock_ev.assert_called_once()
        sql_template = mock_ev.call_args[0][1]
        assert "INSERT INTO comedian_deny_list" in sql_template
        assert "ON CONFLICT (name) DO NOTHING" in sql_template
        deny_rows = mock_ev.call_args[0][2]
        assert ("Jane Smith", "manual_removal", "hide_comedians_script") in deny_rows

    def test_already_hidden_is_noop_no_update(self):
        """Criterion 8644 (part 1): ALREADY HIDDEN must skip UPDATE entirely."""
        mock_get_txn, mock_cur = _conn_mock(rowcount=0)
        with patch.object(_mod, 'get_transaction', mock_get_txn), \
             patch.object(_mod, 'execute_values') as mock_ev:
            _mod._confirm_hide(
                ["Hidden Comic"],
                set(),
                {"Hidden Comic": {"uuid": "uuid-h", "visible": False, "lineup_count": 0}},
            )
        sql_calls = [str(c) for c in mock_cur.execute.call_args_list]
        # No UPDATE and no INSERT — pure no-op on this name.
        assert not any("UPDATE" in c for c in sql_calls), (
            f"ALREADY HIDDEN must not re-flip; got {sql_calls!r}"
        )
        mock_ev.assert_not_called()

    def test_already_denied_is_noop_no_insert(self):
        """Criterion 8644 (part 2): ALREADY DENIED must skip the deny-list INSERT."""
        mock_get_txn, mock_cur = _conn_mock(rowcount=0)
        with patch.object(_mod, 'get_transaction', mock_get_txn), \
             patch.object(_mod, 'execute_values') as mock_ev:
            _mod._confirm_hide(["Spam Name"], {"Spam Name"}, {})
        sql_calls = [str(c) for c in mock_cur.execute.call_args_list]
        assert not any("UPDATE" in c for c in sql_calls)
        # Pre-existing deny-list entry must not be re-inserted.
        mock_ev.assert_not_called()

    def test_mixed_visible_and_not_in_db_runs_both_paths(self):
        """VISIBLE → UPDATE; NOT IN DB → INSERT — both fire in one call when mixed."""
        mock_get_txn, mock_cur = _conn_mock(rowcount=1)
        with patch.object(_mod, 'get_transaction', mock_get_txn), \
             patch.object(_mod, 'execute_values') as mock_ev:
            _mod._confirm_hide(
                ["Real Comic", "Garbage Name"],
                set(),
                {"Real Comic": {"uuid": "u-real", "visible": True, "lineup_count": 2}},
            )
        sql_calls = [str(c) for c in mock_cur.execute.call_args_list]
        assert any("UPDATE comedians" in c and "visible = false" in c for c in sql_calls)
        mock_ev.assert_called_once()
        deny_rows = mock_ev.call_args[0][2]
        assert any(r[0] == "Garbage Name" for r in deny_rows)
        # The visible row must NOT leak into the deny-list insert.
        assert not any(r[0] == "Real Comic" for r in deny_rows)


class TestMain:
    def test_errors_when_no_names_given(self, capsys):
        with patch.object(sys, 'argv', ['hide_comedians.py']):
            rc = _mod.main()
        assert rc == 1
        assert "Error" in capsys.readouterr().err

    def test_dry_run_prints_summary_and_skips_confirm(self, capsys):
        mock_get_conn_deny, _ = _conn_mock(rows=[])
        mock_get_conn_lookup, _ = _conn_mock(rows=[("John Doe", "u-1", True, 4)])

        # _check_deny_list and _lookup_comedians both call get_connection;
        # the deny-list call comes first, then the lookup call. Side_effect
        # rotates through both context managers in order.
        cms = [mock_get_conn_deny.return_value, mock_get_conn_lookup.return_value]
        mock_get_conn = MagicMock(side_effect=cms)

        with patch.object(sys, 'argv', ['hide_comedians.py', '--name', 'John Doe']), \
             patch.object(_mod, 'get_connection', mock_get_conn), \
             patch.object(_mod, 'get_transaction') as mock_get_txn:
            rc = _mod.main()
        assert rc == 0
        # Confirm path must not have fired (no transaction opened).
        mock_get_txn.assert_not_called()
        out = capsys.readouterr().out
        assert "Dry-run" in out
        assert "VISIBLE" in out
