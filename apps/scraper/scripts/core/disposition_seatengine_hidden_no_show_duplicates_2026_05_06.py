#!/usr/bin/env python3
"""
Disable hidden/no-show SeatEngine v1/v3 priority=0 duplicate source rows.

TASK-1953 found two hidden clubs with no show history where both the classic
``seatengine`` source and the ``seatengine_v3`` source were enabled at
``priority=0``:

  147  Cafe CODA
       ss=907 ``seatengine`` id 565; ss=330 ``seatengine_v3`` id e7ea1e53-...

  583  Cultural Center for the Arts with Krackpots Comedy Club
       ss=905 ``seatengine`` id 563; ss=158 ``seatengine_v3`` id 58a56237-...

Both endpoints returned 0 records during the TASK-1953 audit, both clubs are
hidden, and neither club has show history. There is no active canonical scrape
to preserve, so this disposition disables both duplicate rows for each club and
records the rationale in ``metadata.task_1965_disposition``.

Idempotent: only writes when ``enabled`` is currently True OR the metadata key
is missing. Safe to re-run.

Usage
-----
    cd apps/scraper
    make run-script SCRIPT=scripts/core/disposition_seatengine_hidden_no_show_duplicates_2026_05_06.py ARGS='--dry-run'
    make run-script SCRIPT=scripts/core/disposition_seatengine_hidden_no_show_duplicates_2026_05_06.py
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


_METADATA_KEY = "task_1965_disposition"
_DISPOSITION_KIND = "hidden_no_show_parallel_duplicate"


@dataclass(frozen=True)
class DisableTarget:
    """A scraping_sources row to flip enabled=false with a stamped rationale."""

    source_id: int
    expected_club_id: int
    expected_platform: str
    expected_external_id: str
    rationale: str


_DISABLE_TARGETS: list[DisableTarget] = [
    DisableTarget(
        source_id=907,
        expected_club_id=147,
        expected_platform="seatengine",
        expected_external_id="565",
        rationale=(
            "Cafe CODA. Hidden club with 0 historical shows; TASK-1953 found "
            "both v1 venue 565 and v3 venue e7ea1e53-... return 0 records. "
            "Disable this priority=0 source rather than keeping a no-op "
            "parallel duplicate alive."
        ),
    ),
    DisableTarget(
        source_id=330,
        expected_club_id=147,
        expected_platform="seatengine_v3",
        expected_external_id="e7ea1e53-8a31-48b6-bfe4-fd9672791615",
        rationale=(
            "Cafe CODA. Hidden club with 0 historical shows; TASK-1953 found "
            "the v3 endpoint also returns 0 records. No canonical active "
            "source is needed while the venue remains hidden/no-show, so "
            "disable this sibling with the same disposition."
        ),
    ),
    DisableTarget(
        source_id=905,
        expected_club_id=583,
        expected_platform="seatengine",
        expected_external_id="563",
        rationale=(
            "Cultural Center for the Arts with Krackpots Comedy Club. Hidden "
            "club with 0 historical shows; TASK-1953 found v1 venue 563 and "
            "v3 venue 58a56237-... both return 0 records. Prior migration "
            "20260502105947 hid the club; disable this stale no-op priority=0 "
            "source."
        ),
    ),
    DisableTarget(
        source_id=158,
        expected_club_id=583,
        expected_platform="seatengine_v3",
        expected_external_id="58a56237-0902-40c0-8e4b-e592e782aec0",
        rationale=(
            "Cultural Center for the Arts with Krackpots Comedy Club. Hidden "
            "club with 0 historical shows; TASK-1953 found the v3 endpoint "
            "returns 0 records as well. Disable this sibling so the hidden "
            "venue has no priority=0 SeatEngine duplicate scrape."
        ),
    ),
]


def _load_metadata(raw) -> dict:
    if isinstance(raw, str):
        return json.loads(raw)
    if raw is None:
        return {}
    return dict(raw)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Disable TASK-1965 hidden/no-show SeatEngine v1/v3 duplicate "
            "scraping_sources rows for clubs 147 and 583."
        )
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()

    target_ids = [t.source_id for t in _DISABLE_TARGETS]

    with get_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, club_id, platform::text, scraper_key, external_id,
                       priority, enabled, metadata
                FROM scraping_sources
                WHERE id = ANY(%s)
                ORDER BY id
                """,
                (target_ids,),
            )
            rows = {r[0]: r for r in cur.fetchall()}

        problems: list[str] = []
        missing = [sid for sid in target_ids if sid not in rows]
        if missing:
            problems.append(f"missing scraping_sources rows: {missing}")

        for t in _DISABLE_TARGETS:
            row = rows.get(t.source_id)
            if row is None:
                continue
            _, club_id, platform, scraper_key, external_id, priority, _, _ = row
            if club_id != t.expected_club_id:
                problems.append(
                    f"ss.id={t.source_id}: club_id={club_id} (expected {t.expected_club_id})"
                )
            if platform != t.expected_platform:
                problems.append(
                    f"ss.id={t.source_id}: platform={platform!r} (expected {t.expected_platform!r})"
                )
            if scraper_key != t.expected_platform:
                problems.append(
                    f"ss.id={t.source_id}: scraper_key={scraper_key!r} "
                    f"(expected {t.expected_platform!r})"
                )
            if external_id != t.expected_external_id:
                problems.append(
                    f"ss.id={t.source_id}: external_id={external_id!r} "
                    f"(expected {t.expected_external_id!r})"
                )
            if priority != 0:
                problems.append(
                    f"ss.id={t.source_id}: priority={priority} (expected 0)"
                )

        if problems:
            print("ABORT: shape mismatch - refusing to write:", file=sys.stderr)
            for p in problems:
                print(f"  {p}", file=sys.stderr)
            return 1

        print("=== BEFORE ===")
        for t in _DISABLE_TARGETS:
            row = rows[t.source_id]
            sid, cid, platform, _, external_id, priority, enabled, _ = row
            print(
                f"  ss.id={sid:>4} club={cid:>4} {platform:<14} "
                f"ext={str(external_id):<36} pri={priority} enabled={enabled}"
            )

        writes_planned = 0
        if args.dry_run:
            print("\n--dry-run: planning writes, no DB changes...")

        with conn.cursor() as cur:
            for t in _DISABLE_TARGETS:
                row = rows[t.source_id]
                _, _, _, _, _, _, enabled, meta_raw = row
                meta = _load_metadata(meta_raw)
                needs_disable = bool(enabled)
                needs_meta = _METADATA_KEY not in meta
                if not (needs_disable or needs_meta):
                    continue

                new_meta = dict(meta)
                new_meta[_METADATA_KEY] = {
                    "kind": _DISPOSITION_KIND,
                    "rationale": t.rationale,
                }
                action = "PLAN " if args.dry_run else "WRITE"
                print(
                    f"  {action} ss={t.source_id} (club {t.expected_club_id}): "
                    f"enabled={enabled}->FALSE + metadata[{_METADATA_KEY}]={_DISPOSITION_KIND!r}"
                )
                if not args.dry_run:
                    cur.execute(
                        """
                        UPDATE scraping_sources
                        SET enabled = FALSE,
                            metadata = %s,
                            updated_at = NOW()
                        WHERE id = %s
                        """,
                        (json.dumps(new_meta), t.source_id),
                    )
                writes_planned += 1

        if writes_planned == 0:
            print("\nNo changes needed (idempotent re-run).")
            return 0

        if args.dry_run:
            print(f"\n--dry-run: {writes_planned} writes planned (none applied).")
            return 0

        print(f"\n=== AFTER ({writes_planned} writes pending commit on transaction exit) ===")

    with get_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, club_id, platform::text, external_id, enabled
                FROM scraping_sources
                WHERE id = ANY(%s)
                ORDER BY id
                """,
                (target_ids,),
            )
            for sid, cid, platform, external_id, enabled in cur.fetchall():
                print(
                    f"  ss.id={sid:>4} club={cid:>4} {platform:<14} "
                    f"ext={str(external_id):<36} "
                    f"enabled={enabled}"
                )

    return 0


if __name__ == "__main__":
    sys.exit(main())
