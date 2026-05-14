#!/usr/bin/env python3
"""Batch review podcast candidates from the discovery audit log.

Two-step workflow:

    1. ``export`` — read the discovery audit JSONL (written by
       ``populate_comedian_podcast_appearances.py``) plus current DB state, and
       write a CSV with one row per ``(comedian, podcast feed)`` candidate
       awaiting review. The CSV includes blank ``decision`` / ``review_reason``
       columns for spreadsheet editing.

    2. ``apply`` — read decisions back (either the full exported CSV or a
       compact ``candidate_id,decision[,review_reason]`` CSV), validate, and
       upsert ``comedian_podcast_identity_links``. Accepted candidates also
       materialize ``comedian_podcast_appearances`` rows from the cached audit
       data so the reviewed feed shows up immediately without re-running
       discovery.

Usage:
    python -m scripts.core.review_podcast_candidates export \
        --audit-path tmp/podcast_index_low_confidence.jsonl \
        --output review.csv

    python -m scripts.core.review_podcast_candidates apply \
        --input review.csv --dry-run

    python -m scripts.core.review_podcast_candidates apply \
        --input review.csv --confirm --reviewer matt
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from psycopg2.extras import execute_values

from laughtrack.adapters.db import get_connection, get_transaction

_SOURCE = "podcast_index"

_DECISION_ACCEPT = "accept"
_DECISION_REJECT = "reject"
_DECISION_IGNORE = "ignore"
_DECISION_TO_STATUS = {
    _DECISION_ACCEPT: "verified",
    _DECISION_REJECT: "rejected",
    _DECISION_IGNORE: "ambiguous",
}
_VALID_DECISIONS = frozenset(_DECISION_TO_STATUS)
_PENDING_STATUS = "pending"

_FULL_EXPORT_COLUMNS = [
    "candidate_id",
    "comedian_id",
    "comedian_name",
    "matched_name",
    "normalized_match",
    "feed_id",
    "podcast_title",
    "author",
    "feed_url",
    "confidence",
    "current_status",
    "decision",
    "review_reason",
    "evidence",
]

_DEFAULT_AUDIT_PATH = Path("tmp/podcast_index_low_confidence.jsonl")


@dataclass(frozen=True)
class PendingCandidate:
    candidate_id: str
    comedian_id: int
    comedian_name: str
    matched_name: str
    normalized_match: str
    source_feed_id: str
    podcast_title: str
    author: str
    feed_url: str
    confidence: float
    current_status: str
    evidence: dict[str, Any]


@dataclass(frozen=True)
class DecisionRow:
    row_number: int
    candidate_id: str
    decision: str
    review_reason: str


@dataclass(frozen=True)
class ApplyError:
    row_number: int
    message: str


@dataclass
class ApplySummary:
    accepted: int = 0
    rejected: int = 0
    ignored: int = 0
    skipped: int = 0
    errored: int = 0
    appearances_written: int = 0


def _candidate_id(comedian_id: int, source_feed_id: str) -> str:
    return f"{comedian_id}:{source_feed_id}"


def _parse_candidate_id(candidate_id: str) -> Optional[tuple[int, str]]:
    if not candidate_id or ":" not in candidate_id:
        return None
    comedian_str, feed_str = candidate_id.split(":", 1)
    try:
        return int(comedian_str), feed_str
    except ValueError:
        return None


def _read_audit_rows(audit_path: Path) -> list[dict[str, Any]]:
    if not audit_path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with audit_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows


def _aggregate_by_candidate(audit_rows: Iterable[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in audit_rows:
        evidence = row.get("match_evidence") or {}
        feed_id = evidence.get("source_feed_id")
        comedian_id = row.get("comedian_id")
        if comedian_id is None or not feed_id:
            continue
        try:
            cid = int(comedian_id)
        except (TypeError, ValueError):
            continue
        key = _candidate_id(cid, str(feed_id))
        grouped.setdefault(key, []).append(row)
    return grouped


def _representative_appearance(appearances: list[dict[str, Any]]) -> dict[str, Any]:
    return max(appearances, key=lambda r: float(r.get("match_confidence") or 0.0))


def _load_identity_link_statuses(
    conn: Any, candidate_keys: list[tuple[int, str]]
) -> dict[tuple[int, str], str]:
    if not candidate_keys:
        return {}
    comedian_ids = sorted({key[0] for key in candidate_keys})
    statuses: dict[tuple[int, str], str] = {}
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT comedian_id, source_feed_id, LOWER(review_status)
            FROM comedian_podcast_identity_links
            WHERE comedian_id = ANY(%s::int[])
              AND source = %s
            """,
            (comedian_ids, _SOURCE),
        )
        for row in cur.fetchall():
            cid = int(row[0])
            feed = str(row[1])
            status = str(row[2])
            statuses[(cid, feed)] = status
    return statuses


