#!/usr/bin/env python3
"""
Resolve the two actionable active SeatEngine v1/v3 priority=0 duplicates
surfaced by the TASK-1953 audit.

Background
----------
TASK-1950 fixed eight stub clubs that had both a classic ``seatengine`` and
a ``seatengine_v3`` source at ``priority=0``. TASK-1953 re-ran the parallel-
sources query against the live DB on 2026-05-06 and recorded a per-club
disposition. Two clubs are still active duplicates that need cleanup:

  144  The Comedy Studio   ss=943 classic ext=631 (151 records)
                           ss=485 v3 ext=cf2b1561-...
                           Both endpoints currently return 151 records.
                           Canonical: v3 — drives the venue's primary site at
                           thecomedystudio.com on the v3 platform.

  602  Laugh And Enjoy     ss=924 classic ext=586 (0 records, hidden venue)
                           ss=460 v3 ext=c91f790c-...
                           Venue currently hidden pending grand opening; v3 is
                           the verified active source preserved for reopening.

The four other clubs from the TASK-1953 audit are out of scope here:
  - 568, 589 — already disabled by TASK-1950 (``stub_dormant``).
  - 147, 583 — both hidden, both endpoints return 0 records; folded into the
                broader hidden-club cleanup backlog rather than handled here.

Durability note
---------------
``UPSERT_CLUB_BY_SEATENGINE_VENUE`` in ``apps/scraper/sql/club_queries.py``
unconditionally sets ``enabled=TRUE`` on conflict. ``seatengine_national`` scans
venue IDs 1..N each nightly, so any classic SE venue that resolves to a real
``name`` will be upserted and its ``enabled`` flipped back. That is exactly why
the prior ``20260502195959_hide_laugh_and_enjoy_pending_opening`` migration's
flip to ``enabled=false`` on ss=924 did not stick — the row is back at
``enabled=true``. ``metadata`` is NOT in the upsert's SET clause, so the
``task_1966_disposition`` stamp survives the re-enable. Disabling here will
silence ``priority=0`` parallel scrapes for at most one nightly cycle on the
classic SE row; making the upsert respect dispositional disables is a separate
structural change tracked outside this XS task. Rationale lives in
metadata regardless so the audit trail is durable.

What this script does
---------------------
1. Validates expected ``(club_id, platform, scraper_key, external_id, priority)``
   shape on each targeted ``scraping_sources`` row (refuses to write on any
   mismatch — collects all problems first).
2. For each target: ``UPDATE scraping_sources SET enabled=false,
   metadata=metadata || <stamp>::jsonb, updated_at=NOW()`` keyed by ``id``.
3. Stamps ``metadata.task_1966_disposition`` with ``kind='parallel_v1_redundant'``
   and a per-row rationale, mirroring the TASK-1950 / TASK-1924 / TASK-1918
   disposition pattern so the forensic audit trail survives downstream upserts.
4. The v3 sibling rows (ss=485 club 144, ss=460 club 602) are left untouched —
   they are the canonical active sources.

Idempotent: only writes when ``enabled`` is currently True OR the metadata key
is missing. Safe to re-run.

Usage
-----
    cd apps/scraper
    make run-script SCRIPT=scripts/core/disposition_seatengine_v1_v3_parallel_2026_05_06.py ARGS='--dry-run'
    make run-script SCRIPT=scripts/core/disposition_seatengine_v1_v3_parallel_2026_05_06.py
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


_METADATA_KEY = "task_1966_disposition"
_DISPOSITION_KIND = "parallel_v1_redundant"


@dataclass(frozen=True)
class DisableTarget:
    """A scraping_sources row to flip enabled=false with a stamped rationale."""

    source_id: int
    expected_club_id: int
    expected_platform: str          # 'seatengine' (classic v1)
    expected_external_id: str       # external_id used to confirm the right row
    rationale: str


_DISABLE_TARGETS: list[DisableTarget] = [
    DisableTarget(
        source_id=943,
        expected_club_id=144,
        expected_platform="seatengine",
        expected_external_id="631",
        rationale=(
            "The Comedy Studio. v1 venue 631 and v3 venue cf2b1561-... both "
            "return 151 records; running both at priority=0 is redundant and "
            "double-upserts every show. v3 (ss=485) is the canonical primary "
            "for thecomedystudio.com — keep v3 enabled and disable classic v1 "
            "to stop the parallel scrape."
        ),
    ),
    DisableTarget(
        source_id=924,
        expected_club_id=602,
        expected_platform="seatengine",
        expected_external_id="586",
        rationale=(
            "Laugh And Enjoy. Migration 20260502195959_hide_laugh_and_enjoy_"
            "pending_opening intended this exact disable but seatengine_national's "
            "nightly upsert flips enabled back to TRUE because v1 venue 586 "
            "still resolves to a name in the SE directory. v1 endpoint returns "
            "0 records; v3 (ss=460) is the verified active source preserved "
            "for the venue's grand opening. Re-disable here with metadata "
            "stamp; durable resolution requires the upsert to respect "
            "dispositional disables (out of scope for this task)."
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
            "Disable two classic SeatEngine scraping_sources (ss=943 club 144, "
            "ss=924 club 602) that currently run in parallel with their "
            "seatengine_v3 siblings at priority=0. See module docstring for "
            "the full rationale."
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
                       source_url, priority, enabled, metadata
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
            _, club_id, platform, scraper_key, external_id, _, priority, _, _ = row
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
            if str(external_id) != t.expected_external_id:
                problems.append(
                    f"ss.id={t.source_id}: external_id={external_id!r} "
                    f"(expected {t.expected_external_id!r})"
                )
            if priority != 0:
                problems.append(
                    f"ss.id={t.source_id}: priority={priority} (expected 0)"
                )

        if problems:
            print("ABORT: shape mismatch — refusing to write:", file=sys.stderr)
            for p in problems:
                print(f"  {p}", file=sys.stderr)
            return 1

        print("=== BEFORE ===")
        for t in _DISABLE_TARGETS:
            sid, cid, plat, sk, ext, src_url, pri, en, _ = rows[t.source_id]
            print(
                f"  ss.id={sid:>4} club={cid:>4} {plat:<14} ext={ext:<10} "
                f"pri={pri} enabled={en}"
            )

        writes_planned = 0

        if args.dry_run:
            print("\n--dry-run: planning writes, no DB changes...")

        with conn.cursor() as cur:
            for t in _DISABLE_TARGETS:
                row = rows[t.source_id]
                _, _, _, _, _, _, _, enabled, meta_raw = row
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
                    f"enabled={enabled}→FALSE + metadata[{_METADATA_KEY}]={_DISPOSITION_KIND!r}"
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
            for sid, cid, plat, ext, en in cur.fetchall():
                print(
                    f"  ss.id={sid:>4} club={cid:>4} {plat:<14} ext={ext:<10} enabled={en}"
                )

    return 0


if __name__ == "__main__":
    sys.exit(main())
