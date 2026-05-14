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

from scripts.core import review_podcast_appearance_candidates as mod  # noqa: E402


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
        if normalized.startswith("SELECT ear.id"):
            rows = self._conn.review_rows
            if params and not params[0]:
                rows = [row for row in rows if row[5] == "pending"]
            self._last_result = rows
        elif normalized.startswith("UPDATE episode_appearance_reviews"):
            status, role, confidence, evidence_json, reviewer, candidate_id = params
            self._conn.review_updates.append(
                {
                    "id": int(candidate_id),
                    "candidate_status": status,
                    "appearance_role": role,
                    "confidence": confidence,
                    "evidence": json.loads(evidence_json),
                    "reviewed_by": reviewer,
                }
            )
            self._last_result = []
        elif normalized.startswith("INSERT INTO episode_appearances"):
            self._conn.appearance_writes.append(params)
            self._last_result = []
        else:
            self._last_result = []

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self._last_result


class _FakeConn:
    def __init__(self, review_rows: list[tuple[Any, ...]]) -> None:
        self.review_rows = review_rows
        self.review_updates: list[dict[str, Any]] = []
        self.appearance_writes: list[Any] = []
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
    episode_id: int = 5,
    source_episode_id: str = "ep-5",
    status: str = "pending",
    role: str = "guest",
    confidence: float = 0.62,
    evidence: dict[str, Any] | None = None,
) -> tuple[Any, ...]:
    evidence = evidence or {
        "matched_name": "Ari Shaffir",
        "source_field": "title",
        "evidence_text": "Ari Shaffir is our guest",
    }
    return (
        candidate_id,
        comedian_id,
        "Ari Shaffir",
        episode_id,
        source_episode_id,
        status,
        role,
        confidence,
        "Comedy Talk",
        "Ari Shaffir is our guest",
        "https://podcast.example/5",
        evidence,
    )


def _write_decisions(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=mod._FULL_EXPORT_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in mod._FULL_EXPORT_COLUMNS})


def test_export_writes_pending_appearance_candidates_with_blank_decisions(monkeypatch, tmp_path):
    conn = _FakeConn(
        [
            _review_row(candidate_id=1, confidence=0.82),
            _review_row(candidate_id=2, source_episode_id="ep-6", status="rejected"),
        ]
    )
    _install_fakes(monkeypatch, conn)
    output_path = tmp_path / "appearance-review.csv"

    written = mod._export(output_path=output_path, include_resolved=False, limit=None)

    assert written == 1
    rows = list(csv.DictReader(output_path.open()))
    assert rows[0]["candidate_id"] == "1"
    assert rows[0]["comedian_name"] == "Ari Shaffir"
    assert rows[0]["source_episode_id"] == "ep-5"
    assert rows[0]["appearance_role"] == "guest"
    assert rows[0]["decision"] == ""
    assert rows[0]["review_reason"] == ""
    assert json.loads(rows[0]["evidence"])["source_field"] == "title"


def test_apply_accept_reject_ignore_blank_and_dry_run(monkeypatch, tmp_path):
    conn = _FakeConn([_review_row(candidate_id=1), _review_row(candidate_id=2, source_episode_id="ep-6")])
    _install_fakes(monkeypatch, conn)
    input_path = tmp_path / "review.csv"
    _write_decisions(
        input_path,
        [
            {"candidate_id": "1", "decision": "accept", "review_reason": "confirmed"},
            {"candidate_id": "2", "decision": "reject"},
            {"candidate_id": "1", "decision": ""},
        ],
    )

    summary, errors = mod._apply(
        decisions_path=input_path,
        dry_run=True,
        force=False,
        reviewer="matt",
    )

    assert errors == []
    assert summary.accepted == 1
    assert summary.rejected == 1
    assert summary.skipped == 1
    assert summary.appearances_written == 1
    assert conn.review_updates == []
    assert conn.appearance_writes == []


def test_apply_confirm_updates_reviews_and_materializes_accepts(monkeypatch, tmp_path):
    conn = _FakeConn([_review_row(candidate_id=1)])
    _install_fakes(monkeypatch, conn)
    input_path = tmp_path / "review.csv"
    _write_decisions(input_path, [{"candidate_id": "1", "decision": "accept", "review_reason": "heard it"}])

    summary, errors = mod._apply(
        decisions_path=input_path,
        dry_run=False,
        force=False,
        reviewer="matt",
    )

    assert errors == []
    assert summary.accepted == 1
    assert summary.appearances_written == 1
    assert conn.commits == 1
    assert conn.review_updates[0]["candidate_status"] == "accepted"
    assert conn.review_updates[0]["evidence"]["review_reason"] == "heard it"
    assert conn.appearance_writes[0][:7] == (12, 5, "podcast_index", "guest", "accepted", 0.62, "matt")


def test_apply_validates_decisions_candidates_duplicates_and_resolved_status(monkeypatch, tmp_path):
    conn = _FakeConn([_review_row(candidate_id=1, status="accepted")])
    _install_fakes(monkeypatch, conn)
    input_path = tmp_path / "review.csv"
    _write_decisions(
        input_path,
        [
            {"candidate_id": "1", "decision": "accept"},
            {"candidate_id": "999", "decision": "accept"},
            {"candidate_id": "1", "decision": "maybe"},
            {"candidate_id": "1", "decision": "reject"},
        ],
    )

    summary, errors = mod._apply(
        decisions_path=input_path,
        dry_run=False,
        force=False,
        reviewer="matt",
    )

    assert summary.errored == 4
    messages = [err.message for err in errors]
    assert any("already 'accepted'" in msg for msg in messages)
    assert any("unknown candidate_id '999'" in msg for msg in messages)
    assert any("unknown decision 'maybe'" in msg for msg in messages)
    assert any("already decided in row 2" in msg for msg in messages)
    assert conn.review_updates == []