def _load_comedian_names(conn: Any, comedian_ids: list[int]) -> dict[int, str]:
    if not comedian_ids:
        return {}
    unique_ids = sorted({int(cid) for cid in comedian_ids})
    names: dict[int, str] = {}
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, name FROM comedians WHERE id = ANY(%s::int[])",
            (unique_ids,),
        )
        for row in cur.fetchall():
            names[int(row[0])] = str(row[1])
    return names


def _build_pending_candidate(
    candidate_id: str,
    appearances: list[dict[str, Any]],
    comedian_names: dict[int, str],
    identity_links: dict[tuple[int, str], str],
) -> Optional[PendingCandidate]:
    if not appearances:
        return None
    rep = _representative_appearance(appearances)
    evidence = dict(rep.get("match_evidence") or {})
    try:
        comedian_id = int(rep.get("comedian_id"))
    except (TypeError, ValueError):
        return None
    source_feed_id = str(evidence.get("source_feed_id") or "")
    if not source_feed_id:
        return None
    matched_terms = evidence.get("matched_terms") or []
    if not isinstance(matched_terms, list):
        matched_terms = []
    feed_url = str(evidence.get("source_feed_url") or evidence.get("feed_url") or "")
    author = str(evidence.get("author") or evidence.get("feed_author") or "")
    return PendingCandidate(
        candidate_id=candidate_id,
        comedian_id=comedian_id,
        comedian_name=comedian_names.get(comedian_id, ""),
        matched_name=str(rep.get("episode_title") or evidence.get("episode_title") or ""),
        normalized_match=", ".join(str(t) for t in matched_terms),
        source_feed_id=source_feed_id,
        podcast_title=str(rep.get("podcast_name") or evidence.get("podcast_name") or ""),
        author=author,
        feed_url=feed_url,
        confidence=float(rep.get("match_confidence") or 0.0),
        current_status=identity_links.get((comedian_id, source_feed_id), _PENDING_STATUS),
        evidence=evidence,
    )


def _build_candidates(
    audit_rows: list[dict[str, Any]],
    *,
    connection_factory: Any = None,
) -> tuple[list[PendingCandidate], dict[str, list[dict[str, Any]]]]:
    if connection_factory is None:
        connection_factory = get_connection
    grouped = _aggregate_by_candidate(audit_rows)
    keys: set[tuple[int, str]] = set()
    for candidate_id in grouped.keys():
        parsed = _parse_candidate_id(candidate_id)
        if parsed is not None:
            keys.add(parsed)
    sorted_keys = sorted(keys)

    with connection_factory() as conn:
        identity_links = _load_identity_link_statuses(conn, sorted_keys)
        comedian_names = _load_comedian_names(conn, [cid for cid, _ in sorted_keys])

    candidates: list[PendingCandidate] = []
    for candidate_id, appearances in grouped.items():
        candidate = _build_pending_candidate(
            candidate_id, appearances, comedian_names, identity_links
        )
        if candidate is not None:
            candidates.append(candidate)
    candidates.sort(key=lambda c: (-c.confidence, c.comedian_id, c.candidate_id))
    return candidates, grouped


def _export(
    audit_path: Path,
    output_path: Path,
    *,
    include_resolved: bool = False,
    limit: Optional[int] = None,
    connection_factory: Any = None,
) -> int:
    if connection_factory is None:
        connection_factory = get_connection
    audit_rows = _read_audit_rows(audit_path)
    candidates, _ = _build_candidates(audit_rows, connection_factory=connection_factory)
    if not include_resolved:
        candidates = [c for c in candidates if c.current_status == _PENDING_STATUS]
    if limit is not None and limit > 0:
        candidates = candidates[:limit]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(_FULL_EXPORT_COLUMNS)
        for c in candidates:
            writer.writerow(
                [
                    c.candidate_id,
                    c.comedian_id,
                    c.comedian_name,
                    c.matched_name,
                    c.normalized_match,
                    c.source_feed_id,
                    c.podcast_title,
                    c.author,
                    c.feed_url,
                    f"{c.confidence:.2f}",
                    c.current_status,
                    "",
                    "",
                    json.dumps(c.evidence, sort_keys=True),
                ]
            )
    return len(candidates)


