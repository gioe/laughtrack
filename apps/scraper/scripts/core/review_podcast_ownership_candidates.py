#!/usr/bin/env python3
"""Export and apply review decisions for podcast ownership candidates."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from laughtrack.adapters.db import get_connection, get_transaction

_DECISION_ACCEPT = "accept"
_DECISION_REJECT = "reject"
_DECISION_IGNORE = "ignore"
_VALID_DECISIONS = frozenset({_DECISION_ACCEPT, _DECISION_REJECT, _DECISION_IGNORE})
_DECISION_TO_STATUS = {
    _DECISION_ACCEPT: "accepted",
    _DECISION_REJECT: "rejected",
    _DECISION_IGNORE: "ignored",
}
_PENDING_STATUS = "pending"

_FULL_EXPORT_COLUMNS = [
    "candidate_id",
    "comedian_id",
    "comedian_name",
    "podcast_id",
    "source_podcast_id",
    "podcast_title",
    "author_name",
    "feed_url",
    "website_url",
    "association_type",
    "confidence",
    "current_status",
    "decision",
    "review_reason",
    "evidence",
]

_LOAD_CANDIDATES_SQL = """
    SELECT
        pcr.id,
        pcr.comedian_id,
        c.name,
        pcr.podcast_id,
        pcr.source,
        pcr.source_podcast_id,
        pcr.candidate_status,
        COALESCE(NULLIF(pcr.association_type, ''), 'host') AS association_type,
        pcr.confidence,
        p.title AS podcast_title,
        p.author_name,
        p.feed_url,
        p.website_url,
        pcr.evidence
    FROM podcast_candidate_reviews pcr
    JOIN comedians c ON c.id = pcr.comedian_id
    LEFT JOIN podcasts p ON p.id = pcr.podcast_id
    WHERE (%s::boolean OR pcr.candidate_status = 'pending')
    ORDER BY pcr.confidence DESC, pcr.id
    {limit_clause}
"""

_UPDATE_REVIEW_SQL = """
    UPDATE podcast_candidate_reviews
    SET candidate_status = %s,
        association_type = %s,
        confidence = %s,
        evidence = %s::jsonb,
        reviewed_at = NOW(),
        reviewed_by = %s,
        updated_at = NOW()
    WHERE id = %s
"""

_UPSERT_OWNERSHIP_SQL = """
    INSERT INTO comedian_podcasts (
        comedian_id,
        podcast_id,
        association_type,
        source,
        review_status,
        confidence,
        reviewed_by,
        reviewed_at,
        evidence
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), %s::jsonb)
    ON CONFLICT (comedian_id, podcast_id, association_type, source) DO UPDATE SET
        review_status = EXCLUDED.review_status,
        confidence = EXCLUDED.confidence,
        reviewed_by = EXCLUDED.reviewed_by,
        reviewed_at = EXCLUDED.reviewed_at,
        evidence = EXCLUDED.evidence,
        updated_at = NOW()
