from __future__ import annotations

import contextlib
import csv
import json
import sys
from pathlib import Path
from typing import Any

_repo_root = Path(__file__).resolve().parents[3]
_src_path = _repo_root / "src"
for _p in (str(_src_path), str(_repo_root)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from scripts.core import review_podcast_ownership_candidates as mod  # noqa: E402


class _FakeCursor:
    def __init__(self, conn: "_FakeConn") -> None:
        self._conn = conn
        self._last_result: list[tuple[Any, ...]] = []

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, *_exc: Any) -> bool:
        return False

    def execute(self, sql: str, params: Any = None) -> None:
        self._conn.executed.append((sql, params))
        normalized = " ".join(sql.split())
        if normalized.startswith("SELECT pcr.id"):
            rows = self._conn.review_rows
            if params and not params[0]:
                rows = [row for row in rows if row[6] == "pending"]
            self._last_result = rows
        elif normalized.startswith("UPDATE podcast_candidate_reviews"):
            status, association_type, confidence, evidence_json, reviewer, candidate_id = params
            self._conn.review_updates.append(
                {
                    "id": int(candidate_id),
                    "candidate_status": status,
                    "association_type": association_type,
                    "confidence": confidence,
                    "evidence": json.loads(evidence_json),
                    "reviewed_by": reviewer,
                }
            )
            self._last_result = []
        elif normalized.startswith("INSERT INTO comedian_podcasts"):
            self._conn.ownership_writes.append(params)
            self._last_result = []
        else:
            self._last_result = []

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self._last_result


class _FakeConn:
    def __init__(self, review_rows: list[tuple[Any, ...]]) -> None:
        self.review_rows = review_rows
        self.review_updates: list[dict[str, Any]] = []
        self.ownership_writes: list[Any] = []
        self.executed: list[tuple[str, Any]] = []
        self.commits = 0
        self.rollbacks = 0

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


def _review_row(
    *,
    candidate_id: int,
    comedian_id: int = 12,
    podcast_id: int = 42,
    source_podcast_id: str = "1001",
    status: str = "pending",
    association_type: str = "host",
    confidence: float = 0.91,
    evidence: dict[str, Any] | None = None,
) -> tuple[Any, ...]:
    evidence = evidence or {
        "matched_name": "Taylor Comic",
        "confidence_band": "title_exact",
    }
    return (
        candidate_id,
        comedian_id,
        "Taylor Comic",
        podcast_id,
        "podcast_index",
        source_podcast_id,
        status,
        association_type,
        confidence,
        "Taylor Talks",
        "Taylor Comic",
        "https://feeds.example.com/taylor.xml",
        "https://podcast.example/taylor",
        evidence,
    )


def _write_decisions(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=mod._FULL_EXPORT_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in mod._FULL_EXPORT_COLUMNS})


def test_export_writes_pending_ownership_candidates_with_backfill_warning(monkeypatch, tmp_path):
    conn = _FakeConn(
        [
            _review_row(candidate_id=1, confidence=0.91),
            _review_row(candidate_id=2, source_podcast_id="1002", status="rejected"),
        ]
    )
    _install_fakes(monkeypatch, conn)
    output_path = tmp_path / "ownership-review.csv"

    written = mod._export(output_path=output_path, include_resolved=False, limit=None)

    assert written == 1
    rows = list(csv.DictReader(output_path.open()))
    assert rows[0]["candidate_id"] == "1"
    assert rows[0]["comedian_name"] == "Taylor Comic"
    assert rows[0]["podcast_title"] == "Taylor Talks"
    assert rows[0]["association_type"] == "host"
    assert rows[0]["decision"] == ""
    assert rows[0]["review_reason"] == ""
    assert "accepted comedian_podcasts rows exist" in mod._build_parser().description


def test_apply_accept_materializes_comedian_podcast(monkeypatch, tmp_path):
    conn = _FakeConn([_review_row(candidate_id=1)])
    _install_fakes(monkeypatch, conn)
    input_path = tmp_path / "review.csv"
    _write_decisions(input_path, [{"candidate_id": "1", "decision": "accept", "review_reason": "owned"}])

    summary, errors = mod._apply(
        decisions_path=input_path,
        dry_run=False,
        force=False,
        reviewer="matt",
    )

    assert errors == []
    assert summary.accepted == 1
    assert summary.ownership_rows_written == 1
    assert conn.commits == 1
    assert conn.review_updates[0]["candidate_status"] == "accepted"
    assert conn.review_updates[0]["evidence"]["review_reason"] == "owned"
    assert conn.ownership_writes[0][:7] == (12, 42, "host", "podcast_index", "accepted", 0.91, "matt")


def test_apply_reject_only_marks_candidate_rejected(monkeypatch, tmp_path):
    conn = _FakeConn([_review_row(candidate_id=1)])
    _install_fakes(monkeypatch, conn)
    input_path = tmp_path / "review.csv"
    _write_decisions(input_path, [{"candidate_id": "1", "decision": "reject", "review_reason": "not owned"}])

    summary, errors = mod._apply(
        decisions_path=input_path,
        dry_run=False,
        force=False,
        reviewer="matt",
    )

    assert errors == []
    assert summary.rejected == 1
    assert summary.ownership_rows_written == 0
    assert conn.review_updates[0]["candidate_status"] == "rejected"
    assert conn.review_updates[0]["evidence"]["review_reason"] == "not owned"
    assert conn.ownership_writes == []
