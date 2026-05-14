from __future__ import annotations

import contextlib
import csv
import json
import sys
from pathlib import Path
from typing import Any

import pytest

_repo_root = Path(__file__).resolve().parents[3]
_src_path = _repo_root / "src"
for _p in (str(_src_path), str(_repo_root)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from scripts.core import review_podcast_candidates as mod  # noqa: E402


def _audit_row(
    *,
    comedian_id: int,
    source_episode_id: str,
    source_feed_id: str,
    podcast_name: str,
    episode_title: str,
    feed_url: str,
    confidence: float,
    matched_terms: list[str],
    extra_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    evidence = {
        "search_term": " ".join(matched_terms) or "comedian",
        "matched_terms": matched_terms,
        "episode_title": episode_title,
        "podcast_name": podcast_name,
        "source_feed_id": source_feed_id,
        "source_feed_url": feed_url,
        "feed_url": feed_url,
        "metadata_source": "rss",
    }
    if extra_evidence:
        evidence.update(extra_evidence)
    return {
        "comedian_id": comedian_id,
        "source": "podcast_index",
        "source_episode_id": source_episode_id,
        "podcast_name": podcast_name,
        "episode_title": episode_title,
        "release_date": "2024-01-03T10:00:00+00:00",
        "episode_url": f"https://podcast.example/{source_episode_id}",
        "match_confidence": confidence,
        "match_evidence": evidence,
    }


def _write_audit(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")


class _FakeCursor:
    def __init__(self, conn: "_FakeConn") -> None:
        self._conn = conn
        self._last_result: list[tuple[Any, ...]] = []

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, *_exc: Any) -> bool:
        return False

    def execute(self, sql: str, params: Any = None) -> None:
        self._conn._execute_count += 1
        if (
            self._conn._raise_on_execute_count is not None
            and self._conn._execute_count == self._conn._raise_on_execute_count
        ):
            raise RuntimeError(
                f"injected failure on execute #{self._conn._execute_count}"
            )
        self._conn.executed.append((sql, params))
        normalized = " ".join(sql.split())
        if normalized.startswith("SELECT comedian_id, source_feed_id, LOWER(review_status)"):
            wanted_ids = set(params[0]) if params else set()
            self._last_result = [
                (cid, feed, status)
                for (cid, feed), status in self._conn.identity_links.items()
                if cid in wanted_ids
            ]
        elif normalized.startswith("SELECT id, name FROM comedians"):
            wanted_ids = set(params[0]) if params else set()
            self._last_result = [
                (cid, name) for cid, name in self._conn.comedian_names.items() if cid in wanted_ids
            ]
        elif normalized.startswith("INSERT INTO comedian_podcast_identity_links"):
            (
                comedian_id,
                _source,
                feed_id,
                feed_url,
                feed_name,
                status,
                evidence_json,
                reviewer,
            ) = params
            self._conn.identity_links[(int(comedian_id), str(feed_id))] = str(status)
            self._conn.identity_link_writes.append(
                {
                    "comedian_id": int(comedian_id),
                    "source_feed_id": str(feed_id),
                    "source_feed_url": feed_url,
                    "source_feed_name": feed_name,
                    "review_status": str(status),
                    "review_evidence": json.loads(evidence_json),
                    "reviewed_by": reviewer,
                }
            )
        else:
            self._last_result = []

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self._last_result


class _FakeConn:
    def __init__(
        self,
        *,
        comedian_names: dict[int, str] | None = None,
        identity_links: dict[tuple[int, str], str] | None = None,
        raise_on_execute_count: int | None = None,
    ) -> None:
        self.comedian_names = comedian_names or {}
        self.identity_links = dict(identity_links or {})
        self.identity_link_writes: list[dict[str, Any]] = []
        self.appearance_writes: list[tuple[Any, ...]] = []
        self.executed: list[tuple[str, Any]] = []
        self.commits = 0
        self.rollbacks = 0
        self._execute_count = 0
        self._raise_on_execute_count = raise_on_execute_count

    def __enter__(self) -> "_FakeConn":
        return self

    def __exit__(self, *_exc: Any) -> bool:
        return False

    def cursor(self) -> _FakeCursor:
        return _FakeCursor(self)

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


def _fake_execute_values(cur: _FakeCursor, sql: str, values: list[tuple[Any, ...]], template: str) -> None:
    cur._conn.appearance_writes.extend(values)


def _install_fakes(monkeypatch, conn: _FakeConn) -> None:
    monkeypatch.setattr(mod, "get_connection", lambda: conn)

    @contextlib.contextmanager
    def fake_transaction():
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise
        else:
            conn.commit()

    monkeypatch.setattr(mod, "get_transaction", fake_transaction)
    monkeypatch.setattr(mod, "execute_values", _fake_execute_values)


def test_export_writes_full_column_csv_with_blank_decision_fields(monkeypatch, tmp_path):
    audit_path = tmp_path / "audit.jsonl"
    output_path = tmp_path / "review.csv"
    _write_audit(
        audit_path,
        [
            _audit_row(
                comedian_id=12,
                source_episode_id="ep-1",
                source_feed_id="456",
                podcast_name="Comedy Talk",
                episode_title="Ari Shaffir on Tour",
                feed_url="https://feeds.example/comedy-talk.xml",
                confidence=0.5,
                matched_terms=["ari", "shaffir"],
                extra_evidence={"author": "Comedy Talk Network"},
            ),
            _audit_row(
                comedian_id=12,
                source_episode_id="ep-2",
                source_feed_id="456",
                podcast_name="Comedy Talk",
                episode_title="Best of Episode",
                feed_url="https://feeds.example/comedy-talk.xml",
                confidence=0.3,
                matched_terms=["ari"],
            ),
            _audit_row(
                comedian_id=24,
                source_episode_id="ep-9",
                source_feed_id="789",
                podcast_name="Random Show",
                episode_title="Wrong Person",
                feed_url="https://feeds.example/random.xml",
                confidence=0.2,
                matched_terms=[],
            ),
        ],
    )
    conn = _FakeConn(comedian_names={12: "Ari Shaffir", 24: "Other Comedian"})
    _install_fakes(monkeypatch, conn)

    written = mod._export(audit_path=audit_path, output_path=output_path)

    assert written == 2
    with output_path.open() as fh:
        rows = list(csv.DictReader(fh))
    assert rows[0]["candidate_id"] == "12:456"
    assert rows[0]["comedian_id"] == "12"
    assert rows[0]["comedian_name"] == "Ari Shaffir"
    assert rows[0]["matched_name"] == "Ari Shaffir on Tour"
    assert rows[0]["normalized_match"] == "ari, shaffir"
    assert rows[0]["feed_id"] == "456"
    assert rows[0]["podcast_title"] == "Comedy Talk"
    assert rows[0]["author"] == "Comedy Talk Network"
    assert rows[0]["feed_url"] == "https://feeds.example/comedy-talk.xml"
    assert rows[0]["confidence"] == "0.50"
    assert rows[0]["current_status"] == "pending"
    assert rows[0]["decision"] == ""
    assert rows[0]["review_reason"] == ""
    evidence = json.loads(rows[0]["evidence"])
    assert evidence["source_feed_id"] == "456"
    assert evidence["matched_terms"] == ["ari", "shaffir"]
    # Higher confidence candidate sorted first
    assert rows[1]["candidate_id"] == "24:789"
    assert set(rows[0].keys()) == set(mod._FULL_EXPORT_COLUMNS)


def test_export_excludes_already_linked_pairs(monkeypatch, tmp_path):
    audit_path = tmp_path / "audit.jsonl"
    output_path = tmp_path / "review.csv"
    _write_audit(
        audit_path,
        [
            _audit_row(
                comedian_id=12,
                source_episode_id="ep-1",
                source_feed_id="456",
                podcast_name="Already Decided",
                episode_title="Episode",
                feed_url="https://feeds.example/decided.xml",
                confidence=0.4,
                matched_terms=["ari"],
            ),
            _audit_row(
                comedian_id=14,
                source_episode_id="ep-2",
                source_feed_id="999",
                podcast_name="Fresh Candidate",
                episode_title="Episode",
                feed_url="https://feeds.example/fresh.xml",
                confidence=0.4,
                matched_terms=["ari"],
            ),
        ],
    )
    conn = _FakeConn(
        comedian_names={12: "Ari Shaffir", 14: "Mark Normand"},
        identity_links={(12, "456"): "rejected"},
    )
    _install_fakes(monkeypatch, conn)

    written = mod._export(audit_path=audit_path, output_path=output_path)

    assert written == 1
    with output_path.open() as fh:
        rows = list(csv.DictReader(fh))
    assert [r["candidate_id"] for r in rows] == ["14:999"]


def test_export_with_include_resolved_shows_decided_candidates(monkeypatch, tmp_path):
    audit_path = tmp_path / "audit.jsonl"
    output_path = tmp_path / "review.csv"
    _write_audit(
        audit_path,
        [
            _audit_row(
                comedian_id=12,
                source_episode_id="ep-1",
                source_feed_id="456",
                podcast_name="Already Decided",
                episode_title="Episode",
                feed_url="https://feeds.example/decided.xml",
                confidence=0.4,
                matched_terms=["ari"],
            )
        ],
    )
    conn = _FakeConn(
        comedian_names={12: "Ari Shaffir"},
        identity_links={(12, "456"): "verified"},
    )
    _install_fakes(monkeypatch, conn)

    written = mod._export(
        audit_path=audit_path, output_path=output_path, include_resolved=True
    )

    assert written == 1
    with output_path.open() as fh:
        rows = list(csv.DictReader(fh))
    assert rows[0]["current_status"] == "verified"


def _seed_two_candidates(tmp_path: Path) -> Path:
    audit_path = tmp_path / "audit.jsonl"
    _write_audit(
        audit_path,
        [
            _audit_row(
                comedian_id=12,
                source_episode_id="ep-1",
                source_feed_id="456",
                podcast_name="Comedy Talk",
                episode_title="Ari Shaffir on Tour",
                feed_url="https://feeds.example/comedy-talk.xml",
                confidence=0.5,
                matched_terms=["ari", "shaffir"],
            ),
            _audit_row(
                comedian_id=12,
                source_episode_id="ep-2",
                source_feed_id="456",
                podcast_name="Comedy Talk",
                episode_title="Second Episode",
                feed_url="https://feeds.example/comedy-talk.xml",
                confidence=0.4,
                matched_terms=["ari"],
            ),
            _audit_row(
                comedian_id=14,
                source_episode_id="ep-9",
                source_feed_id="999",
                podcast_name="Wrong Match",
                episode_title="Not You",
                feed_url="https://feeds.example/wrong.xml",
                confidence=0.2,
                matched_terms=[],
            ),
        ],
    )
    return audit_path


def _write_decisions(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in columns})


def test_apply_accepts_full_export_csv_and_writes_verified_identity_link(
    monkeypatch, tmp_path
):
    audit_path = _seed_two_candidates(tmp_path)
    review_path = tmp_path / "review.csv"
    _write_decisions(
        review_path,
        mod._FULL_EXPORT_COLUMNS,
        [
            {
                "candidate_id": "12:456",
                "decision": "accept",
                "review_reason": "looks legit",
            },
            {"candidate_id": "14:999", "decision": "reject"},
        ],
    )
    conn = _FakeConn(comedian_names={12: "Ari Shaffir", 14: "Mark Normand"})
    _install_fakes(monkeypatch, conn)

    summary, errors = mod._apply(
        decisions_path=review_path,
        audit_path=audit_path,
        dry_run=False,
        force=False,
        reviewer="matt",
    )

    assert errors == []
    assert summary.accepted == 1
    assert summary.rejected == 1
    assert summary.ignored == 0
    assert summary.skipped == 0
    assert summary.errored == 0
    assert summary.appearances_written == 2  # both Ari Shaffir episodes
    # Identity links written for both candidates
    statuses = {(w["comedian_id"], w["source_feed_id"]): w["review_status"] for w in conn.identity_link_writes}
    assert statuses == {(12, "456"): "verified", (14, "999"): "rejected"}
    # Reviewer captured
    reviewers = {w["reviewed_by"] for w in conn.identity_link_writes}
    assert reviewers == {"matt"}
    # Appearance rows materialized only for accepted candidate
    assert len(conn.appearance_writes) == 2
    assert {row[2] for row in conn.appearance_writes} == {"ep-1", "ep-2"}
    assert conn.commits == 1
    # review_reason flows into evidence for the accepted candidate
    accepted_write = next(w for w in conn.identity_link_writes if w["comedian_id"] == 12)
    assert accepted_write["review_evidence"]["review_reason"] == "looks legit"


def test_apply_accepts_compact_decision_csv(monkeypatch, tmp_path):
    audit_path = _seed_two_candidates(tmp_path)
    review_path = tmp_path / "compact.csv"
    _write_decisions(
        review_path,
        ["candidate_id", "decision"],
        [
            {"candidate_id": "12:456", "decision": "accept"},
            {"candidate_id": "14:999", "decision": "ignore"},
        ],
    )
    conn = _FakeConn(comedian_names={12: "Ari Shaffir", 14: "Mark Normand"})
    _install_fakes(monkeypatch, conn)

    summary, errors = mod._apply(
        decisions_path=review_path,
        audit_path=audit_path,
        dry_run=False,
        force=False,
        reviewer="matt",
    )

    assert errors == []
    assert summary.accepted == 1
    assert summary.ignored == 1
    statuses = {(w["comedian_id"], w["source_feed_id"]): w["review_status"] for w in conn.identity_link_writes}
    assert statuses == {(12, "456"): "verified", (14, "999"): "ambiguous"}


def test_apply_ignores_blank_decisions(monkeypatch, tmp_path):
    audit_path = _seed_two_candidates(tmp_path)
    review_path = tmp_path / "review.csv"
    _write_decisions(
        review_path,
        mod._FULL_EXPORT_COLUMNS,
        [
            {"candidate_id": "12:456", "decision": "accept"},
            {"candidate_id": "14:999", "decision": ""},
        ],
    )
    conn = _FakeConn(comedian_names={12: "Ari Shaffir", 14: "Mark Normand"})
    _install_fakes(monkeypatch, conn)

    summary, errors = mod._apply(
        decisions_path=review_path,
        audit_path=audit_path,
        dry_run=False,
        force=False,
        reviewer="matt",
    )

    assert errors == []
    assert summary.accepted == 1
    assert summary.skipped == 1
    assert summary.errored == 0
    # Only the accepted candidate produced an identity link
    assert {(w["comedian_id"], w["source_feed_id"]) for w in conn.identity_link_writes} == {(12, "456")}


def test_apply_reports_unknown_decision_and_candidate_with_row_numbers(monkeypatch, tmp_path):
    audit_path = _seed_two_candidates(tmp_path)
    review_path = tmp_path / "review.csv"
    _write_decisions(
        review_path,
        ["candidate_id", "decision"],
        [
            {"candidate_id": "12:456", "decision": "maybe"},
            {"candidate_id": "99:000", "decision": "accept"},
            {"candidate_id": "garbage", "decision": "accept"},
        ],
    )
    conn = _FakeConn(comedian_names={12: "Ari Shaffir", 14: "Mark Normand"})
    _install_fakes(monkeypatch, conn)

    summary, errors = mod._apply(
        decisions_path=review_path,
        audit_path=audit_path,
        dry_run=False,
        force=False,
        reviewer="matt",
    )

    assert summary.accepted == 0
    assert summary.errored == 3
    error_by_row = {e.row_number: e.message for e in errors}
    assert 2 in error_by_row and "unknown decision" in error_by_row[2]
    assert "'maybe'" in error_by_row[2]
    assert 3 in error_by_row and "unknown candidate_id" in error_by_row[3]
    assert "'99:000'" in error_by_row[3]
    assert 4 in error_by_row and "malformed candidate_id" in error_by_row[4]
    # No DB writes when every row errored
    assert conn.identity_link_writes == []
    assert conn.appearance_writes == []


def test_apply_refuses_non_pending_without_force(monkeypatch, tmp_path):
    audit_path = _seed_two_candidates(tmp_path)
    review_path = tmp_path / "review.csv"
    _write_decisions(
        review_path,
        ["candidate_id", "decision"],
        [{"candidate_id": "12:456", "decision": "accept"}],
    )
    conn = _FakeConn(
        comedian_names={12: "Ari Shaffir", 14: "Mark Normand"},
        identity_links={(12, "456"): "rejected"},
    )
    _install_fakes(monkeypatch, conn)

    summary, errors = mod._apply(
        decisions_path=review_path,
        audit_path=audit_path,
        dry_run=False,
        force=False,
        reviewer="matt",
    )

    assert summary.accepted == 0
    assert summary.errored == 1
    assert errors[0].row_number == 2
    assert "already 'rejected'" in errors[0].message
    assert "--force" in errors[0].message
    # No new identity_link write
    assert conn.identity_link_writes == []


def test_apply_with_force_overrides_existing_decision(monkeypatch, tmp_path):
    audit_path = _seed_two_candidates(tmp_path)
    review_path = tmp_path / "review.csv"
    _write_decisions(
        review_path,
        ["candidate_id", "decision"],
        [{"candidate_id": "12:456", "decision": "accept"}],
    )
    conn = _FakeConn(
        comedian_names={12: "Ari Shaffir", 14: "Mark Normand"},
        identity_links={(12, "456"): "rejected"},
    )
    _install_fakes(monkeypatch, conn)

    summary, errors = mod._apply(
        decisions_path=review_path,
        audit_path=audit_path,
        dry_run=False,
        force=True,
        reviewer="matt",
    )

    assert errors == []
    assert summary.accepted == 1
    assert summary.errored == 0
    assert conn.identity_links[(12, "456")] == "verified"


def test_apply_dry_run_does_not_write_to_database(monkeypatch, tmp_path):
    audit_path = _seed_two_candidates(tmp_path)
    review_path = tmp_path / "review.csv"
    _write_decisions(
        review_path,
        ["candidate_id", "decision"],
        [
            {"candidate_id": "12:456", "decision": "accept"},
            {"candidate_id": "14:999", "decision": "reject"},
        ],
    )
    conn = _FakeConn(comedian_names={12: "Ari Shaffir", 14: "Mark Normand"})
    _install_fakes(monkeypatch, conn)

    summary, errors = mod._apply(
        decisions_path=review_path,
        audit_path=audit_path,
        dry_run=True,
        force=False,
        reviewer="matt",
    )

    assert errors == []
    assert summary.accepted == 1
    assert summary.rejected == 1
    assert summary.appearances_written == 2  # what *would* be materialized
    assert conn.identity_link_writes == []
    assert conn.appearance_writes == []
    assert conn.commits == 0


def test_apply_decisions_prevent_candidates_from_reappearing_on_next_export(
    monkeypatch, tmp_path
):
    audit_path = _seed_two_candidates(tmp_path)
    review_path = tmp_path / "review.csv"
    _write_decisions(
        review_path,
        ["candidate_id", "decision"],
        [
            {"candidate_id": "12:456", "decision": "accept"},
            {"candidate_id": "14:999", "decision": "reject"},
        ],
    )
    conn = _FakeConn(comedian_names={12: "Ari Shaffir", 14: "Mark Normand"})
    _install_fakes(monkeypatch, conn)

    apply_summary, apply_errors = mod._apply(
        decisions_path=review_path,
        audit_path=audit_path,
        dry_run=False,
        force=False,
        reviewer="matt",
    )
    assert apply_errors == []
    assert apply_summary.accepted == 1 and apply_summary.rejected == 1

    # Re-run export against the same audit file with the now-populated identity_links;
    # both decided candidates must be filtered out.
    output_path = tmp_path / "next-review.csv"
    written = mod._export(audit_path=audit_path, output_path=output_path)
    assert written == 0
    with output_path.open() as fh:
        rows = list(csv.DictReader(fh))
    assert rows == []


def test_apply_ignored_candidates_also_prevent_reappearance(monkeypatch, tmp_path):
    audit_path = _seed_two_candidates(tmp_path)
    review_path = tmp_path / "review.csv"
    _write_decisions(
        review_path,
        ["candidate_id", "decision"],
        [
            {"candidate_id": "12:456", "decision": "ignore"},
            {"candidate_id": "14:999", "decision": "ignore"},
        ],
    )
    conn = _FakeConn(comedian_names={12: "Ari Shaffir", 14: "Mark Normand"})
    _install_fakes(monkeypatch, conn)

    summary, errors = mod._apply(
        decisions_path=review_path,
        audit_path=audit_path,
        dry_run=False,
        force=False,
        reviewer="matt",
    )
    assert errors == []
    assert summary.ignored == 2
    assert summary.appearances_written == 0  # ignore does not materialize

    output_path = tmp_path / "next-review.csv"
    written = mod._export(audit_path=audit_path, output_path=output_path)
    assert written == 0


def test_apply_summary_counts_each_disposition(monkeypatch, tmp_path, capsys):
    audit_path = _seed_two_candidates(tmp_path)
    review_path = tmp_path / "review.csv"
    _write_decisions(
        review_path,
        ["candidate_id", "decision"],
        [
            {"candidate_id": "12:456", "decision": "accept"},
            {"candidate_id": "14:999", "decision": "reject"},
            {"candidate_id": "12:456", "decision": ""},  # blank → skipped
            {"candidate_id": "12:456", "decision": "huh"},  # bad decision → errored
        ],
    )
    conn = _FakeConn(comedian_names={12: "Ari Shaffir", 14: "Mark Normand"})
    _install_fakes(monkeypatch, conn)

    summary, errors = mod._apply(
        decisions_path=review_path,
        audit_path=audit_path,
        dry_run=True,
        force=False,
        reviewer="matt",
    )
    mod._print_apply_report(summary, errors, dry_run=True)

    assert summary.accepted == 1
    assert summary.rejected == 1
    assert summary.skipped == 1
    assert summary.errored == 1

    out = capsys.readouterr().out
    assert "Validation problems:" in out
    assert "row 5:" in out  # the bad decision was the 4th data row → CSV row 5
    assert (
        "DRY RUN — Summary: 1 accepted, 1 rejected, 0 ignored, 1 skipped, 1 errored" in out
    )


def test_apply_errors_when_csv_missing_required_columns(monkeypatch, tmp_path):
    audit_path = _seed_two_candidates(tmp_path)
    review_path = tmp_path / "review.csv"
    with review_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["foo", "bar"])
        writer.writerow(["1", "2"])
    conn = _FakeConn(comedian_names={12: "Ari Shaffir", 14: "Mark Normand"})
    _install_fakes(monkeypatch, conn)

    summary, errors = mod._apply(
        decisions_path=review_path,
        audit_path=audit_path,
        dry_run=True,
        force=False,
        reviewer="matt",
    )

    assert summary.accepted == 0
    assert summary.errored == 1
    assert "missing required columns" in errors[0].message


