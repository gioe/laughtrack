"""
Unit tests for bin/cleanup-stale-scrapers script.

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
from unittest.mock import MagicMock, patch

import pytest

_SCRAPER_ROOT = Path(__file__).resolve().parents[2]  # apps/scraper/
_BIN_PATH = _SCRAPER_ROOT / "bin" / "cleanup-stale-scrapers"


def _load_module() -> ModuleType:
    os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/testdb")
    loader = importlib.machinery.SourceFileLoader("bin_cleanup_stale_scrapers", str(_BIN_PATH))
    spec = importlib.util.spec_from_loader("bin_cleanup_stale_scrapers", loader)
    m = importlib.util.module_from_spec(spec)
    sys.modules["bin_cleanup_stale_scrapers"] = m
    loader.exec_module(m)
    return m


_mod = _load_module()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _conn_mock(scraper_keys=None):
    """Build a mock connection whose cursor returns scraper keys from the clubs table."""
    scraper_keys = scraper_keys or []
    cur = MagicMock()
    cur.fetchall.return_value = [(k,) for k in scraper_keys]
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    return conn, cur


def _make_venue_dir(parent: Path, name: str, key: str | None = None) -> Path:
    """Create a venue directory with a scraper.py under parent."""
    d = parent / name
    d.mkdir(parents=True, exist_ok=True)
    if key is not None:
        (d / "scraper.py").write_text(
            f'class MyScraper:\n    key = "{key}"\n    pass\n'
        )
    else:
        (d / "scraper.py").write_text("class MyScraper:\n    pass\n")
    return d


# ---------------------------------------------------------------------------
# extract_scraper_key
# ---------------------------------------------------------------------------

class TestExtractScraperKey:
    def test_double_quoted_key(self, tmp_path):
        f = tmp_path / "scraper.py"
        f.write_text('class S:\n    key = "comedy_store"\n')
        assert _mod.extract_scraper_key(f) == "comedy_store"

    def test_single_quoted_key(self, tmp_path):
        f = tmp_path / "scraper.py"
        f.write_text("class S:\n    key = 'laugh_factory'\n")
        assert _mod.extract_scraper_key(f) == "laugh_factory"

    def test_extra_whitespace_around_equals(self, tmp_path):
        f = tmp_path / "scraper.py"
        f.write_text('class S:\n    key  =  "the_stand"\n')
        assert _mod.extract_scraper_key(f) == "the_stand"

    def test_missing_key_returns_none(self, tmp_path):
        f = tmp_path / "scraper.py"
        f.write_text("class S:\n    name = 'something'\n")
        assert _mod.extract_scraper_key(f) is None

    def test_empty_file_returns_none(self, tmp_path):
        f = tmp_path / "scraper.py"
        f.write_text("")
        assert _mod.extract_scraper_key(f) is None

    def test_top_level_key_not_matched(self, tmp_path):
        """key = '...' at column 0 (not indented) should not match."""
        f = tmp_path / "scraper.py"
        f.write_text('key = "top_level"\nclass S:\n    pass\n')
        assert _mod.extract_scraper_key(f) is None

    def test_key_with_underscores_and_digits(self, tmp_path):
        f = tmp_path / "scraper.py"
        f.write_text('class S:\n    key = "venue_123_abc"\n')
        assert _mod.extract_scraper_key(f) == "venue_123_abc"


# ---------------------------------------------------------------------------
# scan_venue_scrapers
# ---------------------------------------------------------------------------

class TestScanVenueScrapers:
    def test_returns_key_to_dirname_mapping(self, tmp_path, monkeypatch):
        _make_venue_dir(tmp_path, "comedy_store", key="comedy_store")
        _make_venue_dir(tmp_path, "laugh_factory", key="laugh_factory")
        monkeypatch.setattr(_mod, "VENUES_DIR", tmp_path)

        result = _mod.scan_venue_scrapers()

        assert result == {"comedy_store": "comedy_store", "laugh_factory": "laugh_factory"}

    def test_skips_dirs_without_scraper_py(self, tmp_path, monkeypatch):
        _make_venue_dir(tmp_path, "good_venue", key="good_venue")
        (tmp_path / "no_scraper_dir").mkdir()  # no scraper.py
        monkeypatch.setattr(_mod, "VENUES_DIR", tmp_path)

        result = _mod.scan_venue_scrapers()

        assert list(result.keys()) == ["good_venue"]

    def test_skips_non_directories(self, tmp_path, monkeypatch):
        _make_venue_dir(tmp_path, "real_venue", key="real_venue")
        (tmp_path / "stray_file.py").write_text("# nothing")
        monkeypatch.setattr(_mod, "VENUES_DIR", tmp_path)

        result = _mod.scan_venue_scrapers()

        assert "stray_file.py" not in result

    def test_warns_and_skips_missing_key(self, tmp_path, monkeypatch, capsys):
        _make_venue_dir(tmp_path, "bad_venue", key=None)  # no key attr
        monkeypatch.setattr(_mod, "VENUES_DIR", tmp_path)

        result = _mod.scan_venue_scrapers()

        assert result == {}
        err = capsys.readouterr().err
        assert "no key found" in err.lower()
        assert "bad_venue" in err

    def test_warns_on_duplicate_key(self, tmp_path, monkeypatch, capsys):
        _make_venue_dir(tmp_path, "venue_a", key="shared_key")
        _make_venue_dir(tmp_path, "venue_b", key="shared_key")
        monkeypatch.setattr(_mod, "VENUES_DIR", tmp_path)

        result = _mod.scan_venue_scrapers()

        # First one (alphabetically) wins; second is skipped with a warning
        assert len(result) == 1
        assert "shared_key" in result
        err = capsys.readouterr().err
        assert "duplicate key" in err.lower()

    def test_empty_directory_returns_empty_dict(self, tmp_path, monkeypatch):
        monkeypatch.setattr(_mod, "VENUES_DIR", tmp_path)
        assert _mod.scan_venue_scrapers() == {}


# ---------------------------------------------------------------------------
# main() — empty-DB guard
# ---------------------------------------------------------------------------

class TestEmptyDbGuard:
    def test_exits_when_db_returns_no_keys(self, tmp_path, monkeypatch, capsys):
        _make_venue_dir(tmp_path, "some_venue", key="some_venue")
        monkeypatch.setattr(_mod, "VENUES_DIR", tmp_path)

        conn, _cur = _conn_mock(scraper_keys=[])
        with patch.object(_mod, "connect_with_retry", return_value=conn), \
             patch("sys.argv", ["cleanup-stale-scrapers"]):
            with pytest.raises(SystemExit) as exc_info:
                _mod.main()

        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "zero scraper keys" in err.lower()


# ---------------------------------------------------------------------------
# main() — orphan detection (report mode)
# ---------------------------------------------------------------------------

class TestOrphanDetection:
    def test_no_orphans_prints_clean_message(self, tmp_path, monkeypatch, capsys):
        _make_venue_dir(tmp_path, "comedy_store", key="comedy_store")
        monkeypatch.setattr(_mod, "VENUES_DIR", tmp_path)
        monkeypatch.setattr(_mod, "TESTS_VENUES_DIR", tmp_path / "tests")

        conn, _cur = _conn_mock(scraper_keys=["comedy_store"])
        with patch.object(_mod, "connect_with_retry", return_value=conn), \
             patch("sys.argv", ["cleanup-stale-scrapers"]):
            _mod.main()

        out = capsys.readouterr().out
        assert "no orphaned scrapers found" in out.lower()

    def test_orphan_listed_in_report(self, tmp_path, monkeypatch, capsys):
        _make_venue_dir(tmp_path, "active_venue", key="active_venue")
        _make_venue_dir(tmp_path, "stale_venue", key="stale_venue")
        monkeypatch.setattr(_mod, "VENUES_DIR", tmp_path)
        monkeypatch.setattr(_mod, "TESTS_VENUES_DIR", tmp_path / "tests")

        # DB only knows about active_venue; stale_venue is orphaned
        conn, _cur = _conn_mock(scraper_keys=["active_venue"])
        with patch.object(_mod, "connect_with_retry", return_value=conn), \
             patch("sys.argv", ["cleanup-stale-scrapers"]):
            _mod.main()

        out = capsys.readouterr().out
        assert "stale_venue" in out
        assert "Orphaned" in out
        assert "active_venue" not in out.split("Orphaned")[1]
        assert "--apply" in out

    def test_report_does_not_delete(self, tmp_path, monkeypatch):
        _make_venue_dir(tmp_path, "stale_venue", key="stale_venue")
        monkeypatch.setattr(_mod, "VENUES_DIR", tmp_path)
        monkeypatch.setattr(_mod, "TESTS_VENUES_DIR", tmp_path / "tests")

        conn, _cur = _conn_mock(scraper_keys=["other_key"])
        with patch.object(_mod, "connect_with_retry", return_value=conn), \
             patch.object(_mod.shutil, "rmtree") as mock_rm, \
             patch("sys.argv", ["cleanup-stale-scrapers"]):
            _mod.main()

        mock_rm.assert_not_called()


# ---------------------------------------------------------------------------
# main() — --apply deletion
# ---------------------------------------------------------------------------

class TestApplyDeletion:
    def test_deletes_impl_and_test_dirs(self, tmp_path, monkeypatch):
        impl_dir = tmp_path / "venues"
        test_dir = tmp_path / "tests"
        _make_venue_dir(impl_dir, "stale_venue", key="stale_venue")
        (test_dir / "stale_venue").mkdir(parents=True)
        monkeypatch.setattr(_mod, "VENUES_DIR", impl_dir)
        monkeypatch.setattr(_mod, "TESTS_VENUES_DIR", test_dir)
        monkeypatch.setattr(_mod, "SCRAPER_ROOT", tmp_path)

        conn, _cur = _conn_mock(scraper_keys=["other_key"])
        deleted_paths = []
        with patch.object(_mod, "connect_with_retry", return_value=conn), \
             patch.object(_mod.shutil, "rmtree", side_effect=lambda p: deleted_paths.append(p)), \
             patch("sys.argv", ["cleanup-stale-scrapers", "--apply"]):
            _mod.main()

        assert impl_dir / "stale_venue" in deleted_paths
        assert test_dir / "stale_venue" in deleted_paths

    def test_only_deletes_orphaned_not_active(self, tmp_path, monkeypatch):
        impl_dir = tmp_path / "venues"
        test_dir = tmp_path / "tests"
        _make_venue_dir(impl_dir, "active_venue", key="active_venue")
        _make_venue_dir(impl_dir, "stale_venue", key="stale_venue")
        monkeypatch.setattr(_mod, "VENUES_DIR", impl_dir)
        monkeypatch.setattr(_mod, "TESTS_VENUES_DIR", test_dir)
        monkeypatch.setattr(_mod, "SCRAPER_ROOT", tmp_path)

        conn, _cur = _conn_mock(scraper_keys=["active_venue"])
        deleted_paths = []
        with patch.object(_mod, "connect_with_retry", return_value=conn), \
             patch.object(_mod.shutil, "rmtree", side_effect=lambda p: deleted_paths.append(p)), \
             patch("sys.argv", ["cleanup-stale-scrapers", "--apply"]):
            _mod.main()

        assert impl_dir / "stale_venue" in deleted_paths
        assert impl_dir / "active_venue" not in deleted_paths

    def test_prints_done_message_with_count(self, tmp_path, monkeypatch, capsys):
        impl_dir = tmp_path / "venues"
        test_dir = tmp_path / "tests"
        _make_venue_dir(impl_dir, "stale_a", key="stale_a")
        _make_venue_dir(impl_dir, "stale_b", key="stale_b")
        monkeypatch.setattr(_mod, "VENUES_DIR", impl_dir)
        monkeypatch.setattr(_mod, "TESTS_VENUES_DIR", test_dir)
        monkeypatch.setattr(_mod, "SCRAPER_ROOT", tmp_path)

        conn, _cur = _conn_mock(scraper_keys=["other_key"])
        with patch.object(_mod, "connect_with_retry", return_value=conn), \
             patch.object(_mod.shutil, "rmtree"), \
             patch("sys.argv", ["cleanup-stale-scrapers", "--apply"]):
            _mod.main()

        out = capsys.readouterr().out
        assert "removed 2 orphaned" in out.lower()

    def test_skips_missing_test_dir_gracefully(self, tmp_path, monkeypatch, capsys):
        """--apply should not crash if the test directory doesn't exist."""
        impl_dir = tmp_path / "venues"
        test_dir = tmp_path / "tests"  # does not create the stale_venue subdir
        _make_venue_dir(impl_dir, "stale_venue", key="stale_venue")
        # test dir for stale_venue intentionally absent
        monkeypatch.setattr(_mod, "VENUES_DIR", impl_dir)
        monkeypatch.setattr(_mod, "TESTS_VENUES_DIR", test_dir)
        monkeypatch.setattr(_mod, "SCRAPER_ROOT", tmp_path)

        conn, _cur = _conn_mock(scraper_keys=["other_key"])
        deleted_paths = []
        with patch.object(_mod, "connect_with_retry", return_value=conn), \
             patch.object(_mod.shutil, "rmtree", side_effect=lambda p: deleted_paths.append(p)), \
             patch("sys.argv", ["cleanup-stale-scrapers", "--apply"]):
            _mod.main()

        # impl dir deleted; test dir not passed to rmtree (doesn't exist)
        assert impl_dir / "stale_venue" in deleted_paths
        assert test_dir / "stale_venue" not in deleted_paths
