#!/usr/bin/env python3
"""
Triage disposition for the cluster of 'no events found' WARNs emitted by
SeatEngineScraper in the 2026-05-05 nightly. Follow-up to TASK-1942
(investigation) and parent TASK-1950 (this script's disposition).

Background
----------
TASK-1942 ruled out a platform-wide SeatEngine regression:
  - The shared OAuth token, the v1 API at services.seatengine.com, and the
    scraper itself are all healthy.
  - Each affected venue legitimately returns ``{data: []}`` for both
    ``/api/v1/venues/<id>/shows`` and ``/api/v1/venues/<id>/events``.
  - Convention #80 (`tusk conventions show 80`) records the diagnostic SQL:
    8 of the cluster have ``COUNT(shows)=0`` AND
    ``MAX(last_scraped_date) IS NULL`` — i.e., the
    ``scraping_sources`` row was created during initial discovery but never
    populated any shows. Those 8 are stub/dormant, not a regression.

Re-ran the convention-#80 query at TASK-1950 pickup (2026-05-05) on the 14
unique ``(club_id, seatengine_source_id)`` pairs in the description. (The
TASK-1950 description text says "13 venues" but two clubs — 568 and 589 —
each have BOTH a classic ``seatengine`` and a ``seatengine_v3`` source at
priority=0; the WARN log de-duplicated by club, surfacing 13. Inspecting
``scraping_sources`` shows 16 candidate rows. Only one of {classic, v3}
fires per nightly per club, but the dispositional question — "is this
SeatEngine source dead?" — applies to BOTH rows on those two clubs. Safe
to disable both.)

Diagnostic snapshot (2026-05-05):

  Stub / dormant (all_count=0, latest_scraped IS NULL — never produced a show):
    448  Wiseguys Las Vegas       (ss=159 seatengine    ext=423)
    518  The Port Comedy Club     (ss=7   seatengine    ext=494)
    520  Comedy Club at The Park  (ss=112 seatengine    ext=496)
    521  The Royal Comedy Theatre (ss=355 seatengine    ext=497)
    568  The Brick Room           (ss=359 seatengine_v3 ext=c5595eca-…)
    568  The Brick Room           (ss=892 seatengine    ext=548)
    586  Wiseguys - Westgate      (ss=271 seatengine    ext=566)
    589  Midtown Comedy Lounge    (ss=426 seatengine_v3 ext=364f13ff-…)
    589  Midtown Comedy Lounge    (ss=911 seatengine    ext=569)
    1438 The Comedy Scene         (ss=543 seatengine    ext=129)

  Real prior history (last_scraped recent OR future_count > 0):
    63   TK's                              future=94  total=133 latest=2026-03-26
    82   Wicked Funny NA                   future=141 total=187 latest=2026-03-26
    89   Beaches Comedy Club               future=64  total=109 latest=2026-03-26
    485  LAUGH IT UP COMEDY CLUB           future=12  total=18  latest=2026-04-17
    636  Wicked Funny Danvers              future=0   total=2   latest=2026-04-11
    837  Mesquite St. Comedy Club          future=3   total=7   latest=2026-04-28

Disposition matrix (per criterion 6402: kept-as-is / source disabled / venue
closed / scraper adopted)
-------------------------------------------------------------------------

DISABLE-SOURCE — 12 clubs, 14 ``scraping_sources`` rows. Flips
``enabled=false`` and stamps ``metadata.task_1950_disposition`` with the
per-row rationale. Stops the SeatEngine 'no events found' WARN for these
venues on the next nightly. Does NOT delete historical shows; venues with
prior real bookings keep their existing show inventory in place (those
shows simply stop being refreshed from SeatEngine; if they outlive the
event date they age out naturally).

  Stub / dormant (10 sources across 8 clubs — never had real SE bookings):
    448, 518, 520, 521, 568 (both), 586, 589 (both), 1438

  Working fallback at priority=0 (2 clubs — disable just the SE row):
    485  ss=822 (ticketweb ss=313 produced 12 future shows on 2026-04-17)
    837  ss=805 (ticketleap ss=479 produced 3 future shows on 2026-04-28)

  Venue-side state change, real prior history (2 clubs):
    82   ss=146 — wickedfunnynorthandover.com says 'Closed for Renovations'.
                  Disable so SE stops emitting WARN for a venue that may not
                  return; existing 141 future shows remain visible until they
                  age out. A follow-up should decide whether to hide the club
                  and/or clean the stale shows.
    63   ss=52  — tkscomedy.com rebranded as 'Addison/Dallas' (restaurant);
                  comedy reduced to a single menu link. 94 future shows are
                  now stale. Same disable + follow-up disposition pattern.

KEEP-AS-IS — 2 clubs. No DB writes. WARN remains expected on next nightly
for these venues; criterion 6403 explicitly scopes the no-WARN expectation
to "venues whose source was disabled or club was closed/hidden".

  89   Beaches Comedy Club          — beachescomedyclub.com active, currently
                                       no upcoming shows. 64 prior future
                                       shows from 2026-03-26 still visible.
                                       Wait for venue to repopulate.
  636  Wicked Funny Comedy Danvers  — wickedfunnydanvers.com active, only 2
                                       historical shows (latest 2026-04-11);
                                       venue is real but low-cadence.

NO CLUB HIDES IN THIS SCRIPT. Per LaughTrack feedback memory
("Verify each club before batch-hiding" / "Always Playwright MCP before
hide/close"), the hide-club decisions for the 5 venue-side-defunct
candidates (63 TK's, 518 The Port, 520 Comedy Club at The Park, 586
Wiseguys - Westgate, 589 Midtown Comedy Lounge) are deferred to per-venue
follow-up tasks. Disabling the source by itself satisfies criterion 6402
("source disabled" is a recorded disposition) and silences the SeatEngine
WARN.

Post-action verification (criterion 6403) is verified by the follow-up
task filed alongside this script: re-read the next nightly's WARN log and
confirm zero ``SeatEngineScraper [<club>]: no events found`` messages for
the 12 clubs above. The convention #80 diagnostic SQL on the same 14 club
IDs is the canonical verification query.

What this script does
---------------------
1. Validates expected shape of every targeted ``scraping_sources`` row
   (refuses to write on any mismatch — collects all problems first so a
   single re-run surfaces every discrepancy).
2. Per disable target: ``UPDATE scraping_sources SET enabled=false,
   metadata=<...>, updated_at=NOW()`` keyed by ``id``.
3. Stamps ``metadata.task_1950_disposition`` on every modified row with the
   ``kind`` (``stub_dormant`` / ``fallback_redundant`` / ``venue_state_change``)
   and a per-row rationale, matching the TASK-1918 / TASK-1925 pattern so the
   audit trail survives downstream upserts.

Idempotent: only writes when ``enabled`` is currently True OR the metadata
key is missing. Safe to re-run.

Usage
-----
    cd apps/scraper
    make run-script SCRIPT=scripts/core/disposition_seatengine_no_events_2026_05_05.py ARGS='--dry-run'
    make run-script SCRIPT=scripts/core/disposition_seatengine_no_events_2026_05_05.py
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


_METADATA_KEY = "task_1950_disposition"


@dataclass(frozen=True)
class DisableTarget:
    """A scraping_sources row to flip enabled=false with a stamped rationale."""

    source_id: int
    expected_club_id: int
    expected_platform: str          # 'seatengine' or 'seatengine_v3'
    expected_external_id: str       # external_id used to confirm the right row
    kind: str                       # 'stub_dormant' / 'fallback_redundant' / 'venue_state_change'
    rationale: str


_DISABLE_TARGETS: list[DisableTarget] = [
    # --- venue-side state change (real prior scrape history) ---
    DisableTarget(
        source_id=52,
        expected_club_id=63,
        expected_platform="seatengine",
        expected_external_id="514",
        kind="venue_state_change",
        rationale=(
            "tkscomedy.com rebranded as 'Addison/Dallas' restaurant; comedy "
            "reduced to one menu link. /api/v1/venues/514/shows returns "
            "{data: []}. 94 future shows on the club are stale (last scraped "
            "2026-03-26); disable stops SE WARNs but leaves stale shows in "
            "place — a per-venue follow-up should decide whether to hide the "
            "club and clean the stale show inventory."
        ),
    ),
    DisableTarget(
        source_id=146,
        expected_club_id=82,
        expected_platform="seatengine",
        expected_external_id="487",
        kind="venue_state_change",
        rationale=(
            "wickedfunnynorthandover.com says 'Closed for Renovations'. "
            "/api/v1/venues/487/shows returns {data: []}. 141 future shows on "
            "the club are stale (last scraped 2026-03-26); disable stops SE "
            "WARNs and lets the source be re-enabled if the venue reopens. A "
            "per-venue follow-up should decide whether to hide the club / "
            "clean the stale show inventory before reopening."
        ),
    ),

    # --- stub / dormant (never produced a show) ---
    DisableTarget(
        source_id=159,
        expected_club_id=448,
        expected_platform="seatengine",
        expected_external_id="423",
        kind="stub_dormant",
        rationale=(
            "Stub: COUNT(shows)=0 AND latest_scraped IS NULL — convention #80 "
            "treats this as a never-real row. arts-district.wiseguyscomedy.com "
            "is reachable but the SE calendar has been empty since the source "
            "was created. Disable to silence WARN; re-enable if Wiseguys ever "
            "begins booking through this SE venue id."
        ),
    ),
    DisableTarget(
        source_id=7,
        expected_club_id=518,
        expected_platform="seatengine",
        expected_external_id="494",
        kind="stub_dormant",
        rationale=(
            "Stub (COUNT(shows)=0 / latest_scraped IS NULL) AND theportcomedyclub.com "
            "is unreachable (HTTP 000). No evidence the venue ever booked through "
            "SE. Disable; if a future club detail surfaces, file fresh as a new "
            "scraping_source rather than reviving this stub."
        ),
    ),
    DisableTarget(
        source_id=112,
        expected_club_id=520,
        expected_platform="seatengine",
        expected_external_id="496",
        kind="stub_dormant",
        rationale=(
            "Stub (COUNT(shows)=0 / latest_scraped IS NULL); comedyclubatthepark.com "
            "renders blank/placeholder. No evidence of historical bookings on SE."
        ),
    ),
    DisableTarget(
        source_id=355,
        expected_club_id=521,
        expected_platform="seatengine",
        expected_external_id="497",
        kind="stub_dormant",
        rationale=(
            "Stub (COUNT(shows)=0 / latest_scraped IS NULL). royalcomedy.ca returns "
            "Cloudflare 403 to direct fetches; SE v1 API confirms 0 shows under "
            "venue id 497. Disabling is safe regardless of whether the public "
            "site has bookings — there is no historical SE-sourced inventory to "
            "lose. If a future audit (e.g. via Playwright bypassing CF) surfaces "
            "real shows, a fresh scraping_source can be added."
        ),
    ),
    DisableTarget(
        source_id=359,
        expected_club_id=568,
        expected_platform="seatengine_v3",
        expected_external_id="c5595eca-1589-485a-9488-e01d4d455d76",
        kind="stub_dormant",
        rationale=(
            "Stub (COUNT(shows)=0 / latest_scraped IS NULL). Club 568 has BOTH a "
            "v3 and a classic SE source at priority=0; neither has produced a "
            "show. Disabling both."
        ),
    ),
    DisableTarget(
        source_id=892,
        expected_club_id=568,
        expected_platform="seatengine",
        expected_external_id="548",
        kind="stub_dormant",
        rationale=(
            "Stub (COUNT(shows)=0 / latest_scraped IS NULL). Sibling of v3 row "
            "ss=359 above; disabling the second of two parallel SE rows on "
            "club 568."
        ),
    ),
    DisableTarget(
        source_id=271,
        expected_club_id=586,
        expected_platform="seatengine",
        expected_external_id="566",
        kind="stub_dormant",
        rationale=(
            "Stub (COUNT(shows)=0 / latest_scraped IS NULL); "
            "westgate.wiseguyscomedy.com is unreachable. No historical SE "
            "bookings; disable."
        ),
    ),
    DisableTarget(
        source_id=426,
        expected_club_id=589,
        expected_platform="seatengine_v3",
        expected_external_id="364f13ff-86b9-479f-9720-bd191e285ac3",
        kind="stub_dormant",
        rationale=(
            "Stub (COUNT(shows)=0 / latest_scraped IS NULL). Club 589 has BOTH "
            "a v3 and a classic SE source at priority=0; neither has produced "
            "a show. midtowncomedylounge.com unreachable. Disabling both."
        ),
    ),
    DisableTarget(
        source_id=911,
        expected_club_id=589,
        expected_platform="seatengine",
        expected_external_id="569",
        kind="stub_dormant",
        rationale=(
            "Stub (COUNT(shows)=0 / latest_scraped IS NULL). Sibling of v3 row "
            "ss=426 above; disabling the second of two parallel SE rows on "
            "club 589."
        ),
    ),
    DisableTarget(
        source_id=543,
        expected_club_id=1438,
        expected_platform="seatengine",
        expected_external_id="129",
        kind="stub_dormant",
        rationale=(
            "Stub (COUNT(shows)=0 / latest_scraped IS NULL). "
            "the-comedy-scene.seatengine.com renders the SE storefront with no "
            "calendar entries; venue id 129 has never produced a show. Disable."
        ),
    ),

    # --- fallback redundant (working non-SE fallback at priority=0) ---
    DisableTarget(
        source_id=822,
        expected_club_id=485,
        expected_platform="seatengine",
        expected_external_id="461",
        kind="fallback_redundant",
        rationale=(
            "ticketweb fallback (ss=313, also priority=0) produced 12 future "
            "shows on 2026-04-17. SE row has been redundant since the "
            "ticketweb source was added; disable to stop the parallel WARN."
        ),
    ),
    DisableTarget(
        source_id=805,
        expected_club_id=837,
        expected_platform="seatengine",
        expected_external_id="279",
        kind="fallback_redundant",
        rationale=(
            "ticketleap fallback (ss=479, also priority=0) produced 3 future "
            "shows on 2026-04-28. laughdowntown.com is unreachable, but the "
            "ticketleap feed continues to cover Mesquite St. bookings; SE row "
            "is redundant."
        ),
    ),
]

# Recorded for criterion 6402 ("each of the venues has a recorded disposition"):
# venues left with no DB write under this disposition.
_KEEP_AS_IS_CLUBS: list[tuple[int, str, str]] = [
    (
        89,
        "Beaches Comedy Club",
        "Real prior history (109 shows, latest 2026-03-26); beachescomedyclub.com "
        "is active. SE calendar currently empty but venue is alive — wait for "
        "repopulation. Accept the transient WARN.",
    ),
    (
        636,
        "Wicked Funny Comedy Club Danvers",
        "Real prior history (2 shows, latest 2026-04-11); wickedfunnydanvers.com "
        "is active. Low-cadence venue but live. Accept the transient WARN.",
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
            "Disable 14 SeatEngine scraping_sources across 12 of the 14 venues "
            "that emitted 'no events found' WARNs in the 2026-05-05 nightly. "
            "See module docstring for the full disposition matrix and rationale."
        )
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()

    target_ids = [t.source_id for t in _DISABLE_TARGETS]

    with get_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, club_id, platform, scraper_key, external_id, source_url,
                       priority, enabled, metadata
                FROM scraping_sources WHERE id = ANY(%s) ORDER BY id
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
            if external_id != t.expected_external_id:
                problems.append(
                    f"ss.id={t.source_id}: external_id={external_id!r} "
                    f"(expected {t.expected_external_id!r})"
                )
            if priority != 0:
                problems.append(
                    f"ss.id={t.source_id}: priority={priority} "
                    f"(expected 0 — disposition was constructed against the priority=0 SE row)"
                )

        if problems:
            print("ABORT: shape mismatch — refusing to write:", file=sys.stderr)
            for p in problems:
                print(f"  {p}", file=sys.stderr)
            return 1

        print("=== BEFORE ===")
        for t in _DISABLE_TARGETS:
            r = rows[t.source_id]
            sid, cid, p, sk, ext, src_url, pri, en, _ = r
            print(
                f"  ss.id={sid:>4} club={cid:>4} {p:<14} ext={ext:<10} "
                f"pri={pri} enabled={en} kind={t.kind}"
            )
        if _KEEP_AS_IS_CLUBS:
            print("\n=== KEEP-AS-IS (no DB write — recorded for audit only) ===")
            for cid, name, why in _KEEP_AS_IS_CLUBS:
                print(f"  club={cid:>4} {name!r:<35} {why[:90]}...")

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
                    "kind": t.kind,
                    "rationale": t.rationale,
                }
                action = "PLAN " if args.dry_run else "WRITE"
                print(
                    f"  {action} ss={t.source_id} (club {t.expected_club_id}): "
                    f"enabled={enabled}→FALSE + metadata[{_METADATA_KEY}]={t.kind!r}"
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
                SELECT id, club_id, platform, external_id, enabled
                FROM scraping_sources WHERE id = ANY(%s) ORDER BY id
                """,
                (target_ids,),
            )
            for sid, cid, p, ext, en in cur.fetchall():
                print(f"  ss.id={sid:>4} club={cid:>4} {p:<14} ext={ext:<10} enabled={en}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
