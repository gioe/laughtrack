#!/usr/bin/env python3
"""
Resolve the 2 TicketWeb-platform venues that returned 0 events in the
2026-05-05 production nightly (GHA run 25403481982).

Background
----------
Both venues surfaced ``TicketWebScraper [<club>]: No events found on <url>`` in
the nightly. ticketweb is on the residential-proxy allowlist so this is not an
IP-level block; root causes are venue-side and need targeted dispositions:

  463  The Stand Up Comedy Club  ss=286 (priority=0, ticketweb)
                                 source_url https://www.thestandupclub.com/calendar/ → 404
                                 The ``tw-plugin-upcoming-event-list`` widget
                                 still ships on the venue site — it just moved
                                 to the homepage. Fetching '/' returns 15
                                 future shows that the existing HTML fallback
                                 path (``extract_html_calendar_events``) parses
                                 verbatim. Repointing source_url to '/' restores
                                 coverage with zero code change.

  485  LAUGH IT UP COMEDY CLUB   ss=313 (priority=0, ticketweb)
                                 source_url https://www.laughitupcomedy.com/calendar/
                                 → 308 → 200, but the page is now a Next.js app
                                 (no WordPress, no ``tw-plugin``, no
                                 ``var all_events``, no ``ticketweb`` strings in
                                 the SSR HTML). Footer reads "Powered by
                                 Punchup" and the runtime backend is Supabase
                                 (xudgmlzkdlowirdrfhmw.supabase.co). The venue
                                 has migrated TicketWeb → Punchup; the
                                 TicketWeb scraper will never recover events
                                 from the new platform. Disable the row and
                                 file a follow-up adoption task — Punchup is
                                 already supported via PunchupExtractor (used
                                 by comedy_key_west, west_side,
                                 newport_comedy_series venue scrapers).

Stand Up Club fix is repoint, not disable: ``UPDATE scraping_sources SET
source_url=...`` keyed by id. LAUGH IT UP fix is disable + metadata stamp,
mirroring the convention #79 disposition pattern (TASK-1924/1950/1966).

Side note on club 485 ss=822 (SeatEngine, ext=461): TASK-1950 disabled it as
``fallback_redundant`` with rationale "ticketweb fallback (ss=313, also
priority=0) produced 12 future shows on 2026-04-17". That premise is now
stale — ticketweb is broken for this venue. Re-enabling the SE row is an
alternative to adopting Punchup; the call belongs to the follow-up task, not
this XS regression triage. The Punchup-adoption follow-up references this
explicitly so the trade-off is captured in the audit trail.

What this script does
---------------------
1. Validates expected ``(club_id, platform, scraper_key, priority)`` shape on
   each targeted ``scraping_sources`` row (refuses to write on any mismatch —
   collects all problems first).
2. ss=286 (club 463): ``UPDATE scraping_sources SET source_url='<new>',
   metadata=metadata||<stamp>::jsonb, updated_at=NOW()``. Stamp records
   ``kind='source_url_relocated'`` with the old/new URLs.
3. ss=313 (club 485): ``UPDATE scraping_sources SET enabled=false,
   metadata=metadata||<stamp>::jsonb, updated_at=NOW()``. Stamp records
   ``kind='platform_migration'`` with old platform 'ticketweb' and new
   platform 'punchup'.
4. Idempotent: only writes when live state differs from target (URL already
   points to '/' OR enabled already false AND metadata key already present).

Usage
-----
    cd apps/scraper
    make run-script SCRIPT=scripts/core/disposition_ticketweb_regression_2026_05_05.py ARGS='--dry-run'
    make run-script SCRIPT=scripts/core/disposition_ticketweb_regression_2026_05_05.py
"""

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from dotenv import load_dotenv

load_dotenv(_root / ".env")

from laughtrack.adapters.db import get_transaction


_METADATA_KEY = "task_1943_disposition"


@dataclass(frozen=True)
class RepointTarget:
    """A scraping_sources row to repoint via source_url update + metadata stamp."""

    source_id: int
    expected_club_id: int
    expected_platform: str
    expected_scraper_key: str
    old_source_url: str
    new_source_url: str
    rationale: str