def _read_decision_csv(path: Path) -> tuple[list[DecisionRow], list[ApplyError]]:
    decisions: list[DecisionRow] = []
    errors: list[ApplyError] = []
    if not path.exists():
        return decisions, [ApplyError(1, f"input CSV not found: {path}")]
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            return decisions, [ApplyError(1, "CSV is empty")]
        headers_lower = {h.strip().lower(): h for h in reader.fieldnames if h}
        if "candidate_id" not in headers_lower or "decision" not in headers_lower:
            return decisions, [
                ApplyError(
                    1,
                    "CSV missing required columns; need at least 'candidate_id' and 'decision'",
                )
            ]
        cid_key = headers_lower["candidate_id"]
        decision_key = headers_lower["decision"]
        reason_key = headers_lower.get("review_reason")
        for row_index, row in enumerate(reader, start=2):
            cid = (row.get(cid_key) or "").strip()
            decision = (row.get(decision_key) or "").strip().lower()
            reason = (row.get(reason_key) or "").strip() if reason_key else ""
            if not cid:
                errors.append(ApplyError(row_index, "missing candidate_id"))
                continue
            decisions.append(DecisionRow(row_index, cid, decision, reason))
    return decisions, errors


_INSERT_IDENTITY_LINK_SQL = """
    INSERT INTO comedian_podcast_identity_links (
        comedian_id, source, source_feed_id, source_feed_url, source_feed_name,
        review_status, review_evidence, reviewed_at, reviewed_by
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, NOW(), %s)
    ON CONFLICT (comedian_id, source, source_feed_id) DO UPDATE SET
        review_status = EXCLUDED.review_status,
        review_evidence = EXCLUDED.review_evidence,
        source_feed_url = COALESCE(EXCLUDED.source_feed_url, comedian_podcast_identity_links.source_feed_url),
        source_feed_name = COALESCE(EXCLUDED.source_feed_name, comedian_podcast_identity_links.source_feed_name),
        reviewed_at = EXCLUDED.reviewed_at,
        reviewed_by = EXCLUDED.reviewed_by,
        updated_at = NOW()
"""

_INSERT_APPEARANCE_SQL = """
    INSERT INTO comedian_podcast_appearances (
        comedian_id, source, source_episode_id, podcast_name,
        episode_title, release_date, episode_url,
        match_confidence, match_evidence
    )
    VALUES %s
    ON CONFLICT (comedian_id, source, source_episode_id) DO UPDATE SET
        podcast_name = EXCLUDED.podcast_name,
        episode_title = EXCLUDED.episode_title,
        release_date = EXCLUDED.release_date,
        episode_url = EXCLUDED.episode_url,
        match_confidence = EXCLUDED.match_confidence,
        match_evidence = EXCLUDED.match_evidence,
        updated_at = NOW()
"""

_APPEARANCE_VALUES_TEMPLATE = "(%s, %s, %s, %s, %s, %s::timestamptz, %s, %s, %s::jsonb)"


def _upsert_identity_link(
    conn: Any, candidate: PendingCandidate, status: str, reviewer: str, reason: str
) -> None:
    evidence = dict(candidate.evidence or {})
    if reason:
        evidence["review_reason"] = reason
    with conn.cursor() as cur:
        cur.execute(
            _INSERT_IDENTITY_LINK_SQL,
            (
                candidate.comedian_id,
                _SOURCE,
                candidate.source_feed_id,
                candidate.feed_url or None,
                candidate.podcast_title or None,
                status,
                json.dumps(evidence, sort_keys=True),
                reviewer or None,
            ),
        )


