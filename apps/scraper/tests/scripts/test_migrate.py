"""
Unit tests for bin/migrate script.

Loaded via importlib after pre-seeding DATABASE_URL so the top-level
sys.exit guard does not trigger. All DB access is mocked via patch.object —
no real database required.
"""

import importlib.machinery
import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, call, patch

import pytest

_SCRAPER_ROOT = Path(__file__).resolve().parents[2]  # apps/scraper/
_BIN_MIGRATE = _SCRAPER_ROOT / "bin" / "migrate"


def _load_module() -> ModuleType:
    os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/testdb")
    loader = importlib.machinery.SourceFileLoader("bin_migrate", str(_BIN_MIGRATE))
    spec = importlib.util.spec_from_loader("bin_migrate", loader)
    m = importlib.util.module_from_spec(spec)
    sys.modules["bin_migrate"] = m
    loader.exec_module(m)
    return m


_mod = _load_module()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _conn_mock(applied_names=None):
    """Build a mock connection whose cursor context manager returns a shared cursor.

    The cursor's fetchall() returns rows representing already-applied migrations,
    simulating a SELECT from migrations_log.
    """
    applied_names = applied_names or []
    cur = MagicMock()
    cur.fetchall.return_value = [(n,) for n in applied_names]
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    return conn, cur


# ---------------------------------------------------------------------------
# get_applied
# ---------------------------------------------------------------------------

class TestGetApplied:
    def test_returns_set_of_filenames(self):
        cur = MagicMock()
        cur.fetchall.return_value = [("0001_a.sql",), ("0002_b.sql",)]
        result = _mod.get_applied(cur)
        assert result == {"0001_a.sql", "0002_b.sql"}
        cur.execute.assert_called_once_with(
            "SELECT filename FROM migrations_log ORDER BY filename"
        )

    def test_empty_table(self):
        cur = MagicMock()
        cur.fetchall.return_value = []
        assert _mod.get_applied(cur) == set()


# ---------------------------------------------------------------------------
# get_pending
# ---------------------------------------------------------------------------

class TestGetPending:
    def test_excludes_already_applied(self, tmp_path, monkeypatch):
        (tmp_path / "0001_a.sql").write_text("SELECT 1")
        (tmp_path / "0002_b.sql").write_text("SELECT 2")
        monkeypatch.setattr(_mod, "MIGRATIONS_DIR", tmp_path)
        pending = _mod.get_pending({"0001_a.sql"})
        assert [p.name for p in pending] == ["0002_b.sql"]

    def test_returns_sorted_by_name(self, tmp_path, monkeypatch):
        (tmp_path / "c_003.sql").write_text("x")
        (tmp_path / "a_001.sql").write_text("x")
        (tmp_path / "b_002.sql").write_text("x")
        monkeypatch.setattr(_mod, "MIGRATIONS_DIR", tmp_path)
        pending = _mod.get_pending(set())
        assert [p.name for p in pending] == ["a_001.sql", "b_002.sql", "c_003.sql"]

    def test_all_applied_returns_empty(self, tmp_path, monkeypatch):
        (tmp_path / "0001_a.sql").write_text("x")
        monkeypatch.setattr(_mod, "MIGRATIONS_DIR", tmp_path)
        assert _mod.get_pending({"0001_a.sql"}) == []


# ---------------------------------------------------------------------------
# apply_migration
# ---------------------------------------------------------------------------

class TestApplyMigration:
    def test_executes_sql_and_inserts_log(self, tmp_path):
        f = tmp_path / "0001_create_table.sql"
        f.write_text("CREATE TABLE foo (id SERIAL);")
        cur = MagicMock()

        result = _mod.apply_migration(cur, f)

        assert result is True
        calls = cur.execute.call_args_list
        assert len(calls) == 2
        assert "CREATE TABLE foo" in calls[0].args[0]
        assert "INSERT INTO migrations_log" in calls[1].args[0]
        assert calls[1].args[1] == ("0001_create_table.sql",)

    def test_empty_file_skips_and_warns(self, tmp_path, capsys):
        f = tmp_path / "0001_empty.sql"
        f.write_text("  \n  ")
        cur = MagicMock()

        result = _mod.apply_migration(cur, f)

        assert result is False
        cur.execute.assert_not_called()
        err = capsys.readouterr().err
        assert "empty" in err.lower()
        assert "skipping" in err.lower()


# ---------------------------------------------------------------------------
# main() — end-to-end scenarios
# ---------------------------------------------------------------------------

