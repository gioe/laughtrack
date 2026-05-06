#!/usr/bin/env python3
"""
Disable four dead SeatEngine fallback rows from the 2026-05-06 nightly WARNs.

Background
----------
TASK-1962 triaged four SeatEngineScraper "no events found" WARNs that were
outside the TASK-1942/TASK-1950 audit window:

  141  Improv Asylum             ss=673  SeatEngine venue 35
  207  Dr. Grins Comedy Club     ss=651  SeatEngine venue 4
  463  The Stand Up Comedy Club  ss=1114 SeatEngine venue 438
  574  Go Bananas Comedy Club    ss=570  SeatEngine venue 554

Convention #80 diagnostic SQL showed these are not stub rows: every club has
historical scrape state, and three still have future show rows in the database.
Direct SeatEngine API calls on 2026-05-06 confirmed both
``/api/v1/venues/<id>/shows`` and ``/api/v1/venues/<id>/events`` return
``{data: []}`` for all four venue ids.

Each venue also has a non-SeatEngine priority=0 source or custom scraper that
covers its current public bookings:

  141 Improv Asylum: Tixr source ss=390, public Tixr group has upcoming shows.
  207 Dr. Grins: Etix/custom source ss=154, public Etix/venue listings have shows.
  463 The Stand Up: TicketWeb source ss=286, homepage/TicketWeb has shows.
  574 Go Bananas: custom source ss=959, public site/custom scraper has shows.

Disposition: source disabled for the four SeatEngine rows. No club hides or
venue closures are performed.

What this script does
---------------------
1. Validates expected shape of every targeted ``scraping_sources`` row.
2. Updates each SeatEngine row to ``enabled=false``.
3. Stamps ``metadata.task_1962_disposition`` with a per-row rationale.
4. Prints BEFORE/AFTER blocks for the ops audit trail.

Idempotent: only writes when ``enabled`` is currently True OR the metadata key
is missing. Safe to re-run.

Usage
-----
    cd apps/scraper
    make run-script SCRIPT=scripts/core/disposition_seatengine_no_events_2026_05_06.py ARGS='--dry-run'
    make run-script SCRIPT=scripts/core/disposition_seatengine_no_events_2026_05_06.py
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


_METADATA_KEY = "task_1962_disposition"
_DISPOSITION_KIND = "fallback_redundant_no_events"


@dataclass(frozen=True)
class DisableTarget:
    """A scraping_sources row to flip enabled=false with a stamped rationale."""

    source_id: int
    expected_club_id: int
    expected_platform: str
    expected_external_id: str
    fallback_source_id: int
    rationale: str


_DISABLE_TARGETS: list[DisableTarget] = [
    DisableTarget(
        source_id=673,
        expected_club_id=141,
        expected_platform="seatengine",
        expected_external_id="35",
        fallback_source_id=390,
        rationale=(
            "Improv Asylum. SeatEngine venue 35 returns {data: []} from both "
            "/shows and /events, while the priority=0 Tixr source ss=390 points "
            "at https://www.tixr.com/groups/improvasylum and the public Tixr "
            "calendar has upcoming Improv Asylum shows. Disable the redundant "
            "SeatEngine row to stop nightly WARNs; keep the Tixr source active."
        ),
    ),
    DisableTarget(
        source_id=651,
        expected_club_id=207,
        expected_platform="seatengine",
        expected_external_id="4",
        fallback_source_id=154,
        rationale=(
            "Dr. Grins Comedy Club. SeatEngine venue 4 returns {data: []} from "
            "both /shows and /events. The priority=0 dr_grins/Etix source ss=154 "
            "covers the venue's public bookings, with current public listings "
            "showing upcoming Dr. Grins events. Disable the redundant SeatEngine "
            "row and leave the Etix source active."
        ),
    ),
    DisableTarget(
        source_id=1114,
        expected_club_id=463,
        expected_platform="seatengine",
        expected_external_id="438",
        fallback_source_id=286,
        rationale=(
            "The Stand Up Comedy Club. SeatEngine venue 438 returns {data: []} "
            "from both /shows and /events. The priority=0 TicketWeb source "
            "ss=286 was already repointed to the homepage by TASK-1943 and "
            "public TicketWeb listings have upcoming shows. Disable the "
            "redundant SeatEngine row and leave TicketWeb active."
        ),
    ),
    DisableTarget(
        source_id=570,
        expected_club_id=574,
        expected_platform="seatengine",
        expected_external_id="554",
        fallback_source_id=959,
        rationale=(
            "Go Bananas Comedy Club. SeatEngine venue 554 returns {data: []} "
            "from both /shows and /events. The priority=0 custom go_bananas "
            "source ss=959 points at https://gobananascomedy.com and the public "
            "site has upcoming bookings. Disable the redundant SeatEngine row "
            "and leave the custom scraper active."
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
            "Disable TASK-1962 redundant SeatEngine source rows for four venues "
            "whose SeatEngine APIs now return no events but have active fallback sources."
        )
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()

    target_ids = [t.source_id for t in _DISABLE_TARGETS]
    fallback_ids = [t.fallback_source_id for t in _DISABLE_TARGETS]

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

            cur.execute(
                """
                SELECT id, club_id, priority, enabled
                FROM scraping_sources
                WHERE id = ANY(%s)
                ORDER BY id
                """,
                (fallback_ids,),
            )
            fallback_rows = {r[0]: r for r in cur.fetchall()}

        problems: list[str] = []
        missing = [sid for sid in target_ids if sid not in rows]
        if missing:
            problems.append(f"missing scraping_sources rows: {missing}")

        missing_fallbacks = [sid for sid in fallback_ids if sid not in fallback_rows]
        if missing_fallbacks:
            problems.append(f"missing fallback scraping_sources rows: {missing_fallbacks}")

        for t in _DISABLE_TARGETS:
            row = rows.get(t.source_id)
            if row is not None:
                _, club_id, platform, scraper_key, external_id, priority, _, _ = row
                if club_id != t.expected_club_id:
                    problems.append(
                        f"ss.id={t.source_id}: club_id={club_id} "
                        f"(expected {t.expected_club_id})"
                    )
                if platform != t.expected_platform:
                    problems.append(
                        f"ss.id={t.source_id}: platform={platform!r} "
                        f"(expected {t.expected_platform!r})"
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

            fallback = fallback_rows.get(t.fallback_source_id)
            if fallback is not None:
                _, fallback_club_id, fallback_priority, fallback_enabled = fallback
                if fallback_club_id != t.expected_club_id:
                    problems.append(
                        f"fallback ss.id={t.fallback_source_id}: club_id={fallback_club_id} "
                        f"(expected {t.expected_club_id})"
                    )
                if fallback_priority != 0:
                    problems.append(
                        f"fallback ss.id={t.fallback_source_id}: priority={fallback_priority} "
                        "(expected 0)"
                    )
                if not fallback_enabled:
                    problems.append(f"fallback ss.id={t.fallback_source_id}: enabled is false")

        if problems:
            print("ABORT: shape mismatch - refusing to write:", file=sys.stderr)
            for problem in problems:
                print(f"  {problem}", file=sys.stderr)
            return 1

        print("=== BEFORE ===")
        for t in _DISABLE_TARGETS:
            row = rows[t.source_id]
            sid, cid, platform, _, external_id, priority, enabled, _ = row
            print(
                f"  ss.id={sid:>4} club={cid:>4} {platform:<10} "
                f"ext={str(external_id):<4} pri={priority} enabled={enabled} "
                f"fallback_ss={t.fallback_source_id}"
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
                    "fallback_source_id": t.fallback_source_id,
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
                    f"  ss.id={sid:>4} club={cid:>4} {platform:<10} "
                    f"ext={str(external_id):<4} enabled={enabled}"
                )

    return 0


if __name__ == "__main__":
    sys.exit(main())
