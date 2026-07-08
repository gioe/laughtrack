#!/usr/bin/env python3
"""
Apply TASK-1954 hide/keep dispositions for five SeatEngine no-event venues.

Background
----------
TASK-1950 disabled the SeatEngine sources for these venues after their
SeatEngine APIs stopped returning events. The remaining question for
TASK-1954 is whether the clubs themselves should be hidden.

Playwright verification on 2026-05-06:

  63   TK's
       https://www.tkscomedy.com renders a live TK's Comedy page for
       Addison/Dallas with comedy, shows, events, and ticketing language.
       Disposition: leave visible.

  518  The Port Comedy Club
       https://theportcomedyclub.com fails DNS resolution, the DB row has no
       website, and the SeatEngine source never produced shows.
       Disposition: hide club.

  520  Comedy Club at The Park
       https://www.thepark.com/comedy-club/ renders a live Comedy Club page
       with calendar/ticketing language.
       Disposition: leave visible.

  586  Wiseguys - Westgate
       The task references club id 586, but that row and its SeatEngine
       source are already absent from the live database. The public
       https://westgate.wiseguyscomedy.com SeatEngine page renders a live
       Wiseguys - Westgate shell with upcoming-show navigation.
       Disposition: already absent; no DB write possible.

  589  Midtown Comedy Lounge
       https://midtowncomedylounge.com fails DNS, but the club's current
       SeatEngine-hosted website
       https://v-364f13ff-86b9-479f-9720-bd191e285ac3.seatengine.net/ renders
       a Midtown Comedy Lounge page with event navigation and contact info.
       Disposition: leave visible.

What this script does
---------------------
1. Validates the expected shape of available clubs and scraping_sources rows.
2. Sets clubs.id=518 visible=false.
3. Stamps metadata.task_1954_hide on each available target SeatEngine source
   with the per-club disposition and rationale.

Idempotent: only writes when the club is still visible or the source metadata
key is missing / differs. Safe to re-run.

Usage
-----
    cd apps/scraper
    make run-script SCRIPT=scripts/core/disposition_seatengine_hide_no_event_venues_2026_05_06.py ARGS='--dry-run'
    make run-script SCRIPT=scripts/core/disposition_seatengine_hide_no_event_venues_2026_05_06.py
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


_METADATA_KEY = "task_1954_hide"


@dataclass(frozen=True)
class HideTarget:
    """A club disposition with associated SeatEngine source rows to annotate."""

    club_id: int
    expected_name: str
    source_ids: list[int]
    disposition: str
    rationale: str
    hide_club: bool = False
    allow_missing: bool = False


_HIDE_TARGETS: list[HideTarget] = [
    HideTarget(
        club_id=63,
        expected_name="TK's",
        source_ids=[52],
        disposition="left_visible_live_site",
        rationale=(
            "Playwright rendered https://www.tkscomedy.com as a live TK's "
            "Comedy Addison/Dallas page with shows, events, and ticketing "
            "language. Do not hide; source remains disabled from TASK-1950."
        ),
    ),
    HideTarget(
        club_id=518,
        expected_name="The Port Comedy Club",
        source_ids=[7],
        disposition="hidden_defunct",
        rationale=(
            "Playwright failed DNS for https://theportcomedyclub.com; the club "
            "row has no website and its SeatEngine source never produced shows. "
            "Hide the visible stub venue."
        ),
        hide_club=True,
    ),
    HideTarget(
        club_id=520,
        expected_name="Comedy Club at The Park",
        source_ids=[112],
        disposition="left_visible_live_site",
        rationale=(
            "Playwright rendered https://www.thepark.com/comedy-club/ as a live "
            "Comedy Club page with calendar and ticketing language. Do not hide; "
            "source remains disabled from TASK-1950."
        ),
    ),
    HideTarget(
        club_id=586,
        expected_name="Wiseguys - Westgate",
        source_ids=[271],
        disposition="already_absent",
        rationale=(
            "The clubs row and SeatEngine source referenced by TASK-1950 are "
            "already absent from the live database. Playwright rendered the "
            "public Westgate SeatEngine page as a live Wiseguys shell, so there "
            "is no remaining club row to hide in this task."
        ),
        allow_missing=True,
    ),
    HideTarget(
        club_id=589,
        expected_name="Midtown Comedy Lounge",
        source_ids=[426, 911],
        disposition="left_visible_seatengine_site",
        rationale=(
            "The old midtowncomedylounge.com domain fails DNS, but Playwright "
            "rendered the current SeatEngine-hosted website as a Midtown Comedy "
            "Lounge page with event navigation and contact info. Do not hide; "
            "sources remain disabled from TASK-1950."
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()

    club_ids = [target.club_id for target in _HIDE_TARGETS]
    source_ids = [source_id for target in _HIDE_TARGETS for source_id in target.source_ids]

    with get_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, website, visible, status, closed_at
                FROM clubs
                WHERE id = ANY(%s)
                ORDER BY id
                """,
                (club_ids,),
            )
            clubs = {row[0]: row for row in cur.fetchall()}

            cur.execute(
                """
                SELECT id, club_id, platform::text, scraper_key, external_id,
                       priority, enabled, metadata
                FROM scraping_sources
                WHERE id = ANY(%s)
                ORDER BY id
                """,
                (source_ids,),
            )
            sources = {row[0]: row for row in cur.fetchall()}

            cur.execute(
                """
                SELECT club_id, COUNT(*) AS total_shows
                FROM shows
                WHERE club_id = ANY(%s)
                GROUP BY club_id
                """,
                (club_ids,),
            )
            show_counts = {row[0]: row[1] for row in cur.fetchall()}

        problems: list[str] = []
        for target in _HIDE_TARGETS:
            club = clubs.get(target.club_id)
            if club is None:
                if not target.allow_missing:
                    problems.append(f"clubs.id={target.club_id} missing")
            else:
                _, name, _, _, _, _ = club
                if name != target.expected_name:
                    problems.append(
                        f"clubs.id={target.club_id} name={name!r} "
                        f"(expected {target.expected_name!r})"
                    )

            for source_id in target.source_ids:
                source = sources.get(source_id)
                if source is None:
                    if not target.allow_missing:
                        problems.append(f"scraping_sources.id={source_id} missing")
                    continue

                _, club_id, platform, scraper_key, _, _, _, _ = source
                if club_id != target.club_id:
                    problems.append(
                        f"scraping_sources.id={source_id} club_id={club_id} "
                        f"(expected {target.club_id})"
                    )
                if platform not in {"seatengine", "seatengine_v3"}:
                    problems.append(
                        f"scraping_sources.id={source_id} platform={platform!r} "
                        "(expected SeatEngine platform)"
                    )
                if scraper_key != platform:
                    problems.append(
                        f"scraping_sources.id={source_id} scraper_key={scraper_key!r} "
                        f"(expected {platform!r})"
                    )

            if target.hide_club and show_counts.get(target.club_id, 0) != 0:
                problems.append(
                    f"clubs.id={target.club_id} has {show_counts[target.club_id]} shows; "
                    "refusing to hide without a show cleanup decision"
                )

        if problems:
            print("ABORT: shape mismatch - refusing to write:", file=sys.stderr)
            for problem in problems:
                print(f"  {problem}", file=sys.stderr)
            return 1

        print("=== BEFORE ===")
        for target in _HIDE_TARGETS:
            club = clubs.get(target.club_id)
            if club is None:
                print(
                    f"  clubs.id={target.club_id:>4} {target.expected_name!r}: "
                    "missing; disposition=already_absent"
                )
            else:
                cid, name, website, visible, status, closed_at = club
                print(
                    f"  clubs.id={cid:>4} name={name!r} visible={visible} "
                    f"status={status!r} closed_at={closed_at} shows={show_counts.get(cid, 0)} "
                    f"website={website!r} disposition={target.disposition}"
                )

            for source_id in target.source_ids:
                source = sources.get(source_id)
                if source is None:
                    print(f"    scraping_sources.id={source_id}: missing")
                else:
                    sid, src_club_id, platform, _, external_id, priority, enabled, metadata = source
                    metadata = _load_metadata(metadata)
                    print(
                        f"    ss.id={sid:>4} club={src_club_id:>4} {platform:<13} "
                        f"ext={str(external_id):<40} pri={priority} enabled={enabled} "
                        f"has_task_metadata={_METADATA_KEY in metadata}"
                    )

        writes_planned = 0
        club_updates: list[int] = []
        source_updates: list[tuple[int, dict]] = []

        for target in _HIDE_TARGETS:
            club = clubs.get(target.club_id)
            if target.hide_club and club is not None and club[3]:
                club_updates.append(target.club_id)
                writes_planned += 1

            for source_id in target.source_ids:
                source = sources.get(source_id)
                if source is None:
                    continue
                metadata = _load_metadata(source[7])
                next_payload = {
                    "club_id": target.club_id,
                    "disposition": target.disposition,
                    "hide_club": target.hide_club,
                    "rationale": target.rationale,
                }
                if metadata.get(_METADATA_KEY) != next_payload:
                    next_metadata = dict(metadata)
                    next_metadata[_METADATA_KEY] = next_payload
                    source_updates.append((source_id, next_metadata))
                    writes_planned += 1

        print()
        print(f"club visibility updates planned: {club_updates}")
        print(f"source metadata updates planned: {[sid for sid, _ in source_updates]}")

        if writes_planned == 0:
            print("\nNo changes needed (idempotent re-run).")
            return 0

        if args.dry_run:
            print("\n--dry-run: no DB write performed.")
            return 0

        with conn.cursor() as cur:
            for club_id in club_updates:
                cur.execute(
                    "UPDATE clubs SET visible = FALSE WHERE id = %s AND visible = TRUE "
                    "RETURNING id, visible",
                    (club_id,),
                )
                print(f"updated club: {cur.fetchone()}")

            for source_id, metadata in source_updates:
                cur.execute(
                    "UPDATE scraping_sources SET metadata = %s, updated_at = NOW() "
                    "WHERE id = %s RETURNING id, metadata",
                    (json.dumps(metadata), source_id),
                )
                print(f"updated source: {cur.fetchone()}")

        print("\n=== AFTER ===")
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, visible FROM clubs WHERE id = ANY(%s) ORDER BY id",
                (club_ids,),
            )
            for row in cur.fetchall():
                print(f"  clubs.id={row[0]} visible={row[1]}")

            cur.execute(
                "SELECT id, metadata FROM scraping_sources WHERE id = ANY(%s) ORDER BY id",
                (source_ids,),
            )
            for source_id, metadata in cur.fetchall():
                loaded = _load_metadata(metadata)
                print(f"  ss.id={source_id} {_METADATA_KEY}={loaded.get(_METADATA_KEY)!r}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
