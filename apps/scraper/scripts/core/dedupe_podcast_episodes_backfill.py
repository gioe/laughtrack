#!/usr/bin/env python3
"""One-shot backfill that deletes surplus podcast_episodes dupes after re-pointing
episode_appearances and episode_appearance_reviews onto the canonical row.

TASK-2720 shipped the write-path dedup so new dupes stop accumulating. This
script reconciles the ~29k surplus rows that existed before that change. For
each (podcast_id, release_date, title) group with COUNT(*) > 1 the surviving
canonical row is the one with the lowest id; every appearance and review
pointing at a non-canonical sibling is re-pointed at the canonical id before
the surplus rows are deleted. Appearance rows that would violate the
(comedian_id, episode_id, source) unique constraint after re-pointing are
absorbed instead — the duplicate appearance is deleted on the assumption that
the canonical episode's existing row already covers that (comedian, source)
slot.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from laughtrack.adapters.db import get_connection
from laughtrack.foundation.infrastructure.logger.logger import Logger


@dataclass(frozen=True)
class DupeGroup:
    podcast_id: int
    release_date: Optional[str]
    title: str
    canonical_id: int
    non_canonical_ids: tuple[int, ...]


@dataclass
class DedupeSummary:
    groups_scanned: int = 0
    episodes_deleted: int = 0
    appearances_repointed: int = 0
    appearances_absorbed: int = 0
    reviews_repointed: int = 0
    groups_failed: int = 0
    errors: list[str] = field(default_factory=list)


# Dupe groups are keyed on (podcast_id, release_date, title) — the same key the
# acceptance-criteria post-condition check uses, so a clean run leaves zero
# rows where the criterion would still report a violation. Postgres treats
# NULLs as equal under GROUP BY, so null-release rows are grouped within a
# podcast by exact title match. We do not normalize titles here — TASK-2720
# applies prefix-stripping at write time; for the one-shot historical backfill
# the conservative exact-match key avoids collapsing legitimately distinct
# episodes that happen to share a normalized form.
_FIND_DUPE_GROUPS_SQL = """
    SELECT
        podcast_id,
        release_date,
        title,
        array_agg(id ORDER BY id) AS ids
    FROM podcast_episodes
    GROUP BY podcast_id, release_date, title
    HAVING COUNT(*) > 1
    ORDER BY podcast_id, release_date NULLS LAST, title
"""

# Re-point appearance rows whose episode_id points at a non-canonical sibling
# onto the canonical id, but ONLY where doing so would not collide with an
# existing (comedian_id, canonical_id, source) row. The colliders are left in
# place for the follow-up DELETE step.
_REPOINT_APPEARANCES_SQL = """
    UPDATE episode_appearances ea
    SET episode_id = %s
    WHERE ea.episode_id = ANY(%s)
      AND NOT EXISTS (
          SELECT 1 FROM episode_appearances ea2
          WHERE ea2.episode_id = %s
            AND ea2.comedian_id = ea.comedian_id
            AND ea2.source = ea.source
      )
"""

# Drop any appearance rows that the UPDATE above left behind. These are the
# colliders — a row already exists on the canonical episode for the same
# (comedian_id, source). Removing them preserves the (podcast_id, comedian_id)
# appearance count per criterion 8885 while satisfying the unique constraint.
_DELETE_LEFTOVER_APPEARANCES_SQL = """
    DELETE FROM episode_appearances
    WHERE episode_id = ANY(%s)
"""

# Reviews carry no unique constraint that interacts with episode_id, so a
# straight UPDATE is sufficient. The schema FK is onDelete=SetNull, so
# skipping this step would not corrupt data — but re-pointing preserves the
# audit trail's connection to the canonical episode.
_REPOINT_REVIEWS_SQL = """
    UPDATE episode_appearance_reviews
    SET episode_id = %s
    WHERE episode_id = ANY(%s)
"""

_DELETE_NON_CANONICAL_EPISODES_SQL = """
    DELETE FROM podcast_episodes
    WHERE id = ANY(%s)
