from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

_repo_root = Path(__file__).resolve().parents[3]
_src_path = _repo_root / "src"
for _path in (str(_src_path), str(_repo_root)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from scripts.core import repair_podcast_attribution_integrity as mod  # noqa: E402


def _resolution(
    requested_id: int,
    canonical_id: int,
    *,
    error: str | None = None,
) -> mod.Resolution:
    return mod.Resolution(
        requested_id=requested_id,
        canonical_id=canonical_id,
        canonical_name=f"Comic {canonical_id}",
        canonical_visible=error != "canonical comedian is hidden",
        alias_path=(requested_id, canonical_id)
        if requested_id != canonical_id
        else (canonical_id,),
        error=error,
    )


def _row(
    row_id: int,
    comedian_id: int,
    *,
    table: str = "comedian_podcasts",
    podcast_id: int = 10,
    source: str = "podcast_index",
    source_identity: str = "feed-10",
    target_id: int | None = None,
    active_podcast_deny: bool = False,
) -> mod.AttributionRow:
    return mod.AttributionRow(
        table=table,
        row_id=row_id,
        comedian_id=comedian_id,
        podcast_id=podcast_id,
        source=source,
        role="host" if "podcast" in table else "guest",
        status="accepted",
        confidence=0.95,
        evidence={"source": row_id},
        reviewed_by="reviewer",
        reviewed_at=None,
        created_at=None,
        updated_at=None,
        source_identity=source_identity,
        target_id=target_id,
        active_podcast_deny=active_podcast_deny,
    )


def test_plan_canonicalizes_alias_and_is_idempotent_after_repair():
    alias = _row(1, 20)
    resolutions = {20: _resolution(20, 30)}

    first = mod.plan_repairs([alias], resolutions)

    assert [(action.kind, action.canonical_id) for action in first] == [
        ("canonicalize", 30)
    ]

    repaired = _row(1, 30)
    second = mod.plan_repairs([repaired], {30: _resolution(30, 30)})
    assert [action.kind for action in second] == ["unchanged"]


def test_plan_prefers_canonical_survivor_and_absorbs_cross_source_ownership_conflict():
    alias = _row(8, 20, source="podcast_index")
    canonical = _row(12, 30, source="manual")
    resolutions = {
        20: _resolution(20, 30),
        30: _resolution(30, 30),
    }

    actions = mod.plan_repairs([alias, canonical], resolutions)

    assert actions[0].kind == "absorb"
    assert actions[0].survivor_id == 12
    assert actions[1].kind == "unchanged"


def test_plan_keeps_distinct_appearance_sources_but_merges_review_identity_conflicts():
    appearance_a = _row(
        1,
        20,
        table="episode_appearances",
        source="podcast_index",
        source_identity="episode-10",
        target_id=55,
    )
    appearance_b = _row(
        2,
        30,
        table="episode_appearances",
        source="manual",
        source_identity="episode-10",
        target_id=55,
    )
    review_a = _row(
        3,
        20,
        table="episode_appearance_reviews",
        source="podcast_index",
        source_identity="episode-10",
        target_id=55,
    )
    review_b = _row(
        4,
        30,
        table="episode_appearance_reviews",
        source="podcast_index",
        source_identity="episode-10",
        target_id=55,
    )
    resolutions = {
        20: _resolution(20, 30),
        30: _resolution(30, 30),
    }

    appearance_actions = mod.plan_repairs(
        [appearance_a, appearance_b], resolutions
    )
    review_actions = mod.plan_repairs([review_a, review_b], resolutions)

    assert [action.kind for action in appearance_actions] == [
        "canonicalize",
        "unchanged",
    ]
    assert [action.kind for action in review_actions] == ["absorb", "unchanged"]


def test_plan_blocks_hidden_denied_missing_and_active_podcast_rows():
    rows = [
        _row(1, 1),
        _row(2, 2),
        _row(3, 3),
        _row(4, 4, active_podcast_deny=True),
    ]
    resolutions = {
        1: _resolution(1, 1, error="canonical comedian is hidden"),
        2: _resolution(2, 2, error="canonical comedian is deny-listed"),
        4: _resolution(4, 4),
    }

    actions = mod.plan_repairs(rows, resolutions)

    assert [action.kind for action in actions] == ["block"] * 4
    assert [action.reason for action in actions] == [
        "canonical comedian is hidden",
        "canonical comedian is deny-listed",
        "comedian resolution missing",
        "podcast is actively deny-listed",
    ]


def test_repair_evidence_preserves_absorbed_row_snapshot():
    survivor = _row(1, 30)
    loser = _row(2, 20)

    evidence = mod._with_repair_evidence(
        survivor.evidence,
        action="absorbed_conflict",
        reason="uniqueness conflict",
        row=survivor,
        canonical_id=30,
        absorbed_row=loser,
    )

    entry = evidence["attribution_integrity_repair"][0]
    assert entry["source_row_id"] == 1
    assert entry["absorbed_row"]["row_id"] == 2
    assert entry["absorbed_row"]["evidence"] == {"source": 2}


class _FakeCursor:
    def __init__(self, conn: "_FakeConn") -> None:
        self.conn = conn
        self.rows: list[tuple[Any, ...]] = []

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, *_exc: Any) -> bool:
        return False

    def execute(self, sql: str, params: Any = None) -> None:
        normalized = " ".join(sql.split())
        self.conn.executed.append((normalized, params))
        if normalized.startswith("SELECT cp.id, cp.comedian_id"):
            self.rows = list(self.conn.ownership_rows)
        elif normalized.startswith("WITH RECURSIVE relevant_ids"):
            self.rows = list(self.conn.verify_rows)
        else:
            self.rows = []

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self.rows


