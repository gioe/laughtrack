"""Unit tests for scripts/utils/visualize_metrics.py."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from scripts.utils.visualize_metrics import (
    _fmt_ts,
    _load_run,
    main,
    print_table,
)


# ---------------------------------------------------------------------------
# _fmt_ts
# ---------------------------------------------------------------------------

def test_fmt_ts_valid_iso():
    result = _fmt_ts("2026-03-19T14:30:00")
    assert result == "2026-03-19 14:30:00"


def test_fmt_ts_invalid_returns_original():
    result = _fmt_ts("not-a-date")
    assert result == "not-a-date"


def test_fmt_ts_none_returns_string():
    result = _fmt_ts(None)
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# _load_run
# ---------------------------------------------------------------------------

def test_load_run_valid_json(tmp_path: Path):
    f = tmp_path / "metrics_001.json"
    data = {"session": {"exported_at": "2026-01-01T00:00:00"}}
    f.write_text(json.dumps(data))
    assert _load_run(f) == data


def test_load_run_malformed_json(tmp_path: Path):
    f = tmp_path / "metrics_bad.json"
    f.write_text("{not valid json")
    assert _load_run(f) is None


def test_load_run_missing_file(tmp_path: Path):
    assert _load_run(tmp_path / "nonexistent.json") is None


# ---------------------------------------------------------------------------
# print_table — tabular output columns
# ---------------------------------------------------------------------------

def _make_run(exported_at="2026-03-19T10:00:00", clubs_passed=5, shows_scraped=20, errors=2):
    return {
        "session": {"exported_at": exported_at},
        "clubs": {"successful": clubs_passed},
        "shows": {"scraped": shows_scraped},
        "errors": {"total": errors},
    }


def test_print_table_contains_expected_columns(capsys):
    run = _make_run(clubs_passed=7, shows_scraped=42, errors=3)
    print_table([run])
    out = capsys.readouterr().out
    assert "2026-03-19 10:00:00" in out
    assert "7" in out
    assert "42" in out
    assert "3" in out


def test_print_table_header_labels(capsys):
    print_table([_make_run()])
    out = capsys.readouterr().out
    assert "Timestamp" in out
    assert "Clubs Passed" in out
    assert "Shows Scraped" in out
    assert "Errors" in out


def test_print_table_multiple_rows(capsys):
    runs = [_make_run(clubs_passed=i, shows_scraped=i * 10, errors=i) for i in range(3)]
    print_table(runs)
    out = capsys.readouterr().out
    # Three data rows plus header means at least 4 pipe-delimited rows
    lines_with_pipe = [l for l in out.splitlines() if "|" in l]
    assert len(lines_with_pipe) >= 4  # header + 3 data rows


# ---------------------------------------------------------------------------
# main — missing metrics directory
# ---------------------------------------------------------------------------

def test_main_missing_dir(tmp_path: Path, capsys, monkeypatch):
    missing = tmp_path / "no_such_dir"
    monkeypatch.setattr(sys, "argv", ["visualize_metrics", "--metrics-dir", str(missing)])
    main()
    out = capsys.readouterr().out
    assert "No metrics directory" in out or "no_such_dir" in out


# ---------------------------------------------------------------------------
# main — empty metrics directory
# ---------------------------------------------------------------------------

def test_main_empty_dir(tmp_path: Path, capsys, monkeypatch):
    empty = tmp_path / "metrics"
    empty.mkdir()
    monkeypatch.setattr(sys, "argv", ["visualize_metrics", "--metrics-dir", str(empty)])
    main()
    out = capsys.readouterr().out
    assert "No metrics files" in out


# ---------------------------------------------------------------------------
# main — --runs / -n flag limits output
# ---------------------------------------------------------------------------

def _write_metric_files(directory: Path, count: int) -> None:
    for i in range(count):
        data = {
            "session": {"exported_at": f"2026-01-{i+1:02d}T00:00:00"},
            "clubs": {"successful": i},
            "shows": {"scraped": i * 5},
            "errors": {"total": 0},
        }
        (directory / f"metrics_{i:04d}.json").write_text(json.dumps(data))


def _data_lines(out: str) -> list[str]:
    """Return table data rows (pipe-delimited, excluding header and dividers)."""
    return [l for l in out.splitlines() if l.strip().startswith("|") and "Timestamp" not in l]


def test_main_runs_flag_limits_rows(tmp_path: Path, capsys, monkeypatch):
    mdir = tmp_path / "metrics"
    mdir.mkdir()
    _write_metric_files(mdir, 5)

    monkeypatch.setattr(sys, "argv", ["visualize_metrics", "--metrics-dir", str(mdir), "-n", "2"])
    main()
    out = capsys.readouterr().out
    assert len(_data_lines(out)) == 2


def test_main_default_runs_all_when_fewer_than_default(tmp_path: Path, capsys, monkeypatch):
    mdir = tmp_path / "metrics"
    mdir.mkdir()
    _write_metric_files(mdir, 3)

    monkeypatch.setattr(sys, "argv", ["visualize_metrics", "--metrics-dir", str(mdir)])
    main()
    out = capsys.readouterr().out
    assert len(_data_lines(out)) == 3


# ---------------------------------------------------------------------------
# main — malformed JSON files are skipped gracefully
# ---------------------------------------------------------------------------

def test_main_skips_malformed_json(tmp_path: Path, capsys, monkeypatch):
    mdir = tmp_path / "metrics"
    mdir.mkdir()
    _write_metric_files(mdir, 2)
    (mdir / "metrics_9999.json").write_text("{broken json")

    monkeypatch.setattr(sys, "argv", ["visualize_metrics", "--metrics-dir", str(mdir)])
    main()
    out = capsys.readouterr().out
    # The 2 valid files should be rendered as data rows; malformed file skipped
    assert len(_data_lines(out)) == 2


def test_main_all_malformed_prints_no_readable_message(tmp_path: Path, capsys, monkeypatch):
    mdir = tmp_path / "metrics"
    mdir.mkdir()
    (mdir / "metrics_0000.json").write_text("{bad")
    (mdir / "metrics_0001.json").write_text("not json at all")

    monkeypatch.setattr(sys, "argv", ["visualize_metrics", "--metrics-dir", str(mdir)])
    main()
    out = capsys.readouterr().out
    assert "No readable metrics files" in out