class TestMainHappyPath:
    def test_applies_pending_migrations_in_order(self, tmp_path, monkeypatch, capsys):
        (tmp_path / "0001_a.sql").write_text("CREATE TABLE a (id INT);")
        (tmp_path / "0002_b.sql").write_text("CREATE TABLE b (id INT);")
        monkeypatch.setattr(_mod, "MIGRATIONS_DIR", tmp_path)

        conn, _cur = _conn_mock(applied_names=[])
        with patch.object(_mod, "connect_with_retry", return_value=conn), \
             patch("sys.argv", ["migrate"]):
            _mod.main()

        out = capsys.readouterr().out
        assert "0001_a.sql" in out
        assert "0002_b.sql" in out
        assert "Applied 2 migration" in out
        conn.commit.assert_called()
        conn.close.assert_called_once()


class TestMainDryRun:
    def test_prints_pending_without_migration_commits(self, tmp_path, monkeypatch, capsys):
        (tmp_path / "0001_a.sql").write_text("SELECT 1;")
        (tmp_path / "0002_b.sql").write_text("SELECT 2;")
        monkeypatch.setattr(_mod, "MIGRATIONS_DIR", tmp_path)

        conn, _cur = _conn_mock(applied_names=[])
        with patch.object(_mod, "connect_with_retry", return_value=conn), \
             patch("sys.argv", ["migrate", "--dry-run"]):
            _mod.main()

        out = capsys.readouterr().out
        assert "Dry run" in out
        assert "0001_a.sql" in out
        assert "0002_b.sql" in out
        # Only the initial log-table setup commit; no per-migration commits
        assert conn.commit.call_count == 1


class TestMainNoPending:
    def test_prints_up_to_date_exits_cleanly(self, tmp_path, monkeypatch, capsys):
        (tmp_path / "0001_a.sql").write_text("SELECT 1;")
        monkeypatch.setattr(_mod, "MIGRATIONS_DIR", tmp_path)

        conn, _cur = _conn_mock(applied_names=["0001_a.sql"])
        with patch.object(_mod, "connect_with_retry", return_value=conn), \
             patch("sys.argv", ["migrate"]):
            _mod.main()

        out = capsys.readouterr().out
        assert "up to date" in out.lower()
        conn.close.assert_called_once()


class TestMainRollbackOnError:
    def test_rolls_back_and_exits_1_on_migration_error(self, tmp_path, monkeypatch, capsys):
        (tmp_path / "0001_ok.sql").write_text("SELECT 1;")
        (tmp_path / "0002_bad.sql").write_text("INVALID SQL;")
        monkeypatch.setattr(_mod, "MIGRATIONS_DIR", tmp_path)

        conn, _cur = _conn_mock(applied_names=[])

        call_count = [0]

        def apply_side_effect(cur, path):
            call_count[0] += 1
            if call_count[0] > 1:
                raise Exception("syntax error at or near 'INVALID'")
            return True

        with patch.object(_mod, "connect_with_retry", return_value=conn), \
             patch.object(_mod, "apply_migration", side_effect=apply_side_effect), \
             patch("sys.argv", ["migrate"]):
            with pytest.raises(SystemExit) as exc_info:
                _mod.main()

        assert exc_info.value.code == 1
        conn.rollback.assert_called()
        conn.close.assert_called_once()

    def test_failed_migration_is_not_logged(self, tmp_path, monkeypatch, capsys):
        """The failed migration must not appear in migrations_log (no INSERT)."""
        (tmp_path / "0001_bad.sql").write_text("INVALID SQL;")
        monkeypatch.setattr(_mod, "MIGRATIONS_DIR", tmp_path)

        conn, cur = _conn_mock(applied_names=[])

        def apply_side_effect(cursor, path):
            raise Exception("query failed")

        with patch.object(_mod, "connect_with_retry", return_value=conn), \
             patch.object(_mod, "apply_migration", side_effect=apply_side_effect), \
             patch("sys.argv", ["migrate"]):
            with pytest.raises(SystemExit):
                _mod.main()

        insert_calls = [
            c for c in cur.execute.call_args_list
            if "INSERT INTO migrations_log" in str(c)
        ]
        assert insert_calls == []


class TestMainEmptyFileGuard:
    def test_empty_sql_file_is_not_logged_to_migrations_log(self, tmp_path, monkeypatch, capsys):
        (tmp_path / "0001_empty.sql").write_text("  \n  ")
        monkeypatch.setattr(_mod, "MIGRATIONS_DIR", tmp_path)

        conn, cur = _conn_mock(applied_names=[])
        with patch.object(_mod, "connect_with_retry", return_value=conn), \
             patch("sys.argv", ["migrate"]):
            _mod.main()

        insert_calls = [
            c for c in cur.execute.call_args_list
            if "INSERT INTO migrations_log" in str(c)
        ]
        assert insert_calls == [], "empty .sql file must not be logged to migrations_log"

        captured = capsys.readouterr()
        assert "empty" in captured.err.lower()
        assert "Applied 1 migration" not in captured.out, \
            "empty .sql file must not appear in 'Applied N migration(s)' output"