def _insert_appearance_rows(conn: Any, appearance_rows: list[dict[str, Any]]) -> int:
    if not appearance_rows:
        return 0
    values: list[tuple[Any, ...]] = []
    for row in appearance_rows:
        evidence = row.get("match_evidence") or {}
        try:
            comedian_id = int(row.get("comedian_id"))
        except (TypeError, ValueError):
            continue
        source_episode_id = row.get("source_episode_id")
        if not source_episode_id:
            continue
        values.append(
            (
                comedian_id,
                row.get("source") or _SOURCE,
                str(source_episode_id),
                row.get("podcast_name") or "",
                row.get("episode_title") or "",
                row.get("release_date"),
                row.get("episode_url") or "",
                float(row.get("match_confidence") or 0.0),
                json.dumps(evidence, sort_keys=True),
            )
        )
    if not values:
        return 0
    with conn.cursor() as cur:
        execute_values(cur, _INSERT_APPEARANCE_SQL, values, template=_APPEARANCE_VALUES_TEMPLATE)
    return len(values)


@dataclass
class _PlannedAction:
    decision: DecisionRow
    candidate: PendingCandidate
    appearances: list[dict[str, Any]] = field(default_factory=list)


def _apply(
    decisions_path: Path,
    audit_path: Path,
    *,
    dry_run: bool,
    force: bool,
    reviewer: str,
    connection_factory: Any = None,
    transaction_factory: Any = None,
) -> tuple[ApplySummary, list[ApplyError]]:
    if connection_factory is None:
        connection_factory = get_connection
    if transaction_factory is None:
        transaction_factory = get_transaction
    decisions, parse_errors = _read_decision_csv(decisions_path)

    summary = ApplySummary()
    errors: list[ApplyError] = list(parse_errors)
    summary.errored = len(errors)
    if parse_errors:
        return summary, errors

    audit_rows = _read_audit_rows(audit_path)
    if not audit_rows and not audit_path.exists():
        errors.append(
            ApplyError(
                1,
                f"audit log not found: {audit_path}; "
                "candidate lookups cannot resolve. Re-run discovery "
                "or pass --audit-path to the correct JSONL.",
            )
        )
        summary.errored += 1
        return summary, errors

    candidates, grouped_appearances = _build_candidates(
        audit_rows, connection_factory=connection_factory
    )
    candidates_by_id = {c.candidate_id: c for c in candidates}

    planned_accepts: list[_PlannedAction] = []
    planned_rejects: list[_PlannedAction] = []
    planned_ignores: list[_PlannedAction] = []
    decided_rows: dict[str, int] = {}

    for decision in decisions:
        if not decision.decision:
            summary.skipped += 1
            continue
        if decision.decision not in _VALID_DECISIONS:
            errors.append(
                ApplyError(
                    decision.row_number,
                    f"unknown decision {decision.decision!r}; "
                    f"expected one of {sorted(_VALID_DECISIONS)}",
                )
            )
            summary.errored += 1
            continue
        parsed = _parse_candidate_id(decision.candidate_id)
        if parsed is None:
            errors.append(
                ApplyError(
                    decision.row_number,
                    f"malformed candidate_id {decision.candidate_id!r}; "
                    "expected '<comedian_id>:<source_feed_id>'",
                )
            )
            summary.errored += 1
            continue
        candidate = candidates_by_id.get(decision.candidate_id)
        if candidate is None:
            errors.append(
                ApplyError(
                    decision.row_number,
                    f"unknown candidate_id {decision.candidate_id!r}; "
                    "not found in audit log or current identity links",
                )
            )
            summary.errored += 1
            continue
        if candidate.current_status != _PENDING_STATUS and not force:
            errors.append(
                ApplyError(
                    decision.row_number,
                    f"candidate {decision.candidate_id} is already "
                    f"{candidate.current_status!r}; pass --force to override",
                )
            )
            summary.errored += 1
            continue
        prior_row = decided_rows.get(decision.candidate_id)
        if prior_row is not None:
            errors.append(
                ApplyError(
                    decision.row_number,
                    f"candidate {decision.candidate_id} already decided in row "
                    f"{prior_row}; remove the duplicate before applying",
                )
            )
            summary.errored += 1
            continue
        decided_rows[decision.candidate_id] = decision.row_number
        action = _PlannedAction(
            decision=decision,
            candidate=candidate,
            appearances=grouped_appearances.get(decision.candidate_id, []),
        )
        if decision.decision == _DECISION_ACCEPT:
            planned_accepts.append(action)
        elif decision.decision == _DECISION_REJECT:
            planned_rejects.append(action)
        elif decision.decision == _DECISION_IGNORE:
            planned_ignores.append(action)

    summary.accepted = len(planned_accepts)
    summary.rejected = len(planned_rejects)
    summary.ignored = len(planned_ignores)

    if dry_run:
        summary.appearances_written = sum(len(p.appearances) for p in planned_accepts)
        return summary, errors

    with transaction_factory() as conn:
        for plan in planned_accepts:
            _upsert_identity_link(
                conn,
                plan.candidate,
                _DECISION_TO_STATUS[_DECISION_ACCEPT],
                reviewer,
                plan.decision.review_reason,
            )
            summary.appearances_written += _insert_appearance_rows(conn, plan.appearances)
        for plan in planned_rejects:
            _upsert_identity_link(
                conn,
                plan.candidate,
                _DECISION_TO_STATUS[_DECISION_REJECT],
                reviewer,
                plan.decision.review_reason,
            )
        for plan in planned_ignores:
            _upsert_identity_link(
                conn,
                plan.candidate,
                _DECISION_TO_STATUS[_DECISION_IGNORE],
                reviewer,
                plan.decision.review_reason,
            )

    return summary, errors


