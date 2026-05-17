#!/usr/bin/env python3
"""Backfill accepted comedian podcast episode appearances.

Runs the canonical podcast episode appearance detector against every canonical
comedian and all accepted-feed podcast episodes. The detector applies the
podcast auto-acceptance rules; accepted candidates are materialized into
episode_appearances and unresolved candidates remain in episode_appearance_reviews.

Usage
-----
    cd apps/scraper && make run-script SCRIPT=scripts/core/backfill_podcast_appearances.py ARGS='--dry-run'
    cd apps/scraper && make run-script SCRIPT=scripts/core/backfill_podcast_appearances.py
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Optional

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from dotenv import load_dotenv

load_dotenv(_root / ".env")

from laughtrack.adapters.db import get_transaction
from scripts.core import detect_podcast_episode_appearances as detect_mod

_TASK_ID = 2261
_METADATA_KEY = "task_2261_backfill"

_REQUIRED_COLUMNS = {
    "comedians": {"id", "name", "parent_comedian_id"},
    "comedian_deny_list": {"name"},
    "comedian_podcasts": {"comedian_id", "podcast_id", "association_type", "review_status"},
    "podcasts": {"id", "source", "title", "author_name"},
    "podcast_episodes": {
        "id",
        "podcast_id",
        "source",
        "source_episode_id",
        "title",
        "description",
        "episode_url",
        "source_payload",
    },
    "episode_appearance_reviews": {
        "comedian_id",
        "episode_id",
        "source",
        "source_episode_id",
        "candidate_status",
        "appearance_role",
        "confidence",
        "evidence",
    },
    "episode_appearances": {
        "comedian_id",
        "episode_id",
        "source",
        "appearance_role",
        "review_status",
        "confidence",
        "reviewed_by",
        "reviewed_at",
        "evidence",
    },
}


@dataclass(frozen=True)
class BackfillSnapshot:
    accepted_appearances: int
    comedians_with_accepted_appearances: int
    pending_reviews: int
    ignored_reviews: int


@dataclass(frozen=True)
class BackfillResult:
    before: BackfillSnapshot
    after: BackfillSnapshot
    candidates: int = 0
    auto_accepted: int = 0
    pending: int = 0
    ignored: int = 0
    written: int = 0
    problems: list[str] | None = None


def validate_shape(conn: Any) -> list[str]:
    problems: list[str] = []
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = ANY(%s::text[])
            """,
            (list(_REQUIRED_COLUMNS),),
        )
        actual: dict[str, set[str]] = {}
        for table_name, column_name in cur.fetchall():
            actual.setdefault(str(table_name), set()).add(str(column_name))

    for table_name, required in sorted(_REQUIRED_COLUMNS.items()):
        missing = sorted(required - actual.get(table_name, set()))
        for column in missing:
            problems.append(f"missing {table_name}.{column}")
    return problems


