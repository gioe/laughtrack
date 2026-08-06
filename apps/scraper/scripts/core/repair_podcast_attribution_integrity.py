#!/usr/bin/env python3
"""Repair and verify canonical podcast attribution relationships.

The command is dry-run by default.  ``--apply`` performs the planned repair in
one transaction.  Ownership re-review is intentionally separate: export every
accepted host/cohost row, record an explicit decision for each row, then pass
the completed CSV back with ``--re-review-decisions``.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

from psycopg2.extras import execute_values

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from laughtrack.adapters.db import get_connection, get_transaction

_REPAIR_VERSION = "task-3908-podcast-attribution-integrity-v1"
_REVIEW_DECISIONS = frozenset({"accept", "reject", "deny_podcast"})

_RESOLUTION_SQL = """
    WITH RECURSIVE relevant_ids AS (
        SELECT comedian_id FROM comedian_podcasts
        WHERE review_status = 'accepted'
        UNION
        SELECT comedian_id FROM episode_appearances
        WHERE review_status = 'accepted'
        UNION
        SELECT comedian_id FROM podcast_candidate_reviews
        WHERE candidate_status IN ('accepted', 'pending')
        UNION
        SELECT comedian_id FROM episode_appearance_reviews
        WHERE candidate_status IN ('accepted', 'pending')
    ), lineage AS (
        SELECT
            r.comedian_id AS requested_id,
            c.id AS current_id,
            c.name,
            c.parent_comedian_id,
            c.visible,
            ARRAY[c.id]::int[] AS alias_path,
            FALSE AS cycle
        FROM relevant_ids r
        JOIN comedians c ON c.id = r.comedian_id

        UNION ALL

        SELECT
            l.requested_id,
            parent.id,
            parent.name,
            parent.parent_comedian_id,
            parent.visible,
            l.alias_path || parent.id,
            parent.id = ANY(l.alias_path)
        FROM lineage l
        JOIN comedians parent ON parent.id = l.parent_comedian_id
        WHERE NOT l.cycle
    ), terminal AS (
        SELECT DISTINCT ON (requested_id)
            requested_id,
            current_id AS canonical_id,
            name AS canonical_name,
            visible AS canonical_visible,
            alias_path,
            cycle
        FROM lineage
        WHERE parent_comedian_id IS NULL OR cycle
        ORDER BY requested_id, cardinality(alias_path) DESC
    )
    SELECT
        t.requested_id,
        t.canonical_id,
        t.canonical_name,
        t.canonical_visible,
        t.alias_path,
        t.cycle,
        EXISTS (
            SELECT 1
            FROM comedian_deny_list d
            WHERE LOWER(BTRIM(REGEXP_REPLACE(REPLACE(d.name, CHR(160), ' '), '[[:space:]]+', ' ', 'g'))) =
                  LOWER(BTRIM(REGEXP_REPLACE(REPLACE(t.canonical_name, CHR(160), ' '), '[[:space:]]+', ' ', 'g')))
        ) AS canonical_denied
    FROM terminal t
"""

_ACTIVE_PODCAST_DENIES_SQL = """
    SELECT DISTINCT p.id
    FROM podcasts p
    JOIN podcast_deny_list d ON d.restored_at IS NULL
      AND (
          d.podcast_id = p.id
          OR (d.source = p.source AND d.source_podcast_id = p.source_podcast_id)
          OR (d.feed_url IS NOT NULL AND p.feed_url IS NOT NULL AND d.feed_url = p.feed_url)
      )
"""

_OWNERSHIP_SQL = """
    SELECT
        cp.id, cp.comedian_id, cp.podcast_id, cp.source, cp.association_type,
        cp.review_status, cp.confidence, cp.evidence, cp.reviewed_by,
        cp.reviewed_at, cp.created_at, cp.updated_at,
        p.source, p.source_podcast_id, p.feed_url
    FROM comedian_podcasts cp
    JOIN podcasts p ON p.id = cp.podcast_id
    WHERE cp.review_status = 'accepted'
      AND cp.association_type IN ('host', 'cohost', 'owner')