class _FakeConn:
    def __init__(self, ownership_rows: list[tuple[Any, ...]]) -> None:
        self.ownership_rows = ownership_rows
        self.verify_rows: list[tuple[Any, ...]] = []
        self.executed: list[tuple[str, Any]] = []

    def cursor(self) -> _FakeCursor:
        return _FakeCursor(self)


def _ownership_export_row(row_id: int, podcast_id: int) -> tuple[Any, ...]:
    return (
        row_id,
        30,
        "Taylor Comic",
        None,
        True,
        podcast_id,
        "Taylor Talks",
        "Taylor Comic",
        "https://feeds.example/taylor.xml",
        "https://example.test/taylor",
        "host",
        "podcast_index",
        "codex",
        0.97,
        {"match_field": "author"},
    )


def _write_decisions(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["comedian_podcast_id", "decision", "reason"],
        )
        writer.writeheader()
        writer.writerows(rows)


def test_re_review_requires_complete_coverage_before_writes(tmp_path):
    conn = _FakeConn([_ownership_export_row(1, 10), _ownership_export_row(2, 11)])
    decisions = tmp_path / "decisions.csv"
    _write_decisions(
        decisions,
        [{"comedian_podcast_id": "1", "decision": "accept", "reason": "verified"}],
    )

    try:
        mod._apply_re_review_decisions(
            conn, decisions, "reviewer", mod.RepairSummary()
        )
    except ValueError as exc:
        assert "coverage mismatch" in str(exc)
    else:
        raise AssertionError("incomplete coverage should fail")

    assert not any(sql.startswith("UPDATE comedian_podcasts") for sql, _ in conn.executed)


def test_re_review_accept_reject_and_deny_podcast_preserve_decisions(tmp_path):
    conn = _FakeConn(
        [
            _ownership_export_row(1, 10),
            _ownership_export_row(2, 11),
            _ownership_export_row(3, 12),
        ]
    )
    decisions = tmp_path / "decisions.csv"
    _write_decisions(
        decisions,
        [
            {"comedian_podcast_id": "1", "decision": "accept", "reason": "verified identity"},
            {"comedian_podcast_id": "2", "decision": "reject", "reason": "same-name collision"},
            {"comedian_podcast_id": "3", "decision": "deny_podcast", "reason": "non-comedy podcast"},
        ],
    )
    summary = mod.RepairSummary()

    mod._apply_re_review_decisions(conn, decisions, "reviewer", summary)

    assert summary.re_reviewed_accept == 1
    assert summary.re_reviewed_reject == 2
    assert summary.podcasts_denied == 1
    update_params = [
        params
        for sql, params in conn.executed
        if sql.startswith("UPDATE comedian_podcasts")
    ]
    assert len(update_params) == 3
    assert json.loads(update_params[0][0])["task_3908_re_review"]["decision"] == "accept"
    assert any(sql.startswith("INSERT INTO podcast_deny_list") for sql, _ in conn.executed)


def test_export_and_verify_report_are_repeatable(tmp_path):
    conn = _FakeConn([_ownership_export_row(1, 10)])
    output = tmp_path / "ownership.csv"

    assert mod.export_re_review(conn, output) == 1
    exported = list(csv.DictReader(output.open()))
    assert exported[0]["comedian_podcast_id"] == "1"
    assert exported[0]["decision"] == ""

    conn.verify_rows = [
        ("ownership_invalid", 0),
        ("appearance_invalid", 0),
        ("ownership_missing_re_review", 0),
    ]
    assert mod.verify(conn) == {
        "ownership_invalid": 0,
        "appearance_invalid": 0,
        "ownership_missing_re_review": 0,
    }


def test_sql_contract_covers_active_denies_normalized_names_and_all_four_tables():
    assert "REGEXP_REPLACE(REPLACE" in mod._RESOLUTION_SQL
    assert "restored_at IS NULL" in mod._ACTIVE_PODCAST_DENIES_SQL
    assert "source_podcast_id" in mod._ACTIVE_PODCAST_DENIES_SQL
    assert "feed_url" in mod._ACTIVE_PODCAST_DENIES_SQL
    for table in (
        "comedian_podcasts",
        "episode_appearances",
        "podcast_candidate_reviews",
        "episode_appearance_reviews",
    ):
        assert table in mod._VERIFY_SQL