def test_main_export_command_invokes_export(monkeypatch, tmp_path, capsys):
    audit_path = _seed_two_candidates(tmp_path)
    output_path = tmp_path / "out.csv"
    conn = _FakeConn(comedian_names={12: "Ari Shaffir", 14: "Mark Normand"})
    _install_fakes(monkeypatch, conn)

    exit_code = mod.main(
        [
            "export",
            "--audit-path",
            str(audit_path),
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    captured = capsys.readouterr().out
    assert "Wrote 2 candidate(s)" in captured
    assert output_path.exists()


def test_main_apply_requires_dry_run_or_confirm(monkeypatch, tmp_path):
    audit_path = _seed_two_candidates(tmp_path)
    review_path = tmp_path / "review.csv"
    _write_decisions(
        review_path,
        ["candidate_id", "decision"],
        [{"candidate_id": "12:456", "decision": "accept"}],
    )
    conn = _FakeConn(comedian_names={12: "Ari Shaffir", 14: "Mark Normand"})
    _install_fakes(monkeypatch, conn)

    try:
        mod.main(["apply", "--input", str(review_path), "--audit-path", str(audit_path)])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("expected --dry-run/--confirm requirement to abort")


def test_apply_errors_when_audit_path_missing(monkeypatch, tmp_path):
    review_path = tmp_path / "review.csv"
    _write_decisions(
        review_path,
        ["candidate_id", "decision"],
        [{"candidate_id": "12:456", "decision": "accept"}],
    )
    conn = _FakeConn(comedian_names={12: "Ari Shaffir"})
    _install_fakes(monkeypatch, conn)

    summary, errors = mod._apply(
        decisions_path=review_path,
        audit_path=tmp_path / "does-not-exist.jsonl",
        dry_run=False,
        force=False,
        reviewer="matt",
    )

    assert summary.accepted == 0
    assert summary.errored == 1
    assert len(errors) == 1
    assert "audit log not found" in errors[0].message
    # No DB writes attempted
    assert conn.identity_link_writes == []
    assert conn.appearance_writes == []
    assert conn.commits == 0


def test_apply_errors_when_input_csv_missing(monkeypatch, tmp_path):
    conn = _FakeConn(comedian_names={12: "Ari Shaffir"})
    _install_fakes(monkeypatch, conn)

    summary, errors = mod._apply(
        decisions_path=tmp_path / "nonexistent.csv",
        audit_path=tmp_path / "audit.jsonl",
        dry_run=False,
        force=False,
        reviewer="matt",
    )

    assert summary.errored == 1
    assert "input CSV not found" in errors[0].message
    # No further work attempted
    assert summary.accepted == 0
    assert conn.identity_link_writes == []


def test_apply_rejects_duplicate_candidate_id_rows(monkeypatch, tmp_path):
    audit_path = _seed_two_candidates(tmp_path)
    review_path = tmp_path / "review.csv"
    _write_decisions(
        review_path,
        ["candidate_id", "decision"],
        [
            {"candidate_id": "12:456", "decision": "accept"},
            {"candidate_id": "12:456", "decision": "reject"},
        ],
    )
    conn = _FakeConn(comedian_names={12: "Ari Shaffir", 14: "Mark Normand"})
    _install_fakes(monkeypatch, conn)

    summary, errors = mod._apply(
        decisions_path=review_path,
        audit_path=audit_path,
        dry_run=False,
        force=False,
        reviewer="matt",
    )

    assert summary.accepted == 1  # the first decision still wins
    assert summary.rejected == 0
    assert summary.errored == 1
    duplicate_error = next(e for e in errors if "already decided" in e.message)
    assert duplicate_error.row_number == 3
    assert "row 2" in duplicate_error.message


def test_apply_rolls_back_on_mid_batch_failure(monkeypatch, tmp_path):
    audit_path = _seed_two_candidates(tmp_path)
    review_path = tmp_path / "review.csv"
    _write_decisions(
        review_path,
        ["candidate_id", "decision"],
        [
            {"candidate_id": "12:456", "decision": "accept"},
            {"candidate_id": "14:999", "decision": "accept"},
        ],
    )
    # Execute order during _apply: 2 SELECTs from _build_candidates
    # (identity_link statuses + comedian names), then 1 identity_link
    # INSERT per planned action. Inject the failure on execute #4 so the
    # first accept commits its identity_link write and the second
    # accept's INSERT raises mid-batch.
    conn = _FakeConn(
        comedian_names={12: "Ari Shaffir", 14: "Mark Normand"},
        raise_on_execute_count=4,
    )
    _install_fakes(monkeypatch, conn)

    with pytest.raises(RuntimeError, match="injected failure"):
        mod._apply(
            decisions_path=review_path,
            audit_path=audit_path,
            dry_run=False,
            force=False,
            reviewer="matt",
        )

    # Transaction wrapper invoked rollback, not commit
    assert conn.commits == 0
    assert conn.rollbacks == 1


def test_main_apply_with_errors_returns_nonzero(monkeypatch, tmp_path, capsys):
    audit_path = _seed_two_candidates(tmp_path)
    review_path = tmp_path / "review.csv"
    _write_decisions(
        review_path,
        ["candidate_id", "decision"],
        [{"candidate_id": "12:456", "decision": "huh"}],
    )
    conn = _FakeConn(comedian_names={12: "Ari Shaffir", 14: "Mark Normand"})
    _install_fakes(monkeypatch, conn)

    exit_code = mod.main(
        [
            "apply",
            "--input",
            str(review_path),
            "--audit-path",
            str(audit_path),
            "--dry-run",
        ]
    )

    assert exit_code == 2
    out = capsys.readouterr().out
    assert "unknown decision" in out
    assert "0 accepted" in out