"""


@dataclass(frozen=True)
class OwnershipCandidate:
    candidate_id: int
    comedian_id: int
    comedian_name: str
    podcast_id: Optional[int]
    source: str
    source_podcast_id: str
    current_status: str
    association_type: str
    confidence: float
    podcast_title: str
    author_name: str
    feed_url: str
    website_url: str
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
    ownership_rows_written: int = 0


def _load_candidates(*, include_resolved: bool = False, limit: Optional[int] = None) -> list[OwnershipCandidate]:
    limit_clause = "LIMIT %s" if limit else ""
    params: list[Any] = [include_resolved]
    if limit:
        params.append(int(limit))
    query = _LOAD_CANDIDATES_SQL.format(limit_clause=limit_clause)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, tuple(params))
            rows = cur.fetchall()
    candidates: list[OwnershipCandidate] = []
    for row in rows:
        evidence = row[13] or {}
        if isinstance(evidence, str):
            evidence = json.loads(evidence)
        podcast_id = int(row[3]) if row[3] is not None else None
        candidates.append(
            OwnershipCandidate(
                candidate_id=int(row[0]),
                comedian_id=int(row[1]),
                comedian_name=str(row[2] or ""),
                podcast_id=podcast_id,
                source=str(row[4]),
                source_podcast_id=str(row[5]),
                current_status=str(row[6]),
                association_type=str(row[7] or "host"),
                confidence=float(row[8] or 0.0),
                podcast_title=str(row[9] or ""),
                author_name=str(row[10] or ""),
                feed_url=str(row[11] or ""),
                website_url=str(row[12] or ""),
                evidence=dict(evidence),
            )
        )
    return candidates


def _export(*, output_path: Path, include_resolved: bool = False, limit: Optional[int] = None) -> int:
    candidates = _load_candidates(include_resolved=include_resolved, limit=limit)
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
                    c.podcast_id or "",
                    c.source_podcast_id,
                    c.podcast_title,
                    c.author_name,
                    c.feed_url,
                    c.website_url,
                    c.association_type,
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
                ApplyError(1, "CSV missing required columns; need 'candidate_id' and 'decision'")
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


def _apply(
    *,
    decisions_path: Path,
    dry_run: bool,
    force: bool,
    reviewer: str,
    transaction_factory: Any = None,
) -> Any:
    if transaction_factory is None:
        transaction_factory = get_transaction
    decisions, parse_errors = _read_decision_csv(decisions_path)
    summary = ApplySummary(errored=len(parse_errors))
    errors = list(parse_errors)
    if parse_errors:
        return summary, errors

    candidates = _load_candidates(include_resolved=True)
    candidates_by_id = {str(c.candidate_id): c for c in candidates}
    planned: list[tuple[DecisionRow, OwnershipCandidate]] = []
    decided_rows: dict[str, int] = {}

    for decision in decisions:
        if not decision.decision:
            summary.skipped += 1
            continue
        if decision.decision not in _VALID_DECISIONS:
            errors.append(
                ApplyError(
                    decision.row_number,
                    f"unknown decision {decision.decision!r}; expected one of {sorted(_VALID_DECISIONS)}",
                )
            )
            summary.errored += 1
            continue
        prior_row = decided_rows.get(decision.candidate_id)
        if prior_row is not None:
            errors.append(
                ApplyError(
                    decision.row_number,
                    f"candidate {decision.candidate_id} already decided in row {prior_row}; remove the duplicate",
                )
            )
            summary.errored += 1
            continue
        decided_rows[decision.candidate_id] = decision.row_number
        candidate = candidates_by_id.get(decision.candidate_id)
        if candidate is None:
            errors.append(
                ApplyError(
                    decision.row_number,
                    f"unknown candidate_id {decision.candidate_id!r}; not found in current candidates",
                )
            )
            summary.errored += 1
            continue
        if candidate.current_status != _PENDING_STATUS and not force:
            errors.append(
                ApplyError(
                    decision.row_number,
                    f"candidate {decision.candidate_id} is already {candidate.current_status!r}; pass --force to override",
                )
            )
            summary.errored += 1
            continue
        if decision.decision == _DECISION_ACCEPT and candidate.podcast_id is None:
            errors.append(
                ApplyError(
                    decision.row_number,
                    f"candidate {decision.candidate_id} has no podcast_id; cannot materialize ownership",
                )
            )
            summary.errored += 1
            continue
        planned.append((decision, candidate))

    summary.accepted = sum(1 for decision, _ in planned if decision.decision == _DECISION_ACCEPT)
    summary.rejected = sum(1 for decision, _ in planned if decision.decision == _DECISION_REJECT)
    summary.ignored = sum(1 for decision, _ in planned if decision.decision == _DECISION_IGNORE)
    summary.ownership_rows_written = summary.accepted

    if dry_run or errors:
        return summary, errors

    with transaction_factory() as conn:
        for decision, candidate in planned:
            status = _DECISION_TO_STATUS[decision.decision]
            evidence = dict(candidate.evidence)
            if decision.review_reason:
                evidence["review_reason"] = decision.review_reason
            evidence_json = json.dumps(evidence, sort_keys=True)
            with conn.cursor() as cur:
                cur.execute(
                    _UPDATE_REVIEW_SQL,
                    (
                        status,
                        candidate.association_type,
                        candidate.confidence,
                        evidence_json,
                        reviewer or None,
                        candidate.candidate_id,
                    ),
                )
                if decision.decision == _DECISION_ACCEPT:
                    cur.execute(
                        _UPSERT_OWNERSHIP_SQL,
                        (
                            candidate.comedian_id,
                            candidate.podcast_id,
                            candidate.association_type,
                            candidate.source,
                            "accepted",
                            candidate.confidence,
                            reviewer or None,
                            evidence_json,
                        ),
                    )
    return summary, errors


def _print_apply_report(summary: ApplySummary, errors: list[ApplyError], *, dry_run: bool) -> None:
    if errors:
        print("Validation problems:")
        for err in errors:
            print(f"  row {err.row_number}: {err.message}")
    prefix = "DRY RUN - " if dry_run else ""
    print(
        f"{prefix}Summary: {summary.accepted} accepted, {summary.rejected} rejected, "
        f"{summary.ignored} ignored, {summary.skipped} skipped, {summary.errored} errored"
    )
    if summary.ownership_rows_written:
        verb = "would materialize" if dry_run else "materialized"
        print(f"  {verb} {summary.ownership_rows_written} comedian_podcasts row(s)")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Review podcast ownership candidates. Run episode backfill only after "
            "accepted comedian_podcasts rows exist."
        )
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_export = sub.add_parser("export", help="Write pending ownership candidates to CSV")
    p_export.add_argument("--output", type=Path, required=True)
    p_export.add_argument("--include-resolved", action="store_true")
    p_export.add_argument("--limit", type=int, default=None)

    p_apply = sub.add_parser("apply", help="Apply reviewed CSV decisions")
    p_apply.add_argument("--input", type=Path, required=True)
    mode = p_apply.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--confirm", action="store_true")
    p_apply.add_argument("--force", action="store_true")
    p_apply.add_argument("--reviewer", default=None)
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "export":
        written = _export(
            output_path=args.output,
            include_resolved=args.include_resolved,
            limit=args.limit,
        )
        print(f"Wrote {written} candidate(s) to {args.output}")
        return 0
    if args.command == "apply":
        summary, errors = _apply(
            decisions_path=args.input,
            dry_run=args.dry_run,
            force=args.force,
            reviewer=args.reviewer or os.environ.get("USER") or "",
        )
        _print_apply_report(summary, errors, dry_run=args.dry_run)
        return 2 if summary.errored else 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
