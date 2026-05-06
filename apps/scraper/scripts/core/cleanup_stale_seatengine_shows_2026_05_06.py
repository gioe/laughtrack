#!/usr/bin/env python3
"""
Delete stale future SeatEngine show inventory for TASK-1955.

TASK-1950 disabled the dead SeatEngine scraping_sources for two clubs but
intentionally left their existing future show rows in place for a follow-up
disposition:

  63  TK's                                  ss=52  SeatEngine venue 514
  82  Wicked Funny Comedy Club North Andover ss=146 SeatEngine venue 487

The follow-up decision here is DELETE, not hide or cancel:
  - the current ``shows`` table has no ``visible`` column,
  - the current ``shows`` table has no cancellation/status column,
  - the source rows are already disabled because SeatEngine returns no events,
  - leaving these rows visible continues to show misleading future inventory.

This script deletes only future rows for these clubs whose
``last_scraped_date`` is on or before the TASK-1950 stale-source cutoff. It
also stamps the disabled SeatEngine ``scraping_sources.metadata`` with
``task_1955_show_cleanup`` so the per-club disposition survives after the show
rows are gone.

Safeguards:
  - validates the expected club and source rows,
  - requires the SeatEngine source to already be disabled,
  - aborts if either club has newer future inventory mixed in,
  - deletes by ``shows.id`` inside one transaction,
  - supports ``--dry-run`` with the exact planned counts.

Idempotent: after the first real run, no stale future rows remain and only the
metadata stamp is rechecked.

Usage
-----
    cd apps/scraper
    make run-script SCRIPT=scripts/core/cleanup_stale_seatengine_shows_2026_05_06.py ARGS='--dry-run'
    make run-script SCRIPT=scripts/core/cleanup_stale_seatengine_shows_2026_05_06.py
"""

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from dotenv import load_dotenv

load_dotenv(_root / ".env")

from laughtrack.adapters.db import get_transaction


_METADATA_KEY = "task_1955_show_cleanup"
_STALE_LAST_SCRAPED_CUTOFF = "2026-03-26T23:59:59+00:00"
_PRIOR_DISPOSITION_KEY = "task_1950_disposition"


@dataclass(frozen=True)
class CleanupTarget:
    """A disabled SeatEngine source whose stale future show rows should be deleted."""

    club_id: int
    club_name: str
    source_id: int
    expected_external_id: str
    rationale: str
    disposition_kind: str = "delete_stale_future_shows"
    expected_platform: str = "seatengine"
    delete_future_shows: bool = True


_CLEANUP_TARGETS: list[CleanupTarget] = [
    CleanupTarget(
        club_id=63,
        club_name="TK's",
        source_id=52,
        expected_external_id="514",
        rationale=(
            "TK's rebranded as the Addison/Dallas restaurant and the SeatEngine "
            "venue returns no events. TASK-1950 disabled ss=52; delete stale "
            "future rows scraped before that disposition so users no longer see "
            "obsolete TK's comedy inventory."
        ),
    ),
    CleanupTarget(
        club_id=82,
        club_name="Wicked Funny Comedy Club North Andover",
        source_id=146,
        expected_external_id="487",
        rationale=(
            "Wicked Funny North Andover is closed for renovations and the "
            "SeatEngine venue returns no events. TASK-1950 disabled ss=146; "
            "delete stale future rows scraped before that disposition. If the "
            "venue reopens, a fresh scrape should repopulate current inventory."
        ),
    ),
]


def _load_metadata(raw) -> dict:
    if isinstance(raw, str):
        return json.loads(raw)
    if raw is None:
        return {}
    return dict(raw)


def _metadata_stamp(target: CleanupTarget, deleted_count: int | None) -> dict:
    stamp = {
        "kind": target.disposition_kind,
        "stale_last_scraped_cutoff": _STALE_LAST_SCRAPED_CUTOFF,
        "rationale": target.rationale,
    }
    if deleted_count is not None:
        stamp["deleted_future_show_count"] = deleted_count
    return stamp