def _load_snapshot(conn: Any) -> BackfillSnapshot:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                COUNT(*) FILTER (WHERE ea.review_status = 'accepted') AS accepted_appearances,
                COUNT(DISTINCT ea.comedian_id) FILTER (WHERE ea.review_status = 'accepted')
                    AS comedians_with_accepted_appearances
            FROM episode_appearances ea
            """
        )
        accepted_appearances, comedians_with_accepted_appearances = cur.fetchone()

        cur.execute(
            """
            SELECT
                COUNT(*) FILTER (WHERE candidate_status = 'pending') AS pending_reviews,
                COUNT(*) FILTER (WHERE candidate_status = 'ignored') AS ignored_reviews
            FROM episode_appearance_reviews
            """
        )
        pending_reviews, ignored_reviews = cur.fetchone()

    return BackfillSnapshot(
        accepted_appearances=int(accepted_appearances or 0),
        comedians_with_accepted_appearances=int(comedians_with_accepted_appearances or 0),
        pending_reviews=int(pending_reviews or 0),
        ignored_reviews=int(ignored_reviews or 0),
    )


def load_before_snapshot(conn: Any) -> BackfillSnapshot:
    return _load_snapshot(conn)


def load_after_snapshot(conn: Any) -> BackfillSnapshot:
    return _load_snapshot(conn)


def _stamp_candidates(
    candidates: list[detect_mod.EpisodeAppearanceCandidate],
) -> list[detect_mod.EpisodeAppearanceCandidate]:
    stamped: list[detect_mod.EpisodeAppearanceCandidate] = []
    for candidate in candidates:
        evidence = dict(candidate.evidence)
        evidence[_METADATA_KEY] = {
            "task_id": _TASK_ID,
            "kind": "podcast_appearance_backfill",
            "launcher": "scripts/core/backfill_podcast_appearances.py",
            "detector": "scripts/core/detect_podcast_episode_appearances.py",
        }
        stamped.append(replace(candidate, evidence=evidence))
    return stamped


def _print_snapshot(label: str, snapshot: BackfillSnapshot) -> None:
    print(f"=== {label} ===")
    print(f"  accepted episode_appearances: {snapshot.accepted_appearances}")
    print(f"  comedians with accepted episode_appearances: {snapshot.comedians_with_accepted_appearances}")
    print(f"  pending episode_appearance_reviews: {snapshot.pending_reviews}")
    print(f"  ignored episode_appearance_reviews: {snapshot.ignored_reviews}")


def backfill_podcast_appearances(
    *,
    dry_run: bool,
    comedian_ids: Optional[list[int]] = None,
    comedian_names: Optional[list[str]] = None,
    episode_ids: Optional[list[int]] = None,
    episode_limit: Optional[int] = None,
    include_aliases: bool = True,
) -> BackfillResult:
    with get_transaction() as conn:
        before = load_before_snapshot(conn)
        _print_snapshot("BEFORE", before)

        problems = validate_shape(conn)
        if problems:
            print("\nABORT: shape mismatch - refusing to write:")
            for problem in problems:
                print(f"  {problem}")
            return BackfillResult(before=before, after=before, problems=problems)

        comedians = detect_mod.load_match_comedians_from_conn(
            conn,
            comedian_ids=comedian_ids,
            comedian_names=comedian_names,
            limit=None,
        )
        episodes = detect_mod.load_episode_inputs_from_conn(
            conn,
            episode_ids=episode_ids,
            limit=episode_limit,
        )
        candidates = detect_mod.detect_episode_candidates(
            comedians,
            episodes,
            include_aliases=include_aliases,
            auto_accept=True,
        )
        candidates = _stamp_candidates(candidates)

        if dry_run:
            summary = detect_mod.DetectSummary(candidates=len(candidates))
            summary.auto_accepted = sum(1 for c in candidates if c.status == "accepted")
            summary.pending = sum(1 for c in candidates if c.status == "pending")
            summary.ignored = sum(1 for c in candidates if c.status == "ignored")
            written = 0
            print("\n--dry-run: no DB write performed.")
        else:
            summary = detect_mod.persist_candidates_with_conn(conn, candidates, dry_run=False)
            written = summary.written

        after = load_after_snapshot(conn)
        print()
        _print_snapshot("AFTER", after)
        print(
            "\nSummary: "
            f"{summary.candidates} candidates, {summary.auto_accepted} auto-accepted, "
            f"{summary.pending} pending, {summary.ignored} ignored, {written} written"
        )

        return BackfillResult(
            before=before,
            after=after,
            candidates=summary.candidates,
            auto_accepted=summary.auto_accepted,
            pending=summary.pending,
            ignored=summary.ignored,
            written=written,
            problems=[],
        )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Backfill accepted comedian podcast episode appearances")
    parser.add_argument("--dry-run", action="store_true", help="Preview the backfill without writing")
    parser.add_argument("--comedian-id", dest="comedian_ids", action="append", type=int, default=None)
    parser.add_argument("--comedian-name", dest="comedian_names", action="append", default=None)
    parser.add_argument("--episode-id", dest="episode_ids", action="append", type=int, default=None)
    parser.add_argument("--episode-limit", type=int, default=None)
    parser.add_argument("--no-aliases", action="store_true")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    result = backfill_podcast_appearances(
        dry_run=args.dry_run,
        comedian_ids=args.comedian_ids,
        comedian_names=args.comedian_names,
        episode_ids=args.episode_ids,
        episode_limit=args.episode_limit,
        include_aliases=not args.no_aliases,
    )
    return 1 if result.problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