"""

_APPEARANCE_SQL = """
    SELECT
        ea.id, ea.comedian_id, pe.podcast_id, ea.source, ea.appearance_role,
        ea.review_status, ea.confidence, ea.evidence, ea.reviewed_by,
        ea.reviewed_at, ea.created_at, ea.updated_at,
        pe.source, pe.source_episode_id, pe.id
    FROM episode_appearances ea
    JOIN podcast_episodes pe ON pe.id = ea.episode_id
    WHERE ea.review_status = 'accepted'
      AND (ea.comedian_id = ANY(%s::int[]) OR pe.podcast_id = ANY(%s::int[]))
"""

_OWNERSHIP_REVIEWS_SQL = """
    SELECT
        r.id, r.comedian_id, r.podcast_id, r.source,
        COALESCE(NULLIF(r.association_type, ''), 'host'),
        r.candidate_status, r.confidence, r.evidence, r.reviewed_by,
        r.reviewed_at, r.created_at, r.updated_at,
        p.source, r.source_podcast_id, p.feed_url
    FROM podcast_candidate_reviews r
    LEFT JOIN podcasts p ON p.id = r.podcast_id
    WHERE r.candidate_status IN ('accepted', 'pending')
      AND (r.comedian_id = ANY(%s::int[]) OR r.podcast_id = ANY(%s::int[]))
"""

_APPEARANCE_REVIEWS_SQL = """
    SELECT
        r.id, r.comedian_id, pe.podcast_id, r.source, r.appearance_role,
        r.candidate_status, r.confidence, r.evidence, r.reviewed_by,
        r.reviewed_at, r.created_at, r.updated_at,
        pe.source, r.source_episode_id, r.episode_id
    FROM episode_appearance_reviews r
    LEFT JOIN podcast_episodes pe ON pe.id = r.episode_id
    WHERE r.candidate_status IN ('accepted', 'pending')
      AND (r.comedian_id = ANY(%s::int[]) OR pe.podcast_id = ANY(%s::int[]))
"""

_OWNERSHIP_REVIEW_EXPORT_SQL = """
    SELECT
        cp.id, cp.comedian_id, c.name, c.parent_comedian_id, c.visible,
        cp.podcast_id, p.title, p.author_name, p.feed_url, p.website_url,
        cp.association_type, cp.source, cp.reviewed_by, cp.confidence, cp.evidence
    FROM comedian_podcasts cp
    JOIN comedians c ON c.id = cp.comedian_id
    JOIN podcasts p ON p.id = cp.podcast_id
    WHERE cp.review_status = 'accepted'
      AND cp.association_type IN ('host', 'cohost')
    ORDER BY cp.id