"""


def load_dupe_groups(conn: Any, *, limit: Optional[int] = None) -> list[DupeGroup]:
    """Return one DupeGroup per (podcast_id, release_date, title) with COUNT > 1."""
    with conn.cursor() as cur:
        cur.execute(_FIND_DUPE_GROUPS_SQL)
        rows = cur.fetchall() or []
    groups: list[DupeGroup] = []
    for row in rows:
        podcast_id, release_date, title, ids = row
        if len(ids) < 2:
            continue
        groups.append(
            DupeGroup(
                podcast_id=int(podcast_id),
                release_date=str(release_date) if release_date is not None else None,
                title=title,
                canonical_id=int(ids[0]),
                non_canonical_ids=tuple(int(i) for i in ids[1:]),
            )
        )
        if limit is not None and len(groups) >= limit:
            break
    return groups


def _reconcile_group(conn: Any, group: DupeGroup) -> tuple[int, int, int]:
    """Apply one dupe group's reconciliation. Returns (appearances_repointed,
    appearances_absorbed, reviews_repointed)."""
    non_canonical = list(group.non_canonical_ids)
    with conn.cursor() as cur:
        cur.execute(
            _REPOINT_APPEARANCES_SQL,
            (group.canonical_id, non_canonical, group.canonical_id),
        )
        repointed = cur.rowcount or 0
        cur.execute(_DELETE_LEFTOVER_APPEARANCES_SQL, (non_canonical,))
        absorbed = cur.rowcount or 0
        cur.execute(_REPOINT_REVIEWS_SQL, (group.canonical_id, non_canonical))
        reviews = cur.rowcount or 0
        cur.execute(_DELETE_NON_CANONICAL_EPISODES_SQL, (non_canonical,))
    return repointed, absorbed, reviews


def dedupe_podcast_episodes(
    *,
    dry_run: bool,
    confirm: bool,
    limit: Optional[int] = None,
) -> DedupeSummary:
    if dry_run == confirm:
        raise ValueError("choose exactly one of dry_run or confirm")

    summary = DedupeSummary()

    def process(conn: Any) -> None:
        groups = load_dupe_groups(conn, limit=limit)
        summary.groups_scanned = len(groups)
        if dry_run:
            for group in groups:
                summary.episodes_deleted += len(group.non_canonical_ids)
            return
        for group in groups:
            try:
                repointed, absorbed, reviews = _reconcile_group(conn, group)
            except Exception as exc:
                summary.groups_failed += 1
                message = (
                    f"podcast_id={group.podcast_id} release_date={group.release_date} "
                    f"title={group.title!r}: {exc}"
                )
                summary.errors.append(message)
                Logger.warn(f"[dedupe-podcast-episodes] group failed: {message}")
                raise
            summary.episodes_deleted += len(group.non_canonical_ids)
            summary.appearances_repointed += repointed
            summary.appearances_absorbed += absorbed
            summary.reviews_repointed += reviews

    if dry_run:
        with get_connection() as conn:
            process(conn)
        return summary

    with get_connection(autocommit=False) as conn:
        try:
            process(conn)
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    return summary


def _print_report(summary: DedupeSummary, *, dry_run: bool) -> None:
    prefix = "DRY RUN — " if dry_run else ""
    print(
        f"{prefix}Summary: {summary.groups_scanned} dupe groups, "
        f"{summary.episodes_deleted} episodes deleted, "
        f"{summary.appearances_repointed} appearances re-pointed, "
        f"{summary.appearances_absorbed} appearances absorbed (collisions), "
        f"{summary.reviews_repointed} reviews re-pointed, "
        f"{summary.groups_failed} groups failed"
    )
    for error in summary.errors:
        print(f"  error: {error}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "One-shot backfill: dedupe podcast_episodes by deleting non-canonical "
            "siblings after re-pointing episode_appearances and reviews."
        ),
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Scan dupe groups and report planned deletes without writing",
    )
    mode.add_argument(
        "--confirm",
        action="store_true",
        help="Re-point appearances/reviews and delete non-canonical episodes",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process at most N dupe groups (useful for staged runs)",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.dry_run == args.confirm:
        parser.error("choose exactly one of --dry-run or --confirm")

    summary = dedupe_podcast_episodes(
        dry_run=args.dry_run,
        confirm=args.confirm,
        limit=args.limit,
    )
    _print_report(summary, dry_run=args.dry_run)
    return 0 if summary.groups_failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