def _needs_metadata_update(meta: dict, stale_future: int) -> bool:
    if _METADATA_KEY not in meta:
        return True
    return stale_future > 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Delete stale future show inventory for TASK-1955 clubs 63 and 82 "
            "and stamp the disabled SeatEngine source rows."
        )
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()

    club_ids = [t.club_id for t in _CLEANUP_TARGETS]
    source_ids = [t.source_id for t in _CLEANUP_TARGETS]

    with get_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, visible
                FROM clubs
                WHERE id = ANY(%s)
                ORDER BY id
                """,
                (club_ids,),
            )
            club_rows = {r[0]: r for r in cur.fetchall()}

            cur.execute(
                """
                SELECT id, club_id, platform::text, scraper_key, external_id,
                       enabled, metadata
                FROM scraping_sources
                WHERE id = ANY(%s)
                ORDER BY id
                """,
                (source_ids,),
            )
            source_rows = {r[0]: r for r in cur.fetchall()}

            cur.execute(
                """
                SELECT club_id,
                       COUNT(*) FILTER (WHERE date > NOW()) AS future_total,
                       COUNT(*) FILTER (
                           WHERE date > NOW()
                             AND last_scraped_date <= %s::timestamptz
                       ) AS stale_future,
                       COUNT(*) FILTER (
                           WHERE date > NOW()
                             AND (
                                 last_scraped_date IS NULL
                                 OR last_scraped_date > %s::timestamptz
                             )
                       ) AS newer_future,
                       MIN(date) FILTER (WHERE date > NOW()) AS first_future,
                       MAX(date) FILTER (WHERE date > NOW()) AS last_future,
                       MAX(last_scraped_date) FILTER (WHERE date > NOW()) AS latest_scraped
                FROM shows
                WHERE club_id = ANY(%s)
                GROUP BY club_id
                ORDER BY club_id
                """,
                (_STALE_LAST_SCRAPED_CUTOFF, _STALE_LAST_SCRAPED_CUTOFF, club_ids),
            )
            show_stats = {r[0]: r for r in cur.fetchall()}

        problems: list[str] = []

        for target in _CLEANUP_TARGETS:
            club_row = club_rows.get(target.club_id)
            if club_row is None:
                problems.append(f"missing clubs.id={target.club_id}")
            else:
                _, name, _ = club_row
                if name != target.club_name:
                    problems.append(
                        f"clubs.id={target.club_id}: name={name!r} "
                        f"(expected {target.club_name!r})"
                    )

            source_row = source_rows.get(target.source_id)
            if source_row is None:
                problems.append(f"missing scraping_sources.id={target.source_id}")
            else:
                _, club_id, platform, scraper_key, external_id, enabled, meta_raw = source_row
                meta = _load_metadata(meta_raw)
                if club_id != target.club_id:
                    problems.append(
                        f"ss.id={target.source_id}: club_id={club_id} "
                        f"(expected {target.club_id})"
                    )
                if platform != target.expected_platform:
                    problems.append(
                        f"ss.id={target.source_id}: platform={platform!r} "
                        f"(expected {target.expected_platform!r})"
                    )
                if scraper_key != target.expected_platform:
                    problems.append(
                        f"ss.id={target.source_id}: scraper_key={scraper_key!r} "
                        f"(expected {target.expected_platform!r})"
                    )
                if external_id != target.expected_external_id:
                    problems.append(
                        f"ss.id={target.source_id}: external_id={external_id!r} "
                        f"(expected {target.expected_external_id!r})"
                    )
                if enabled:
                    problems.append(
                        f"ss.id={target.source_id}: enabled=True "
                        "(expected TASK-1950 to have disabled it first)"
                    )
                if _PRIOR_DISPOSITION_KEY not in meta:
                    problems.append(
                        f"ss.id={target.source_id}: missing metadata[{_PRIOR_DISPOSITION_KEY}]"
                    )

            stats = show_stats.get(target.club_id)
            if stats is not None:
                _, _, _, newer_future, _, _, _ = stats
                if newer_future:
                    problems.append(
                        f"clubs.id={target.club_id}: found {newer_future} newer/null "
                        "future shows; refusing to mix stale cleanup with fresh inventory"
                    )

        if problems:
            print("ABORT: shape mismatch - refusing to write:", file=sys.stderr)
            for problem in problems:
                print(f"  {problem}", file=sys.stderr)
            return 1

        print("=== TARGETS ===")
        for target in _CLEANUP_TARGETS:
            _, _, visible = club_rows[target.club_id]
            stats = show_stats.get(target.club_id)
            if stats is None:
                future_total = stale_future = newer_future = 0
                first_future = last_future = latest_scraped = None
            else:
                (
                    _,
                    future_total,
                    stale_future,
                    newer_future,
                    first_future,
                    last_future,
                    latest_scraped,
                ) = stats
            print(
                f"  club={target.club_id:>3} {target.club_name!r} visible={visible} "
                f"future_total={future_total} stale_future={stale_future} "
                f"newer_future={newer_future} first={first_future} "
                f"last={last_future} latest_scraped={latest_scraped}"
            )

        if args.dry_run:
            print("\n--dry-run: planning writes, no DB changes...")

        total_deleted = 0
        with conn.cursor() as cur:
            for target in _CLEANUP_TARGETS:
                stats = show_stats.get(target.club_id)
                stale_future = int(stats[2]) if stats is not None else 0

                source_row = source_rows[target.source_id]
                meta = _load_metadata(source_row[6])
                needs_meta = _needs_metadata_update(meta, stale_future)
                action = "PLAN " if args.dry_run else "WRITE"
                metadata_action = (
                    f"stamp metadata[{_METADATA_KEY}]={target.disposition_kind!r}"
                    if needs_meta
                    else f"preserve existing metadata[{_METADATA_KEY}]"
                )

                print(
                    f"  {action} club={target.club_id}: delete {stale_future} stale future shows "
                    f"+ {metadata_action}"
                )

                if args.dry_run:
                    continue

                if stale_future:
                    cur.execute(
                        """
                        WITH stale AS (
                            SELECT id
                            FROM shows
                            WHERE club_id = %s
                              AND date > NOW()
                              AND last_scraped_date <= %s::timestamptz
                        )
                        DELETE FROM shows
                        WHERE id IN (SELECT id FROM stale)
                        RETURNING id
                        """,
                        (target.club_id, _STALE_LAST_SCRAPED_CUTOFF),
                    )
                    deleted = len(cur.fetchall())
                else:
                    deleted = 0

                total_deleted += deleted
                if deleted != stale_future:
                    raise RuntimeError(
                        f"clubs.id={target.club_id}: planned {stale_future} deletes, "
                        f"but deleted {deleted}"
                    )

                if needs_meta or deleted:
                    new_meta = dict(meta)
                    new_meta[_METADATA_KEY] = _metadata_stamp(target, deleted)
                    cur.execute(
                        """
                        UPDATE scraping_sources
                        SET metadata = %s, updated_at = NOW()
                        WHERE id = %s
                        """,
                        (json.dumps(new_meta), target.source_id),
                    )

        if args.dry_run:
            print("\nDRY RUN COMPLETE: no changes written.")
        else:
            print(f"\nDONE: deleted {total_deleted} stale future shows.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