"""

_VERIFY_SQL = """
    WITH RECURSIVE relevant_ids AS (
        SELECT comedian_id FROM comedian_podcasts
        WHERE review_status = 'accepted'
        UNION
        SELECT comedian_id FROM episode_appearances
        WHERE review_status = 'accepted'
        UNION
        SELECT comedian_id FROM podcast_candidate_reviews
        WHERE candidate_status IN ('accepted', 'pending')
        UNION
        SELECT comedian_id FROM episode_appearance_reviews
        WHERE candidate_status IN ('accepted', 'pending')
    ), lineage AS (
        SELECT c.id AS requested_id, c.id AS current_id, c.name,
               c.parent_comedian_id, c.visible, ARRAY[c.id]::int[] AS path,
               FALSE AS cycle
        FROM relevant_ids r
        JOIN comedians c ON c.id = r.comedian_id
        UNION ALL
        SELECT l.requested_id, p.id, p.name, p.parent_comedian_id, p.visible,
               l.path || p.id, p.id = ANY(l.path)
        FROM lineage l
        JOIN comedians p ON p.id = l.parent_comedian_id
        WHERE NOT l.cycle
    ), terminal AS (
        SELECT DISTINCT ON (requested_id)
            requested_id, current_id AS canonical_id, name AS canonical_name,
            visible AS canonical_visible, cycle
        FROM lineage
        WHERE parent_comedian_id IS NULL OR cycle
        ORDER BY requested_id, cardinality(path) DESC
    ), eligible AS (
        SELECT t.*,
            EXISTS (
                SELECT 1 FROM comedian_deny_list d
                WHERE LOWER(BTRIM(REGEXP_REPLACE(REPLACE(d.name, CHR(160), ' '), '[[:space:]]+', ' ', 'g'))) =
                      LOWER(BTRIM(REGEXP_REPLACE(REPLACE(t.canonical_name, CHR(160), ' '), '[[:space:]]+', ' ', 'g')))
            ) AS denied
        FROM terminal t
    ), active_denied_podcasts AS (
        SELECT DISTINCT p.id
        FROM podcasts p
        JOIN podcast_deny_list d ON d.restored_at IS NULL
          AND (
              d.podcast_id = p.id
              OR (d.source = p.source AND d.source_podcast_id = p.source_podcast_id)
              OR (d.feed_url IS NOT NULL AND p.feed_url IS NOT NULL AND d.feed_url = p.feed_url)
          )
    )
    SELECT 'ownership_invalid' AS metric, COUNT(*)::bigint AS value
    FROM comedian_podcasts cp
    JOIN eligible e ON e.requested_id = cp.comedian_id
    WHERE cp.review_status = 'accepted'
      AND cp.association_type IN ('host', 'cohost', 'owner')
      AND (cp.comedian_id <> e.canonical_id OR e.cycle OR NOT e.canonical_visible OR e.denied
           OR cp.podcast_id IN (SELECT id FROM active_denied_podcasts))
    UNION ALL
    SELECT 'appearance_invalid', COUNT(*)::bigint
    FROM episode_appearances ea
    JOIN podcast_episodes pe ON pe.id = ea.episode_id
    JOIN eligible e ON e.requested_id = ea.comedian_id
    WHERE ea.review_status = 'accepted'
      AND (ea.comedian_id <> e.canonical_id OR e.cycle OR NOT e.canonical_visible OR e.denied
           OR pe.podcast_id IN (SELECT id FROM active_denied_podcasts))
    UNION ALL
    SELECT 'ownership_review_invalid', COUNT(*)::bigint
    FROM podcast_candidate_reviews r
    JOIN eligible e ON e.requested_id = r.comedian_id
    WHERE r.candidate_status IN ('accepted', 'pending')
      AND (r.comedian_id <> e.canonical_id OR e.cycle OR NOT e.canonical_visible OR e.denied
           OR r.podcast_id IN (SELECT id FROM active_denied_podcasts))
    UNION ALL
    SELECT 'appearance_review_invalid', COUNT(*)::bigint
    FROM episode_appearance_reviews r
    LEFT JOIN podcast_episodes pe ON pe.id = r.episode_id
    JOIN eligible e ON e.requested_id = r.comedian_id
    WHERE r.candidate_status IN ('accepted', 'pending')
      AND (r.comedian_id <> e.canonical_id OR e.cycle OR NOT e.canonical_visible OR e.denied
           OR pe.podcast_id IN (SELECT id FROM active_denied_podcasts))
    UNION ALL
    SELECT 'ownership_missing_re_review', COUNT(*)::bigint
    FROM comedian_podcasts cp
    WHERE cp.review_status = 'accepted'
      AND cp.association_type IN ('host', 'cohost')
      AND NOT (cp.evidence ? 'task_3908_re_review')
