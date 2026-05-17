#!/usr/bin/env python3
"""Report deterministic spot-check sampling for auto-accepted podcast appearances."""

from __future__ import annotations

import argparse
import hashlib
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from laughtrack.adapters.db import get_connection
from laughtrack.core.podcast_appearance_auto_acceptance import AUTO_ACCEPTANCE_RULE_VERSION

_LOAD_AUTO_ACCEPTED_SQL = """
    SELECT
        ear.id,
        c.name,
        p.title AS podcast_title,
        pe.title AS episode_title,
        ear.confidence,
        ear.evidence->'auto_acceptance'->>'rule_id' AS rule_id,
        COALESCE((ear.evidence->'spot_check'->>'drift_flag')::boolean, false) AS drift_flag
    FROM episode_appearance_reviews ear
    JOIN comedians c ON c.id = ear.comedian_id
    LEFT JOIN podcast_episodes pe ON pe.id = ear.episode_id
    LEFT JOIN podcasts p ON p.id = pe.podcast_id
    WHERE ear.candidate_status = 'accepted'
      AND ear.evidence ? 'auto_acceptance'
    ORDER BY ear.id
"""


@dataclass(frozen=True)
class AutoAcceptedReviewRow:
    candidate_id: int
    comedian_name: str
    podcast_title: str
    episode_title: str
    confidence: float
    rule_id: str
    drift_flag: bool = False


@dataclass(frozen=True)
class SpotCheckReport:
    total_auto_accepted: int
    rule_counts: dict[str, int]
    drift_flags: int
    sample_rows: list[AutoAcceptedReviewRow]


def _sample_key(row: AutoAcceptedReviewRow) -> str:
    return hashlib.sha256(f"{AUTO_ACCEPTANCE_RULE_VERSION}:{row.candidate_id}".encode("utf-8")).hexdigest()


def build_report(rows: list[AutoAcceptedReviewRow], *, sample_rate: float = 0.02) -> SpotCheckReport:
    sample_size = max(1, round(len(rows) * sample_rate)) if rows else 0
    sample_rows = sorted(rows, key=_sample_key)[:sample_size]
    return SpotCheckReport(
        total_auto_accepted=len(rows),
        rule_counts=dict(Counter(row.rule_id for row in rows)),
        drift_flags=sum(1 for row in rows if row.drift_flag),
        sample_rows=sample_rows,
    )


def load_auto_accepted_rows(*, limit: Optional[int] = None) -> list[AutoAcceptedReviewRow]:
    query = _LOAD_AUTO_ACCEPTED_SQL
    params: tuple[Any, ...] | None = None
    if limit:
        query += "\n    LIMIT %s"
        params = (int(limit),)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return [
                AutoAcceptedReviewRow(
                    candidate_id=int(row[0]),
                    comedian_name=str(row[1] or ""),
                    podcast_title=str(row[2] or ""),
                    episode_title=str(row[3] or ""),
                    confidence=float(row[4] or 0.0),
                    rule_id=str(row[5] or "unknown"),
                    drift_flag=bool(row[6]),
                )
                for row in cur.fetchall()
            ]


def _print_report(report: SpotCheckReport) -> None:
    print(f"auto_accepted={report.total_auto_accepted}")
    print(f"drift_flags={report.drift_flags}")
    for rule_id, count in sorted(report.rule_counts.items()):
        print(f"rule {rule_id}: {count}")
    print("spot.check sample:")
    for row in report.sample_rows:
        print(
            f"  candidate_id={row.candidate_id} confidence={row.confidence:.2f} "
            f"rule={row.rule_id} comedian={row.comedian_name!r} episode={row.episode_title!r}"
        )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sample auto-accepted podcast appearance rows for QA")
    parser.add_argument("--sample-rate", type=float, default=0.02)
    parser.add_argument("--limit", type=int, default=None)
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    rows = load_auto_accepted_rows(limit=args.limit)
    _print_report(build_report(rows, sample_rate=args.sample_rate))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