@dataclass(frozen=True)
class DisableTarget:
    """A scraping_sources row to flip enabled=false with a stamped rationale."""

    source_id: int
    expected_club_id: int
    expected_platform: str
    expected_scraper_key: str
    new_platform: str
    rationale: str


_REPOINT_TARGETS: list[RepointTarget] = [
    RepointTarget(
        source_id=286,
        expected_club_id=463,
        expected_platform="ticketweb",
        expected_scraper_key="ticketweb",
        old_source_url="https://www.thestandupclub.com/calendar/",
        new_source_url="https://www.thestandupclub.com/",
        rationale=(
            "The Stand Up Comedy Club. Venue moved their TicketWeb "
            "tw-plugin-upcoming-event-list widget from /calendar/ (now 404) "
            "to the homepage /. Verified live on 2026-05-06: '/' returns 15 "
            "future shows that the existing HTML fallback path parses cleanly "
            "(JS var all_events path absent on both URLs). Repoint restores "
            "coverage with no code change."
        ),
    ),
]


_DISABLE_TARGETS: list[DisableTarget] = [
    DisableTarget(
        source_id=313,
        expected_club_id=485,
        expected_platform="ticketweb",
        expected_scraper_key="ticketweb",
        new_platform="punchup",
        rationale=(
            "LAUGH IT UP COMEDY CLUB. Venue migrated from TicketWeb (WordPress "
            "tw-plugin) to Punchup (Next.js + Supabase). Verified live on "
            "2026-05-06: laughitupcomedy.com/calendar SSR HTML has zero "
            "ticketweb / tw-plugin / all_events markers; footer reads 'Powered "
            "by Punchup' and the runtime backend is "
            "xudgmlzkdlowirdrfhmw.supabase.co. Calendar renders 3 May shows "
            "(Laughing Stock 5/8, Freddy Rubino 5/15, Zen and Friends 5/29) "
            "via Punchup's React Query hydration — the TicketWeb scraper "
            "cannot recover events from the new platform. Punchup is already "
            "supported via PunchupExtractor (comedy_key_west, west_side, "
            "newport_comedy_series venue scrapers); follow-up task tracks "
            "adoption. Note: ss=822 (SeatEngine ext=461) was disabled by "
            "TASK-1950 as fallback_redundant when ticketweb was producing "
            "shows; that premise is now stale and SE re-enablement is an "
            "alternative captured in the follow-up."
        ),
    ),
]


def _load_metadata(raw) -> dict:
    if isinstance(raw, str):
        return json.loads(raw)
    if raw is None:
        return {}
    return dict(raw)