"""


@dataclass(frozen=True)
class Resolution:
    requested_id: int
    canonical_id: int
    canonical_name: str
    canonical_visible: bool
    alias_path: tuple[int, ...]
    error: Optional[str] = None


@dataclass(frozen=True)
class AttributionRow:
    table: str
    row_id: int
    comedian_id: int
    podcast_id: Optional[int]
    source: str
    role: str
    status: str
    confidence: float
    evidence: dict[str, Any]
    reviewed_by: Optional[str]
    reviewed_at: Any
    created_at: Any
    updated_at: Any
    source_identity: str
    target_id: Optional[int]
    active_podcast_deny: bool


@dataclass(frozen=True)
class RepairAction:
    kind: str
    row: AttributionRow
    canonical_id: Optional[int]
    reason: str
    survivor_id: Optional[int] = None


@dataclass
class RepairSummary:
    canonicalized: dict[str, int] = field(default_factory=dict)
    absorbed: dict[str, int] = field(default_factory=dict)
    blocked: dict[str, int] = field(default_factory=dict)
    unchanged: dict[str, int] = field(default_factory=dict)
    re_reviewed_accept: int = 0
    re_reviewed_reject: int = 0
    podcasts_denied: int = 0

    def bump(self, bucket: str, table: str) -> None:
        values = getattr(self, bucket)
        values[table] = values.get(table, 0) + 1


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return str(value)


def _as_evidence(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        value = json.loads(value)
    return dict(value) if isinstance(value, dict) else {"original_evidence": _jsonable(value)}


def _snapshot(row: AttributionRow) -> dict[str, Any]:
    return _jsonable(asdict(row))


def _with_repair_evidence(
    evidence: dict[str, Any],
    *,
    action: str,
    reason: str,
    row: AttributionRow,
    canonical_id: Optional[int],
    absorbed_row: Optional[AttributionRow] = None,
) -> dict[str, Any]:
    result = dict(evidence)
    history = list(result.get("attribution_integrity_repair", []))
    entry: dict[str, Any] = {
        "version": _REPAIR_VERSION,
        "action": action,
        "reason": reason,
        "requested_comedian_id": row.comedian_id,
        "canonical_comedian_id": canonical_id,
        "source_row_id": row.row_id,
    }
    if absorbed_row is not None:
        entry["absorbed_row"] = _snapshot(absorbed_row)
    history.append(entry)
    result["attribution_integrity_repair"] = history
    return result


def _unique_key(row: AttributionRow, canonical_id: int) -> tuple[Any, ...]:
    if row.table == "comedian_podcasts":
        # Accepted ownership also has a cross-source partial unique index.
        return (canonical_id, row.podcast_id, row.role)
    if row.table == "episode_appearances":
        return (canonical_id, row.target_id, row.source)
    return (canonical_id, row.source, row.source_identity)


def plan_repairs(
    rows: Iterable[AttributionRow],
    resolutions: dict[int, Resolution],
) -> list[RepairAction]:
    """Return a deterministic repair plan without touching the database."""

    rows_list = list(rows)
    actions: dict[int, RepairAction] = {}
    eligible_groups: dict[tuple[Any, ...], list[tuple[AttributionRow, Resolution]]] = {}

    for row in rows_list:
        resolution = resolutions.get(row.comedian_id)
        if resolution is None:
            actions[row.row_id] = RepairAction(
                "block", row, None, "comedian resolution missing"
            )
            continue
        reason = resolution.error
        if row.active_podcast_deny:
            reason = "podcast is actively deny-listed"
        if reason:
            actions[row.row_id] = RepairAction(
                "block", row, resolution.canonical_id, reason
            )
            continue
        eligible_groups.setdefault(_unique_key(row, resolution.canonical_id), []).append(
            (row, resolution)
        )

    for group in eligible_groups.values():
        canonical_rows = [item for item in group if item[0].comedian_id == item[1].canonical_id]
        survivor_row, survivor_resolution = min(
            canonical_rows or group,
            key=lambda item: item[0].row_id,
        )
        if survivor_row.comedian_id != survivor_resolution.canonical_id:
            actions[survivor_row.row_id] = RepairAction(
                "canonicalize",
                survivor_row,
                survivor_resolution.canonical_id,
                "alias resolved to eligible canonical comedian",
            )
        else:
            actions[survivor_row.row_id] = RepairAction(
                "unchanged", survivor_row, survivor_resolution.canonical_id, "eligible canonical row"
            )
        for row, resolution in group:
            if row.row_id == survivor_row.row_id:
                continue
            actions[row.row_id] = RepairAction(
                "absorb",
                row,
                resolution.canonical_id,
                "canonicalization uniqueness conflict",
                survivor_id=survivor_row.row_id,
            )

    return [actions[row.row_id] for row in rows_list]


def _load_resolutions(conn: Any) -> dict[int, Resolution]:
    with conn.cursor() as cur:
        cur.execute(_RESOLUTION_SQL)
        rows = cur.fetchall()
    resolutions: dict[int, Resolution] = {}
    for requested_id, canonical_id, name, visible, path, cycle, denied in rows:
        error = None
        if cycle:
            error = "comedian alias cycle"
        elif not visible:
            error = "canonical comedian is hidden"
        elif denied:
            error = "canonical comedian is deny-listed"
        resolutions[int(requested_id)] = Resolution(
            requested_id=int(requested_id),
            canonical_id=int(canonical_id),
            canonical_name=str(name or ""),
            canonical_visible=bool(visible),
            alias_path=tuple(int(value) for value in (path or [])),
            error=error,
        )
    return resolutions


def _load_active_podcast_denies(conn: Any) -> set[int]:
    with conn.cursor() as cur:
        cur.execute(_ACTIVE_PODCAST_DENIES_SQL)
        return {int(row[0]) for row in cur.fetchall()}


def _row_from_db(table: str, raw: tuple[Any, ...], active_denies: set[int]) -> AttributionRow:
    podcast_id = int(raw[2]) if raw[2] is not None else None
    return AttributionRow(
        table=table,
        row_id=int(raw[0]),
        comedian_id=int(raw[1]),
        podcast_id=podcast_id,
        source=str(raw[3]),
        role=str(raw[4] or ""),
        status=str(raw[5]),
        confidence=float(raw[6] or 0.0),
        evidence=_as_evidence(raw[7]),
        reviewed_by=str(raw[8]) if raw[8] is not None else None,
        reviewed_at=raw[9],
        created_at=raw[10],
        updated_at=raw[11],
        source_identity=str(raw[13] or ""),
        target_id=int(raw[14]) if raw[14] is not None and table.startswith("episode_") else None,
        active_podcast_deny=podcast_id in active_denies if podcast_id is not None else False,
    )


def _load_rows(
    conn: Any,
    resolutions: dict[int, Resolution],
    active_denies: set[int],
) -> dict[str, list[AttributionRow]]:
    problem_ids = sorted(
        requested_id
        for requested_id, resolution in resolutions.items()
        if resolution.error or requested_id != resolution.canonical_id
    )
    canonical_targets = sorted(
        {
            resolution.canonical_id
            for resolution in resolutions.values()
            if resolution.requested_id != resolution.canonical_id
        }
    )
    relevant_ids = sorted(set(problem_ids) | set(canonical_targets)) or [-1]
    denied_podcast_ids = sorted(active_denies) or [-1]

    query_specs = (
        ("comedian_podcasts", _OWNERSHIP_SQL, None),
        ("episode_appearances", _APPEARANCE_SQL, (relevant_ids, denied_podcast_ids)),
        ("podcast_candidate_reviews", _OWNERSHIP_REVIEWS_SQL, (relevant_ids, denied_podcast_ids)),
        ("episode_appearance_reviews", _APPEARANCE_REVIEWS_SQL, (relevant_ids, denied_podcast_ids)),
    )
    result: dict[str, list[AttributionRow]] = {}
    with conn.cursor() as cur:
        for table, query, params in query_specs:
            cur.execute(query, params)
            result[table] = [
                _row_from_db(table, raw, active_denies) for raw in cur.fetchall()
            ]
    return result


def _chunks(values: list[Any], size: int = 1000) -> Iterable[list[Any]]:
    for index in range(0, len(values), size):
        yield values[index : index + size]


def _persist_blocked_materialized_batch(
    cur: Any, table: str, actions: list[RepairAction]
) -> None:
    if not actions:
        return
    evidence_rows = []
    for action in actions:
        row = action.row
        evidence = _with_repair_evidence(
            row.evidence,
            action="blocked",
            reason=action.reason,
            row=row,
            canonical_id=action.canonical_id,
        )
        evidence_rows.append((action, json.dumps(evidence, sort_keys=True)))

    if table == "comedian_podcasts":
        values = [
            (
                action.row.comedian_id,
                action.row.podcast_id,
                action.row.source,
                action.row.source_identity,
                action.row.role,
                action.row.confidence,
                evidence_json,
                "task-3908-repair",
            )
            for action, evidence_json in evidence_rows
        ]
        sql = """
            INSERT INTO podcast_candidate_reviews (
                comedian_id, podcast_id, source, source_podcast_id,
                candidate_status, association_type, confidence, evidence,
                reviewed_at, reviewed_by
            )
            VALUES %s
            ON CONFLICT (comedian_id, source, source_podcast_id) DO UPDATE SET
                podcast_id = EXCLUDED.podcast_id,
                candidate_status = 'rejected',
                association_type = EXCLUDED.association_type,
                confidence = EXCLUDED.confidence,
                evidence = EXCLUDED.evidence,
                reviewed_at = NOW(),
                reviewed_by = EXCLUDED.reviewed_by,
                updated_at = NOW()
        """
        template = "(%s, %s, %s, %s, 'rejected', %s, %s, %s::jsonb, NOW(), %s)"
    else:
        values = [
            (
                action.row.comedian_id,
                action.row.target_id,
                action.row.source,
                action.row.source_identity,
                action.row.role,
                action.row.confidence,
                evidence_json,
                "task-3908-repair",
            )
            for action, evidence_json in evidence_rows
        ]
        sql = """
        INSERT INTO episode_appearance_reviews (
            comedian_id, episode_id, source, source_episode_id,
            candidate_status, appearance_role, confidence, evidence,
            reviewed_at, reviewed_by
        )
        VALUES %s
        ON CONFLICT (comedian_id, source, source_episode_id) DO UPDATE SET
            episode_id = EXCLUDED.episode_id,
            candidate_status = 'rejected',
            appearance_role = EXCLUDED.appearance_role,
            confidence = EXCLUDED.confidence,
            evidence = EXCLUDED.evidence,
            reviewed_at = NOW(),
            reviewed_by = EXCLUDED.reviewed_by,
            updated_at = NOW()
        """
        template = "(%s, %s, %s, %s, 'rejected', %s, %s, %s::jsonb, NOW(), %s)"

    for chunk in _chunks(values):
        execute_values(cur, sql, chunk, template=template)
    delete_table = table
    for id_chunk in _chunks([action.row.row_id for action in actions], size=5000):
        cur.execute(f"DELETE FROM {delete_table} WHERE id = ANY(%s::int[])", (id_chunk,))


def _persist_blocked_review_batch(
    cur: Any, table: str, actions: list[RepairAction]
) -> None:
    values = []
    for action in actions:
        row = action.row
        evidence = _with_repair_evidence(
            row.evidence,
            action="rejected",
            reason=action.reason,
            row=row,
            canonical_id=action.canonical_id,
        )
        values.append((row.row_id, json.dumps(evidence, sort_keys=True)))
    sql = f"""
        UPDATE {table} AS target
        SET candidate_status = 'rejected', evidence = repair.evidence::jsonb,
            reviewed_at = NOW(), reviewed_by = 'task-3908-repair', updated_at = NOW()
        FROM (VALUES %s) AS repair(id, evidence)
        WHERE target.id = repair.id::int
    """
    for chunk in _chunks(values):
        execute_values(cur, sql, chunk)


def _persist_canonicalize(cur: Any, action: RepairAction) -> None:
    row = action.row
    conflict_specs = {
        "comedian_podcasts": (
            "podcast_id = %s AND association_type = %s AND source = %s",
            (row.podcast_id, row.role, row.source),
            "review_status <> 'accepted'",
        ),
        "episode_appearances": (
            "episode_id = %s AND source = %s",
            (row.target_id, row.source),
            "review_status <> 'accepted'",
        ),
        "podcast_candidate_reviews": (
            "source = %s AND source_podcast_id = %s",
            (row.source, row.source_identity),
            "candidate_status NOT IN ('accepted', 'pending')",
        ),
        "episode_appearance_reviews": (
            "source = %s AND source_episode_id = %s",
            (row.source, row.source_identity),
            "candidate_status NOT IN ('accepted', 'pending')",
        ),
    }
    key_sql, key_params, inactive_sql = conflict_specs[row.table]
    cur.execute(
        f"""
        DELETE FROM {row.table}
        WHERE comedian_id = %s
          AND {key_sql}
          AND id <> %s
          AND {inactive_sql}
        RETURNING to_jsonb({row.table}.*)
        """,
        (action.canonical_id, *key_params, row.row_id),
    )
    displaced_conflicts = [result[0] for result in cur.fetchall()]
    evidence = _with_repair_evidence(
        row.evidence,
        action="canonicalized",
        reason=action.reason,
        row=row,
        canonical_id=action.canonical_id,
    )
    if displaced_conflicts:
        evidence["attribution_integrity_repair"][-1]["displaced_inactive_conflicts"] = (
            _jsonable(displaced_conflicts)
        )
    cur.execute(
        f"""
        UPDATE {row.table}
        SET comedian_id = %s, evidence = %s::jsonb, updated_at = NOW()
        WHERE id = %s
        """,
        (action.canonical_id, json.dumps(evidence, sort_keys=True), row.row_id),
    )


def _persist_absorb(
    cur: Any,
    action: RepairAction,
    survivors: dict[tuple[str, int], AttributionRow],
) -> None:
    assert action.survivor_id is not None
    survivor = survivors[(action.row.table, action.survivor_id)]
    cur.execute(
        f"SELECT evidence FROM {action.row.table} WHERE id = %s FOR UPDATE",
        (action.survivor_id,),
    )
    current = cur.fetchone()
    survivor_evidence = _as_evidence(current[0]) if current else survivor.evidence
    evidence = _with_repair_evidence(
        survivor_evidence,
        action="absorbed_conflict",
        reason=action.reason,
        row=survivor,
        canonical_id=action.canonical_id,
        absorbed_row=action.row,
    )
    cur.execute(
        f"UPDATE {action.row.table} SET evidence = %s::jsonb, updated_at = NOW() WHERE id = %s",
        (json.dumps(evidence, sort_keys=True), action.survivor_id),
    )
    cur.execute(f"DELETE FROM {action.row.table} WHERE id = %s", (action.row.row_id,))


def _apply_re_review_decisions(
    conn: Any,
    decisions_path: Path,
    reviewer: str,
    summary: RepairSummary,
) -> None:
    with conn.cursor() as cur:
        cur.execute(_OWNERSHIP_REVIEW_EXPORT_SQL)
        current_rows = {int(row[0]): row for row in cur.fetchall()}

    with decisions_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or [])
        if not {"comedian_podcast_id", "decision", "reason"}.issubset(fieldnames):
            raise ValueError("re-review CSV requires comedian_podcast_id, decision, and reason")
        decisions: dict[int, tuple[str, str]] = {}
        for line_number, row in enumerate(reader, start=2):
            row_id = int((row.get("comedian_podcast_id") or "0").strip())
            decision = (row.get("decision") or "").strip().lower()
            reason = (row.get("reason") or "").strip()
            if row_id in decisions:
                raise ValueError(f"duplicate comedian_podcast_id {row_id} on line {line_number}")
            if decision not in _REVIEW_DECISIONS:
                raise ValueError(f"invalid decision {decision!r} on line {line_number}")
            if not reason:
                raise ValueError(f"missing reason on line {line_number}")
            decisions[row_id] = (decision, reason)

    missing = sorted(set(current_rows) - set(decisions))
    unknown = sorted(set(decisions) - set(current_rows))
    if missing or unknown:
        raise ValueError(
            f"re-review coverage mismatch: missing={missing[:10]} unknown={unknown[:10]}"
        )

    with conn.cursor() as cur:
        for row_id, (decision, reason) in decisions.items():
            current = current_rows[row_id]
            evidence = _as_evidence(current[14])
            evidence["task_3908_re_review"] = {
                "version": _REPAIR_VERSION,
                "decision": decision,
                "reason": reason,
                "reviewed_by": reviewer,
            }
            if decision == "accept":
                summary.re_reviewed_accept += 1
                cur.execute(
                    """
                    UPDATE comedian_podcasts
                    SET evidence = %s::jsonb, reviewed_at = NOW(), reviewed_by = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (json.dumps(evidence, sort_keys=True), reviewer, row_id),
                )
                continue

            summary.re_reviewed_reject += 1
            cur.execute(
                """
                UPDATE comedian_podcasts
                SET review_status = 'rejected', evidence = %s::jsonb,
                    reviewed_at = NOW(), reviewed_by = %s, updated_at = NOW()
                WHERE id = %s
                """,
                (json.dumps(evidence, sort_keys=True), reviewer, row_id),
            )
            if decision == "deny_podcast":
                summary.podcasts_denied += 1
                cur.execute(
                    """
                    INSERT INTO podcast_deny_list (podcast_id, reason, denied_by)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (podcast_id) DO UPDATE SET
                        reason = EXCLUDED.reason,
                        denied_by = EXCLUDED.denied_by,
                        denied_at = NOW(),
                        restored_at = NULL,
                        restored_by = NULL,
                        updated_at = NOW()
                    """,
                    (int(current[5]), reason, reviewer),
                )