def _print_apply_report(
    summary: ApplySummary, errors: list[ApplyError], *, dry_run: bool
) -> None:
    if errors:
        print("Validation problems:")
        for err in errors:
            print(f"  row {err.row_number}: {err.message}")
    prefix = "DRY RUN — " if dry_run else ""
    print(
        f"{prefix}Summary: {summary.accepted} accepted, "
        f"{summary.rejected} rejected, {summary.ignored} ignored, "
        f"{summary.skipped} skipped, {summary.errored} errored"
    )
    if summary.appearances_written:
        verb = "would materialize" if dry_run else "materialized"
        print(f"  {verb} {summary.appearances_written} comedian_podcast_appearances row(s)")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Batch review podcast candidates from the discovery audit log",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_export = sub.add_parser(
        "export", help="Write pending candidates to a CSV for spreadsheet review"
    )
    p_export.add_argument(
        "--audit-path",
        type=Path,
        default=_DEFAULT_AUDIT_PATH,
        help="JSONL audit log produced by populate_comedian_podcast_appearances",
    )
    p_export.add_argument("--output", type=Path, required=True, help="CSV output path")
    p_export.add_argument(
        "--include-resolved",
        action="store_true",
        help="Also include candidates that already have an identity link decision",
    )
    p_export.add_argument(
        "--limit", type=int, default=None, help="Cap number of rows written"
    )

    p_apply = sub.add_parser("apply", help="Apply decisions from a reviewed CSV")
    p_apply.add_argument("--input", type=Path, required=True, help="Reviewed CSV path")
    p_apply.add_argument(
        "--audit-path",
        type=Path,
        default=_DEFAULT_AUDIT_PATH,
        help="JSONL audit log (re-read so accepted candidates can materialize)",
    )
    mode = p_apply.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--dry-run", action="store_true", help="Preview decisions without writing"
    )
    mode.add_argument(
        "--confirm", action="store_true", help="Apply decisions to the database"
    )
    p_apply.add_argument(
        "--force",
        action="store_true",
        help="Allow mutating candidates that already have a decision",
    )
    p_apply.add_argument(
        "--reviewer",
        default=None,
        help="reviewed_by tag recorded on identity_link rows (default: $USER)",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "export":
        written = _export(
            audit_path=args.audit_path,
            output_path=args.output,
            include_resolved=args.include_resolved,
            limit=args.limit,
        )
        print(f"Wrote {written} candidate(s) to {args.output}")
        return 0

    if args.command == "apply":
        reviewer = args.reviewer or os.environ.get("USER") or ""
        summary, errors = _apply(
            decisions_path=args.input,
            audit_path=args.audit_path,
            dry_run=args.dry_run,
            force=args.force,
            reviewer=reviewer,
        )
        _print_apply_report(summary, errors, dry_run=args.dry_run)
        return 2 if summary.errored else 0

    parser.error(f"unknown command {args.command!r}")
    return 2  # unreachable, parser.error exits


if __name__ == "__main__":
    sys.exit(main())