def _validate_shape(
    rows: dict,
    repoints: list[RepointTarget],
    disables: list[DisableTarget],
) -> list[str]:
    """Collect (do not raise) every shape mismatch found across all targets."""
    problems: list[str] = []
    expected_ids = [t.source_id for t in repoints] + [t.source_id for t in disables]
    missing = [sid for sid in expected_ids if sid not in rows]
    if missing:
        problems.append(f"missing scraping_sources rows: {missing}")

    for t in repoints:
        row = rows.get(t.source_id)
        if row is None:
            continue
        _, club_id, platform, scraper_key, _, source_url, priority, _, _ = row
        if club_id != t.expected_club_id:
            problems.append(
                f"ss.id={t.source_id}: club_id={club_id} (expected {t.expected_club_id})"
            )
        if platform != t.expected_platform:
            problems.append(
                f"ss.id={t.source_id}: platform={platform!r} (expected {t.expected_platform!r})"
            )
        if scraper_key != t.expected_scraper_key:
            problems.append(
                f"ss.id={t.source_id}: scraper_key={scraper_key!r} "
                f"(expected {t.expected_scraper_key!r})"
            )
        if priority != 0:
            problems.append(
                f"ss.id={t.source_id}: priority={priority} (expected 0)"
            )
        if source_url not in (t.old_source_url, t.new_source_url):
            problems.append(
                f"ss.id={t.source_id}: source_url={source_url!r} "
                f"(expected {t.old_source_url!r} or {t.new_source_url!r})"
            )

    for t in disables:
        row = rows.get(t.source_id)
        if row is None:
            continue
        _, club_id, platform, scraper_key, _, _, priority, _, _ = row
        if club_id != t.expected_club_id:
            problems.append(
                f"ss.id={t.source_id}: club_id={club_id} (expected {t.expected_club_id})"
            )
        if platform != t.expected_platform:
            problems.append(
                f"ss.id={t.source_id}: platform={platform!r} (expected {t.expected_platform!r})"
            )
        if scraper_key != t.expected_scraper_key:
            problems.append(
                f"ss.id={t.source_id}: scraper_key={scraper_key!r} "
                f"(expected {t.expected_scraper_key!r})"
            )
        if priority != 0:
            problems.append(
                f"ss.id={t.source_id}: priority={priority} (expected 0)"
            )
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Disposition the 2 TicketWeb venues that returned 0 events in the "
            "2026-05-05 nightly. Repoints ss=286 (Stand Up Comedy Club) "
            "source_url to / (widget moved homepage) and disables ss=313 "
            "(LAUGH IT UP) which migrated to Punchup. See module docstring."
        )
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()

    target_ids = (
        [t.source_id for t in _REPOINT_TARGETS]
        + [t.source_id for t in _DISABLE_TARGETS]
    )

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

        problems = _validate_shape(rows, _REPOINT_TARGETS, _DISABLE_TARGETS)
        if problems:
            print("ABORT: shape mismatch — refusing to write:", file=sys.stderr)
            for p in problems:
                print(f"  {p}", file=sys.stderr)
            return 1

        print("=== BEFORE ===")
        for sid in target_ids:
            _, cid, plat, _sk, _ext, src_url, pri, en, _ = rows[sid]
            print(
                f"  ss.id={sid:>4} club={cid:>4} {plat:<14} pri={pri} "
                f"enabled={en} url={src_url!r}"
            )

        writes_planned = 0

        if args.dry_run:
            print("\n--dry-run: planning writes, no DB changes...")

        with conn.cursor() as cur:
            for t in _REPOINT_TARGETS:
                row = rows[t.source_id]
                _, _, _, _, _, source_url, _, _, meta_raw = row
                meta = _load_metadata(meta_raw)
                needs_repoint = source_url != t.new_source_url
                needs_meta = _METADATA_KEY not in meta
                if not (needs_repoint or needs_meta):
                    continue

                new_meta = dict(meta)
                new_meta[_METADATA_KEY] = {
                    "kind": "source_url_relocated",
                    "old_source_url": t.old_source_url,
                    "new_source_url": t.new_source_url,
                    "rationale": t.rationale,
                }
                action = "PLAN " if args.dry_run else "WRITE"
                print(
                    f"  {action} ss={t.source_id} (club {t.expected_club_id}): "
                    f"source_url={source_url!r}→{t.new_source_url!r} + "
                    f"metadata[{_METADATA_KEY}]='source_url_relocated'"
                )
                if not args.dry_run:
                    cur.execute(
                        """
                        UPDATE scraping_sources
                        SET source_url = %s,
                            metadata = %s,
                            updated_at = NOW()
                        WHERE id = %s
                        """,
                        (t.new_source_url, json.dumps(new_meta), t.source_id),
                    )
                writes_planned += 1

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
                    "kind": "platform_migration",
                    "from_platform": t.expected_platform,
                    "to_platform": t.new_platform,
                    "rationale": t.rationale,
                }
                action = "PLAN " if args.dry_run else "WRITE"
                print(
                    f"  {action} ss={t.source_id} (club {t.expected_club_id}): "
                    f"enabled={enabled}→FALSE + metadata[{_METADATA_KEY}]="
                    f"'platform_migration' (ticketweb→punchup)"
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
                SELECT id, club_id, platform::text, source_url, enabled
                FROM scraping_sources
                WHERE id = ANY(%s)
                ORDER BY id
                """,
                (target_ids,),
            )
            for sid, cid, plat, src_url, en in cur.fetchall():
                print(
                    f"  ss.id={sid:>4} club={cid:>4} {plat:<14} enabled={en} "
                    f"url={src_url!r}"
                )

    return 0


if __name__ == "__main__":
    sys.exit(main())