def export_re_review(conn: Any, output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with conn.cursor() as cur:
        cur.execute(_OWNERSHIP_REVIEW_EXPORT_SQL)
        rows = cur.fetchall()
    columns = [
        "comedian_podcast_id",
        "comedian_id",
        "comedian_name",
        "parent_comedian_id",
        "comedian_visible",
        "podcast_id",
        "podcast_title",
        "podcast_author",
        "feed_url",
        "website_url",
        "association_type",
        "source",
        "previous_reviewer",
        "confidence",
        "decision",
        "reason",
        "evidence",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        for row in rows:
            writer.writerow([*row[:14], "", "", json.dumps(_jsonable(row[14]), sort_keys=True)])
    return len(rows)


def verify(conn: Any) -> dict[str, int]:
    with conn.cursor() as cur:
        cur.execute(_VERIFY_SQL)
        return {str(metric): int(value) for metric, value in cur.fetchall()}


def repair(
    *,
    apply: bool,
    decisions_path: Optional[Path] = None,
    reviewer: str = "task-3908-repair",
    transaction_factory: Callable[[], Any] = get_transaction,
) -> tuple[RepairSummary, dict[str, int]]:
    summary = RepairSummary()
    with transaction_factory() as conn:
        if decisions_path is not None:
            _apply_re_review_decisions(conn, decisions_path, reviewer, summary)

        resolutions = _load_resolutions(conn)
        active_denies = _load_active_podcast_denies(conn)
        rows_by_table = _load_rows(conn, resolutions, active_denies)
        actions_by_table = {
            table: plan_repairs(rows, resolutions) for table, rows in rows_by_table.items()
        }

        for table, actions in actions_by_table.items():
            for action in actions:
                bucket = {
                    "block": "blocked",
                    "canonicalize": "canonicalized",
                    "absorb": "absorbed",
                    "unchanged": "unchanged",
                }[action.kind]
                summary.bump(bucket, table)

        if apply:
            survivors = {
                (row.table, row.row_id): row
                for rows in rows_by_table.values()
                for row in rows
            }
            with conn.cursor() as cur:
                # Delete/merge conflict losers before canonicalizing survivors so
                # both the full and partial unique indexes remain satisfied.
                for actions in actions_by_table.values():
                    for action in actions:
                        if action.kind == "absorb":
                            _persist_absorb(cur, action, survivors)
                for table, actions in actions_by_table.items():
                    blocked = [action for action in actions if action.kind == "block"]
                    if table in {"comedian_podcasts", "episode_appearances"}:
                        _persist_blocked_materialized_batch(cur, table, blocked)
                    else:
                        _persist_blocked_review_batch(cur, table, blocked)
                    for action in actions:
                        if action.kind == "canonicalize":
                            _persist_canonicalize(cur, action)

            verification = verify(conn)
            if any(verification.values()):
                raise RuntimeError(f"post-repair verification failed: {verification}")
        else:
            verification = {}
            conn.rollback()
    return summary, verification


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Repair canonical podcast attribution. Defaults to dry-run; use --apply "
            "only after reviewing the complete plan."
        )
    )
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--export-re-review", type=Path)
    parser.add_argument("--re-review-decisions", type=Path)
    parser.add_argument("--reviewer", default=os.environ.get("USER") or "task-3908-repair")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.export_re_review:
        with get_connection() as conn:
            count = export_re_review(conn, args.export_re_review)
        print(json.dumps({"exported": count, "path": str(args.export_re_review)}, indent=2))
        return 0
    if args.verify:
        with get_connection() as conn:
            result = verify(conn)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 1 if any(result.values()) else 0

    summary, verification = repair(
        apply=args.apply,
        decisions_path=args.re_review_decisions,
        reviewer=args.reviewer,
    )
    print(
        json.dumps(
            {
                "mode": "apply" if args.apply else "dry_run",
                "summary": asdict(summary),
                "verification": verification,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
