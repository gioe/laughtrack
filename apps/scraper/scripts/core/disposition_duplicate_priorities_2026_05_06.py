#!/usr/bin/env python3
"""
Disposition the 21 enabled (club_id, priority=0) duplicate scraping_sources
groups recorded in the TASK-1967 audit (2026-05-06 snapshot).

Background
----------
TASK-1967 audited the live DB for enabled rows that share (club_id, priority)
across different platforms and recorded 21 unintentional duplicates, every
one of them at priority=0. Each group has the same shape: a manually-
configured primary source on the venue's actual ticketing platform PLUS an
auto-discovered ``seatengine`` row inserted by the ``seatengine_national``
nightly venue-id sweep. The audit lives at
``apps/scraper/docs/audits/task-1967-duplicate-priorities.md``.

The disposition decision for every one of the 21 cases is the same:
**disable the SeatEngine row, keep the manually-configured primary**.
Per-venue diagnostic against the live shows table on 2026-05-06 confirmed
zero of the 21 venues has ANY future show whose ``show_page_url`` contains
``seatengine`` — every venue's primary platform is the producer of record,
and the SE row is silently double-running with no events to show for it.

Demoting the SE row to ``priority=1`` was considered and rejected: the
``seatengine_national`` upsert (``UPSERT_CLUB_BY_SEATENGINE_VENUE`` in
``apps/scraper/sql/club_queries.py``) hardcodes ``priority=0`` and does not
honour priority changes — TASK-1968 only added a carve-out for ``enabled``.
A demoted row would be flipped back to ``priority=0`` on the next nightly
sweep. ``enabled=false`` is the only durable disposition.

Durability mechanism
--------------------
TASK-1968 modified the SeatEngine UPSERT's ``ON CONFLICT (club_id, platform,
priority) DO UPDATE`` clause to preserve ``scraping_sources.enabled`` when
the existing row's metadata carries any ``task_*_disposition`` key. The
disposition stamp written here therefore survives the nightly seatengine_
national sweep — without TASK-1968 the disable would be silently reverted
within 24h (this is exactly what happened to migration
``20260502195959_hide_laugh_and_enjoy_pending_opening`` before TASK-1966
re-disabled and TASK-1968 made it stick).

What this script does
---------------------
1. Validates expected ``(club_id, platform, scraper_key, external_id, priority)``
   shape on each targeted ``scraping_sources`` row (refuses to write on any
   mismatch — collects all problems first).
2. For each target: ``UPDATE scraping_sources SET enabled=false,
   metadata=<merged>::jsonb, updated_at=NOW()`` keyed by ``id``.
3. Stamps ``metadata.task_1979_disposition`` with
   ``kind='cross_platform_priority0_redundant'`` and a per-row rationale,
   mirroring the TASK-1962 / TASK-1966 disposition pattern so the forensic
   audit trail survives downstream upserts.
4. The primary rows (one per club, the manually-configured platform) are
   left untouched — they are the canonical active sources.

Idempotent: only writes when ``enabled`` is currently True OR the metadata
key is missing. Safe to re-run.

Verification
------------
After running this script, ``make check-scraping-priorities`` should exit
0 with no remaining duplicate groups (TASK-1967's CI guard).

Usage
-----
    cd apps/scraper
    make run-script SCRIPT=scripts/core/disposition_duplicate_priorities_2026_05_06.py ARGS='--dry-run'
    make run-script SCRIPT=scripts/core/disposition_duplicate_priorities_2026_05_06.py
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


_METADATA_KEY = "task_1979_disposition"
_DISPOSITION_KIND = "cross_platform_priority0_redundant"


@dataclass(frozen=True)
class DisableTarget:
    """A scraping_sources row to flip enabled=false with a stamped rationale."""

    source_id: int
    expected_club_id: int
    expected_external_id: str       # SeatEngine venue id used to confirm the right row
    primary_source_id: int          # the sibling row at priority=0 that stays enabled
    primary_platform: str           # for the audit-trail rationale
    rationale: str

    expected_platform: str = "seatengine"  # all 21 targets are SeatEngine v1


# Per-row evidence: future-shows URL host distribution captured 2026-05-06 from
# the live DB. "0 SE-domain URLs" means the SE row is producing nothing for the
# venue — the manually-configured primary platform is the producer of record.
_DISABLE_TARGETS: list[DisableTarget] = [
    DisableTarget(
        source_id=931, expected_club_id=80, expected_external_id="617",
        primary_source_id=101, primary_platform="custom (uptown_theater)",
        rationale=(
            "Uptown Theater. Primary ss=101 is the venue's own custom scraper at "
            "uptownpvd.com/events; 19 future shows on 2026-05-06 all served from "
            "uptownpvd.com domain, 0 from SE. SE venue 617 was auto-discovered by "
            "seatengine_national sweep — disable as redundant cross-platform sibling."
        ),
    ),
    DisableTarget(
        source_id=672, expected_club_id=140, expected_external_id="34",
        primary_source_id=444, primary_platform="custom (laugh_boston via pixlcalendar)",
        rationale=(
            "Laugh Boston. Primary ss=444 is the laugh_boston custom scraper "
            "pulling from pixlcalendar.com/api; 137 future shows on 2026-05-06 with 0 "
            "from SE. SE venue 34 (boston-laugh-laugh-boston.seatengine.com) is the "
            "venue's old SE widget — auto-discovered drift, redundant with primary."
        ),
    ),
    DisableTarget(
        source_id=735, expected_club_id=143, expected_external_id="136",
        primary_source_id=510, primary_platform="wix_events",
        rationale=(
            "Nick's Comedy Stop. Primary ss=510 is wix_events ext=comp-m4t1prev on "
            "nickscomedystop.com (a Wix-built site); 9 future shows on 2026-05-06 with "
            "0 from SE. SE venue 136 was auto-discovered against nickscomedystop.com "
            "but the Wix calendar is the canonical source — disable SE as redundant."
        ),
    ),
    DisableTarget(
        source_id=848, expected_club_id=158, expected_external_id="488",
        primary_source_id=167, primary_platform="custom (comedy_store)",
        rationale=(
            "The Comedy Store. Primary ss=167 is the comedy_store custom scraper at "
            "thecomedystore.com/calendar; 288 future shows on 2026-05-06 with 0 from "
            "SE. SE venue 488 (URL also thecomedystore.com) is auto-discovered but "
            "the custom scraper covers the venue's actual calendar — disable SE."
        ),
    ),
    DisableTarget(
        source_id=660, expected_club_id=223, expected_external_id="20",
        primary_source_id=209, primary_platform="custom (post_office_cafe via thundertix)",
        rationale=(
            "Post Office Cafe. Primary ss=209 is the post_office_cafe custom scraper "
            "pulling from postofficecafecabaret.thundertix.com; 232 future shows on "
            "2026-05-06 all from thundertix domain, 0 from SE. SE venue 20 is auto-"
            "discovered drift on postofficecabaret.com — disable as redundant."
        ),
    ),
    DisableTarget(
        source_id=711, expected_club_id=308, expected_external_id="105",
        primary_source_id=191, primary_platform="ticketmaster (live_nation Z7r9jZadLM)",
        rationale=(
            "Funny Bone Columbus. Primary ss=191 is the live_nation Ticketmaster "
            "scraper. 226 future shows on 2026-05-06 served via etix.com (66), "
            "columbus.funnybone.com (10) and ticketmaster.com (4) — 0 from SE. "
            "TASK-1967 audit flagged this as a possible legitimate fallback, but the "
            "data shows SE produces nothing and the upsert hardcodes priority=0 so "
            "demote-to-priority=1 wouldn't stick. Disable SE."
        ),
    ),
    DisableTarget(
        source_id=719, expected_club_id=317, expected_external_id="114",
        primary_source_id=210, primary_platform="ticketmaster (live_nation Z7r9jZa7KA)",
        rationale=(
            "Dayton Funny Bone. Primary ss=210 is the live_nation Ticketmaster "
            "scraper. 84 future shows on 2026-05-06 served via etix.com (66), "
            "dayton.funnybone.com (9), ticketmaster.com (5) — 0 from SE. Same "
            "rationale as club 308: SE produces nothing; demote-priority would be "
            "reverted by the seatengine_national upsert. Disable SE."
        ),
    ),
    DisableTarget(
        source_id=722, expected_club_id=323, expected_external_id="120",
        primary_source_id=193, primary_platform="ticketmaster (live_nation Z7r9jZa7eK)",
        rationale=(
            "Albany Funny Bone. Primary ss=193 is the live_nation Ticketmaster "
            "scraper. 142 future shows on 2026-05-06 served via etix.com (72), "
            "albany.funnybone.com (6), ticketmaster.com (2) — 0 from SE. Same "
            "Funny-Bone-trio rationale as 308/317. Disable SE."
        ),
    ),
    DisableTarget(
        source_id=726, expected_club_id=327, expected_external_id="124",
        primary_source_id=617, primary_platform="showslinger (show_slinger)",
        rationale=(
            "the Comedy Shoppe. Primary ss=617 is the show_slinger Showslinger "
            "scraper for jjcomedy.com (combo_widget id=238). 63 future shows on "
            "2026-05-06 all from app.showslinger.com, 0 from SE. SE venue 124 (URL "
            "jjcomedy.com) is auto-discovered drift — disable as redundant."
        ),
    ),
    DisableTarget(
        source_id=843, expected_club_id=506, expected_external_id="482",
        primary_source_id=578, primary_platform="crowdwork (rails_comedy)",
        rationale=(
            "Rails Comedy. Primary ss=578 is the rails_comedy Crowdwork scraper "
            "(crowdwork.com/api/v2/railscomedy/shows). 11 future shows on 2026-05-06 "
            "all from crowdwork.com, 0 from SE. SE venue 482 (URL railscomedy.com) "
            "is auto-discovered — disable as redundant."
        ),
    ),
    DisableTarget(
        source_id=846, expected_club_id=510, expected_external_id="486",
        primary_source_id=423, primary_platform="eventbrite (43929578463)",
        rationale=(
            "Comedy Blvd (HIDDEN venue). Primary ss=423 is the Eventbrite organiser "
            "43929578463; 0 future shows currently and last_scraped_date is null "
            "(venue is hidden in the schema). Both sources produce nothing today "
            "but the manually-configured Eventbrite source is the canonical one for "
            "comedyblvdla.com if/when the venue reactivates. SE venue 486 was "
            "auto-discovered against the venue domain — disable as redundant."
        ),
    ),
    DisableTarget(
        source_id=880, expected_club_id=552, expected_external_id="532",
        primary_source_id=235, primary_platform="custom (the_bit_theater)",
        rationale=(
            "The Bit Theater. Primary ss=235 is the the_bit_theater custom scraper "
            "for bitimprov.org/event. 16 future shows on 2026-05-06 all from "
            "bitimprov.org, 0 from SE. SE row URL is venue-the-bit-theater-532."
            "seatengine.cloud (a SeatEngine Cloud venue) but it's producing nothing "
            "— the venue's own site is the source of truth. Disable SE."
        ),
    ),
    DisableTarget(
        source_id=895, expected_club_id=571, expected_external_id="551",
        primary_source_id=216, primary_platform="squadup (9086799)",
        rationale=(
            "Sunset Strip. Primary ss=216 is the SquadUp scraper for venue 9086799 "
            "at sunsetstripatx.com/events. 110 future shows on 2026-05-06 all from "
            "squadup.com, 0 from SE. SE venue 551 was auto-discovered against "
            "sunsetstripatx.com — disable as redundant."
        ),
    ),
    DisableTarget(
        source_id=899, expected_club_id=575, expected_external_id="555",
        primary_source_id=401, primary_platform="eventbrite (113948356841)",
        rationale=(
            "The Attic Comedy Club. Primary ss=401 is the Eventbrite organiser "
            "113948356841. 98 future shows on 2026-05-06 all from eventbrite.com, "
            "0 from SE. SE venue 555 (URL theatticcomedy.com) was auto-discovered "
            "by the nightly sweep — disable as redundant cross-platform sibling."
        ),
    ),
    DisableTarget(
        source_id=915, expected_club_id=593, expected_external_id="577",
        primary_source_id=152, primary_platform="eventbrite (87966212103)",
        rationale=(
            "National Lampoon The Yellow Door. Primary ss=152 is the Eventbrite "
            "organiser 87966212103. 122 future shows on 2026-05-06 all from "
            "eventbrite.com, 0 from SE. SE venue 577 (URL nlyellowdoor.com) is "
            "auto-discovered drift — disable as redundant."
        ),
    ),
    DisableTarget(
        source_id=767, expected_club_id=786, expected_external_id="203",
        primary_source_id=350, primary_platform="simpletix",
        rationale=(
            "ImprovCity. Primary ss=350 is the SimpleTix scraper at "
            "simpletix.com/e/improvcity-show-tickets-249393. 64 future shows on "
            "2026-05-06 all from simpletix.com, 0 from SE. SE venue 203 (URL "
            "improvcityonline.com) is auto-discovered — disable as redundant."
        ),
    ),
    DisableTarget(
        source_id=772, expected_club_id=794, expected_external_id="214",
        primary_source_id=37, primary_platform="jetbook",
        rationale=(
            "The Improv Collective. Primary ss=37 is the JetBook scraper for the "
            "improv-collective-srzaf iframe. 86 future shows on 2026-05-06 all "
            "from jetbook.co, 0 from SE. SE venue 214 (URL tickets."
            "improvcollectiveoc.com) is auto-discovered drift — disable as redundant."
        ),
    ),
    DisableTarget(
        source_id=774, expected_club_id=796, expected_external_id="217",
        primary_source_id=452, primary_platform="crowdwork (the_backline)",
        rationale=(
            "The Backline. Primary ss=452 is the the_backline Crowdwork scraper "
            "(crowdwork.com/api/v2/thebacklinecomedytheatre/shows). 286 future "
            "shows on 2026-05-06 all from crowdwork.com, 0 from SE. SE venue 217 "
            "(URL backlinecomedy.com) is auto-discovered — disable as redundant."
        ),
    ),
    DisableTarget(
        source_id=791, expected_club_id=817, expected_external_id="250",
        primary_source_id=111, primary_platform="custom (json_ld)",
        rationale=(
            "Laughing Skull. Primary ss=111 is the json_ld custom scraper for "
            "laughingskulllounge.com/events/. 68 future shows on 2026-05-06 all "
            "from laughingskulllounge.com, 0 from SE. SE venue 250 (URL "
            "laughingskulllounge.com) was auto-discovered against the same domain "
            "but the JSON-LD scraper is the venue's actual source. Disable SE."
        ),
    ),
    DisableTarget(
        source_id=792, expected_club_id=818, expected_external_id="251",
        primary_source_id=57, primary_platform="showpass",
        rationale=(
            "The Comedy Cave. Primary ss=57 is the Showpass scraper at "
            "showpass.com/api/public/venues/comedy-cave/calendar/. 62 future shows "
            "on 2026-05-06, 0 from SE. SE venue 251 (URL comedycave.com) is auto-"
            "discovered drift — disable as redundant."
        ),
    ),
    DisableTarget(
        source_id=798, expected_club_id=826, expected_external_id="265",
        primary_source_id=553, primary_platform="custom (json_ld)",
        rationale=(
            "The Comedy Club On State (HIDDEN venue). Primary ss=553 is the json_ld "
            "custom scraper for madisoncomedy.com/events. 22 future shows on "
            "2026-05-06 from madisoncomedy.com (last_scraped_date 2026-04-16, "
            "currently quiescent). SE venue 265 (URL madisoncomedy.com) is auto-"
            "discovered drift — disable as redundant. Venue stays hidden either "
            "way; this disposition just stops the parallel SE scrape."
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
            "Disable 21 auto-discovered SeatEngine scraping_sources rows that "
            "currently double-run at priority=0 alongside a manually-configured "
            "primary on a different platform. See module docstring for the full "
            "TASK-1967 audit context."
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

        print(f"=== BEFORE ({len(_DISABLE_TARGETS)} targets) ===")
        for t in _DISABLE_TARGETS:
            sid, cid, plat, sk, ext, src_url, pri, en, _ = rows[t.source_id]
            print(
                f"  ss.id={sid:>4} club={cid:>4} {plat:<14} ext={str(ext):<6} "
                f"pri={pri} enabled={en}  primary={t.primary_platform}"
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
                    "primary_source_id": t.primary_source_id,
                    "primary_platform": t.primary_platform,
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
                    f"  ss.id={sid:>4} club={cid:>4} {plat:<14} ext={str(ext):<6} enabled={en}"
                )

    return 0


if __name__ == "__main__":
    sys.exit(main())
