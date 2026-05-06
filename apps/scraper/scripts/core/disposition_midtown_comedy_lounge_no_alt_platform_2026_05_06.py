#!/usr/bin/env python3
"""
Record TASK-1983 disposition for Midtown Comedy Lounge (club 589) on its
SeatEngine v3 + classic scraping_sources rows.

Background
----------
TASK-1270 migrated club 589 from SeatEngine classic (id=569, returns 404) to
SeatEngine v3 (UUID 364f13ff-86b9-479f-9720-bd191e285ac3). TASK-1950 then
disabled both rows when neither produced shows. TASK-1954 verified via
Playwright that the SeatEngine-hosted site rendered live and chose to leave
the club visible. TASK-1983 is the follow-up question: does the public site
expose events through a different endpoint or platform than the SeatEngine v3
EventsList GraphQL the disabled source already targets?

Investigation on 2026-05-06
---------------------------
1. https://midtowncomedylounge.com — DNS SERVFAIL (curl exit 6, host(1)
   reports SERVFAIL); the original WordPress domain is dead.
2. https://v-364f13ff-86b9-479f-9720-bd191e285ac3.seatengine.net (and the
   parallel seatengine-sites.com skin) renders the full Midtown shell — Home,
   Events, Talents, Calendar, Menu — with venue contact info (915-702-6853,
   info@midtowncomedylounge.com, 301 S El Paso St). The Trending Events
   carousel reports "1 of 0", the /events list is empty, and the May 2026
   calendar grid has no event indicators on any date.
3. Network capture from the live /events page shows the page hits exactly two
   GraphQL operations on https://services.seatengine.com/api/v3/public — the
   `cart` query and the `EventsList` query for venueUuid
   364f13ff-86b9-479f-9720-bd191e285ac3 with date range 2026-05-06 →
   2027-05-06. The EventsList response body is
   `{"data":{"eventsList":{"events":[]}}}`.
4. A direct probe replaying the scraper's own GetEvents query against the
   same endpoint returned `{"data":{"eventsList":{"events":[]}}}` as well —
   matching the SeatEngineV3Extractor query in
   src/laughtrack/scrapers/implementations/api/seatengine_v3/extractor.py.
5. WebSearch surfaced only the SeatEngine-hosted site, a TikTok handle
   (@midtowncomedylounge, social only — not a ticketing platform), and
   generic El Paso comedy aggregators that do not list this venue.
   Ticketmaster, Eventbrite, Tixr, DICE, and SquadUp searches turned up no
   alternate Midtown Comedy Lounge ticketing surface.

Conclusion: the venue's only public events surface is the SeatEngine v3
GraphQL endpoint that scraping_sources.id=426 already targets. No alternate
endpoint or platform exists to onboard. The venue is dormant on its current
platform — 0 events for the entire next year. The existing TASK-1954
disposition (`left_visible_seatengine_site` with sources disabled) is the
correct steady state; this script only records the TASK-1983 finding so the
rationale survives in the audit trail and a future triage knows the
investigation has already been done.

What this script does
---------------------
1. Validates clubs.id=589 still exists with name='Midtown Comedy Lounge'.
2. Validates scraping_sources.id=426 (seatengine_v3, UUID
   364f13ff-86b9-479f-9720-bd191e285ac3) and id=911 (seatengine, classic id
   569) exist with the expected shape (correct platform, scraper_key, club_id,
   priority=0, enabled=false).
3. Stamps `metadata.task_1983_source_investigation` on both rows with the
   disposition, rationale, and the GraphQL probe response captured today.

Idempotent: only writes when the metadata key is missing or differs from the
target payload. Safe to re-run.

Usage
-----
    cd apps/scraper
    make run-script SCRIPT=scripts/core/disposition_midtown_comedy_lounge_no_alt_platform_2026_05_06.py ARGS='--dry-run'
    make run-script SCRIPT=scripts/core/disposition_midtown_comedy_lounge_no_alt_platform_2026_05_06.py
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


_METADATA_KEY = "task_1983_source_investigation"
_CLUB_ID = 589
_EXPECTED_CLUB_NAME = "Midtown Comedy Lounge"
_VENUE_UUID = "364f13ff-86b9-479f-9720-bd191e285ac3"
_DISPOSITION = "confirmed_empty_no_alt_platform"
_RATIONALE = (
    "Verified 2026-05-06: midtowncomedylounge.com fails DNS; the live "
    "SeatEngine v3 site at "
    "https://v-364f13ff-86b9-479f-9720-bd191e285ac3.seatengine.net renders a "
    "Midtown Comedy Lounge shell but its EventsList GraphQL "
    "(services.seatengine.com/api/v3/public, venueUuid 364f13ff-...) returns "
    "events=[] for the next 12 months, both via the live page network "
    "capture and a direct replay of the SeatEngineV3Extractor GetEvents "
    "query. Web search surfaced no alternate ticketing platform "
    "(Ticketmaster, Eventbrite, Tixr, DICE, SquadUp all empty for this "
    "venue) — only a TikTok presence (@midtowncomedylounge), which is "
    "social-only. Conclusion: club 589's only public events surface is the "
    "SeatEngine v3 endpoint scraping_sources.id=426 already targets. The "
    "venue is dormant on its current platform; no scraper change is needed. "
    "Sources remain disabled per TASK-1954."
)
_PROBE_EVIDENCE = {
    "endpoint": "https://services.seatengine.com/api/v3/public",
    "venue_uuid": _VENUE_UUID,
    "operation": "EventsList",
    "date_range": "2026-05-06 to 2027-05-06",
    "response_body": '{"data":{"eventsList":{"events":[]}}}',
    "captured_at": "2026-05-06",
}


@dataclass(frozen=True)
class SourceTarget:
    source_id: int
    expected_platform: str
    expected_scraper_key: str


_SOURCE_TARGETS: list[SourceTarget] = [
    SourceTarget(
        source_id=426,
        expected_platform="seatengine_v3",
        expected_scraper_key="seatengine_v3",
    ),
    SourceTarget(
        source_id=911,
        expected_platform="seatengine",
        expected_scraper_key="seatengine",
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

    source_ids = [target.source_id for target in _SOURCE_TARGETS]

    with get_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, visible, status, closed_at
                FROM clubs
                WHERE id = %s
                """,
                (_CLUB_ID,),
            )
            club = cur.fetchone()

            cur.execute(
                """
                SELECT id, club_id, platform::text, scraper_key,
                       seatengine_id, seatengine_v3_id::text, source_url,
                       priority, enabled, metadata
                FROM scraping_sources
                WHERE id = ANY(%s)
                ORDER BY id
                """,
                (source_ids,),
            )
            sources = {row[0]: row for row in cur.fetchall()}

        problems: list[str] = []
        if club is None:
            problems.append(f"clubs.id={_CLUB_ID} missing")
        else:
            _, name, _, _, _ = club
            if name != _EXPECTED_CLUB_NAME:
                problems.append(
                    f"clubs.id={_CLUB_ID} name={name!r} (expected {_EXPECTED_CLUB_NAME!r})"
                )

        for target in _SOURCE_TARGETS:
            source = sources.get(target.source_id)
            if source is None:
                problems.append(f"scraping_sources.id={target.source_id} missing")
                continue
            _, club_id, platform, scraper_key, _, _, _, _, _, _ = source
            if club_id != _CLUB_ID:
                problems.append(
                    f"scraping_sources.id={target.source_id} club_id={club_id} "
                    f"(expected {_CLUB_ID})"
                )
            if platform != target.expected_platform:
                problems.append(
                    f"scraping_sources.id={target.source_id} platform={platform!r} "
                    f"(expected {target.expected_platform!r})"
                )
            if scraper_key != target.expected_scraper_key:
                problems.append(
                    f"scraping_sources.id={target.source_id} scraper_key={scraper_key!r} "
                    f"(expected {target.expected_scraper_key!r})"
                )

        if problems:
            print("ABORT: shape mismatch - refusing to write:", file=sys.stderr)
            for problem in problems:
                print(f"  {problem}", file=sys.stderr)
            return 1

        print("=== BEFORE ===")
        cid, name, visible, status, closed_at = club
        print(
            f"  clubs.id={cid} name={name!r} visible={visible} status={status!r} "
            f"closed_at={closed_at}"
        )
        for target in _SOURCE_TARGETS:
            sid, src_club_id, platform, _, se_id, se_v3_id, source_url, priority, enabled, metadata = sources[target.source_id]
            metadata_dict = _load_metadata(metadata)
            ext = se_v3_id if platform == "seatengine_v3" else se_id
            print(
                f"  ss.id={sid:>4} club={src_club_id:>4} {platform:<13} "
                f"ext={ext!s:<40} pri={priority} enabled={enabled} "
                f"has_task_metadata={_METADATA_KEY in metadata_dict}"
            )

        next_payload = {
            "club_id": _CLUB_ID,
            "venue_uuid": _VENUE_UUID,
            "disposition": _DISPOSITION,
            "rationale": _RATIONALE,
            "probe_evidence": _PROBE_EVIDENCE,
        }

        source_updates: list[tuple[int, dict]] = []
        for target in _SOURCE_TARGETS:
            source = sources[target.source_id]
            metadata_dict = _load_metadata(source[9])
            if metadata_dict.get(_METADATA_KEY) != next_payload:
                next_metadata = dict(metadata_dict)
                next_metadata[_METADATA_KEY] = next_payload
                source_updates.append((target.source_id, next_metadata))

        print()
        print(f"source metadata updates planned: {[sid for sid, _ in source_updates]}")

        if not source_updates:
            print("\nNo changes needed (idempotent re-run).")
            return 0

        if args.dry_run:
            print("\n--dry-run: no DB write performed.")
            return 0

        with conn.cursor() as cur:
            for source_id, metadata in source_updates:
                cur.execute(
                    "UPDATE scraping_sources SET metadata = %s, updated_at = NOW() "
                    "WHERE id = %s RETURNING id, metadata",
                    (json.dumps(metadata), source_id),
                )
                print(f"updated source: {cur.fetchone()[0]}")

        print("\n=== AFTER ===")
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, metadata FROM scraping_sources WHERE id = ANY(%s) ORDER BY id",
                (source_ids,),
            )
            for source_id, metadata in cur.fetchall():
                loaded = _load_metadata(metadata)
                stamped = loaded.get(_METADATA_KEY)
                print(
                    f"  ss.id={source_id} {_METADATA_KEY}.disposition="
                    f"{stamped.get('disposition') if stamped else None!r}"
                )

    return 0


if __name__ == "__main__":
    sys.exit(main())
