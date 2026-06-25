#!/usr/bin/env python3
"""
Fold the duplicate national-chain Comedy Zone club rows created by a bulk
ticketmaster import (TASK-3457).

Background
----------
TASK-3321 (Funny Bone fold) confirmed the national-chain bulk-import
duplicate pattern extends to Comedy Zone: an older established
"<City> Comedy Zone" row scraped via `seatengine` (the venue's own
ticketing) carrying hundreds of shows, duplicated by a newer
"Comedy Zone - <City>" row (9xxx id) created by a ticketmaster
national-chain bulk import that re-added the chain without deduping
against the existing rows. The duplicate club shell splits
shows/attribution and produces duplicate UI cards.

This folds each ticketmaster duplicate into its established seatengine
canonical, following the audited-fold pattern from TASK-3150
(scripts/core/fold_audited_duplicate_clubs_2026_06_21.py) and TASK-3321
(scripts/core/fold_funny_bone_national_chain_dups_2026_06_25.py), and the
closed-name convention from the Stifel Theatre fold.

Confirmed pairs (canonical <- duplicate), measured 2026-06-25:

  * 73 Greenville Comedy Zone    <- 9435 Comedy Zone - Greenville (Greenville, SC)
  * 59 Jacksonville Comedy Zone  <- 9866 Comedy Zone - Jacksonville (Jacksonville, FL)

(Charlotte 58 vs 2879 'The Comedy Zone' is a separate case — 2879 is
already hidden with 0 shows on a tour_dates stub — and is out of scope.
Helium Atlanta 134/4734 is tracked by TASK-3381.)

What this script does
---------------------
1. Validates the expected name of each canonical and duplicate row
   (FOR UPDATE lock); refuses to write on any mismatch.
2. Registers a club_aliases row routing the duplicate's "Comedy Zone -
   <City>" name (+ city/state) to the canonical id, so a future
   ticketmaster bulk import re-resolves to canonical instead of
   re-inserting.
3. Moves the duplicate's scraping_sources to the canonical club, DISABLED
   (the canonical's own seatengine source already covers the venue; the
   moved ticketmaster source becomes a disabled fallback, never orphaned).
4. Re-points the duplicate's shows: shows colliding on (date, room) with an
   existing canonical show are deduped (lineup_items / tagged_shows / tickets
   copied to the surviving canonical show, click-events + notifications
   repointed, then the duplicate show deleted); non-colliding shows are moved
   to canonical.
5. Moves user-facing club references (favorite_clubs, email_subscriptions,
   processed_emails, tagged_clubs, production_company_venues,
   club_image_assets, scraper_run_clubs) to canonical, deduping conflicts.
6. Closes each duplicate club: renames to
   "<dup name> (duplicate of club <canonical>; folded from club <dup>)",
   visible=FALSE, status='closed', closed_at=NOW().
7. Recomputes clubs.total_shows for every touched club.
8. Writes a recovery log to docs/audits/task-3457-comedy-zone-dup-folds.json.

Idempotent: aliases upsert, source moves only affect rows still on the
duplicate, show map only matches shows still on the duplicate, and closed
rows already carrying the closed-name are matched by it. Safe to re-run.

Usage
-----
    cd apps/scraper
    make run-script SCRIPT=scripts/core/fold_comedy_zone_national_chain_dups_2026_06_25.py ARGS='--dry-run'
    make run-script SCRIPT=scripts/core/fold_comedy_zone_national_chain_dups_2026_06_25.py
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor, execute_values

load_dotenv(_root / ".env")

from laughtrack.adapters.db import get_transaction


TASK_ID = 3457
ALIAS_SOURCE = "TASK-3457"
RECOVERY_LOG_PATH = _root / "docs" / "audits" / "task-3457-comedy-zone-dup-folds.json"


@dataclass(frozen=True)
class FoldSpec:
    canonical_id: int
    duplicate_id: int
    canonical_name: str
    duplicate_name: str
    city: str
    state: str

    @property
    def closed_name(self) -> str:
        return (
            f"{self.duplicate_name} (duplicate of club {self.canonical_id}; "
            f"folded from club {self.duplicate_id})"
        )

    @property
    def alias_name(self) -> str:
        # Route the bulk-import name back to the canonical row.
        return self.duplicate_name


FOLDS: tuple[FoldSpec, ...] = (
    FoldSpec(73, 9435, "Greenville Comedy Zone", "Comedy Zone - Greenville", "Greenville", "SC"),
    FoldSpec(59, 9866, "Jacksonville Comedy Zone", "Comedy Zone - Jacksonville", "Jacksonville", "FL"),
)


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _fetch_one(cur: RealDictCursor, sql: str, params: tuple = ()) -> dict[str, Any] | None:
    cur.execute(sql, params)
    row = cur.fetchone()
    return dict(row) if row else None


def _fetch_all(cur: RealDictCursor, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    cur.execute(sql, params)
    return [dict(row) for row in cur.fetchall()]


def _club_ids() -> tuple[int, ...]:
    ids: set[int] = set()
    for fold in FOLDS:
        ids.add(fold.canonical_id)
        ids.add(fold.duplicate_id)
    return tuple(sorted(ids))


def _validate(cur: RealDictCursor) -> dict[str, Any]:
    problems: list[str] = []
    rows = _fetch_all(
        cur,
        """
        SELECT id, name, city, state, visible, status, total_shows
        FROM clubs
        WHERE id = ANY(%s)
        FOR UPDATE
        """,
        (list(_club_ids()),),
    )
    clubs_by_id = {row["id"]: row for row in rows}
    for fold in FOLDS:
        canonical = clubs_by_id.get(fold.canonical_id)
        duplicate = clubs_by_id.get(fold.duplicate_id)
        if canonical is None:
            problems.append(f"canonical club {fold.canonical_id} not found")
        elif canonical["name"] != fold.canonical_name:
            problems.append(
                f"club {fold.canonical_id} name is {canonical['name']!r}, expected {fold.canonical_name!r}"
            )
        if duplicate is None:
            problems.append(f"duplicate club {fold.duplicate_id} not found")
        elif duplicate["name"] not in {fold.duplicate_name, fold.closed_name}:
            problems.append(
                f"club {fold.duplicate_id} name is {duplicate['name']!r}, expected {fold.duplicate_name!r}"
            )
    if problems:
        raise RuntimeError("; ".join(problems))
    return {"clubs": rows}


def _snapshot(cur: RealDictCursor) -> dict[str, Any]:
    ids = list(_club_ids())
    duplicate_ids = [fold.duplicate_id for fold in FOLDS]
    return {
        "clubs": _fetch_all(
            cur,
            """
            SELECT id, name, city, state, visible, status, closed_at, total_shows
            FROM clubs
            WHERE id = ANY(%s)
            ORDER BY id
            """,
            (ids,),
        ),
        "sources": _fetch_all(
            cur,
            """
            SELECT id, club_id, platform, scraper_key, ticketmaster_id,
                   source_url, priority, enabled, metadata
            FROM scraping_sources
            WHERE club_id = ANY(%s)
            ORDER BY club_id, priority, id
            """,
            (ids,),
        ),
        "aliases": _fetch_all(
            cur,
            """
            SELECT id, club_id, alias_name, normalized_alias_name, city, state,
                   normalized_city, normalized_state, source, verified
            FROM club_aliases
            WHERE source = %s
               OR club_id = ANY(%s)
            ORDER BY club_id, id
            """,
            (ALIAS_SOURCE, ids),
        ),
        "duplicate_show_summary": _fetch_all(
            cur,
            """
            SELECT club_id, COUNT(*) AS show_count, MIN(date) AS first_show, MAX(date) AS last_show
            FROM shows
            WHERE club_id = ANY(%s)
            GROUP BY club_id
            ORDER BY club_id
            """,
            (duplicate_ids,),
        ),
        "remaining_duplicate_references": _fetch_one(
            cur,
            """
            SELECT
                (SELECT COUNT(*) FROM shows WHERE club_id = ANY(%s)) AS shows,
                (SELECT COUNT(*) FROM scraping_sources WHERE club_id = ANY(%s)) AS scraping_sources,
                (SELECT COUNT(*) FROM ticket_purchase_click_events WHERE club_id = ANY(%s)) AS click_events,
                (SELECT COUNT(*) FROM favorite_clubs WHERE club_id = ANY(%s)) AS favorite_clubs,
                (SELECT COUNT(*) FROM email_subscriptions WHERE club_id = ANY(%s)) AS email_subscriptions,
                (SELECT COUNT(*) FROM tagged_clubs WHERE club_id = ANY(%s)) AS tagged_clubs,
                (SELECT COUNT(*) FROM production_company_venues WHERE club_id = ANY(%s)) AS production_company_venues,
                (SELECT COUNT(*) FROM processed_emails WHERE club_id = ANY(%s)) AS processed_emails,
                (SELECT COUNT(*) FROM club_image_assets WHERE club_id = ANY(%s)) AS club_image_assets,
                (SELECT COUNT(*) FROM scraper_run_clubs WHERE club_id = ANY(%s)) AS scraper_run_clubs
            """,
            (duplicate_ids,) * 10,
        ),
    }


def _create_temp_tables(cur: RealDictCursor) -> None:
    cur.execute(
        """
        CREATE TEMP TABLE task_3457_folds (
            new_id INTEGER NOT NULL,
            old_id INTEGER NOT NULL,
            old_name TEXT NOT NULL,
            closed_name TEXT NOT NULL,
            alias_name TEXT NOT NULL,
            city TEXT NOT NULL,
            state TEXT NOT NULL
        ) ON COMMIT DROP
        """
    )
    execute_values(
        cur,
        """
        INSERT INTO task_3457_folds (
            new_id, old_id, old_name, closed_name, alias_name, city, state
        )
        VALUES %s
        """,
        [
            (
                fold.canonical_id,
                fold.duplicate_id,
                fold.duplicate_name,
                fold.closed_name,
                fold.alias_name,
                fold.city,
                fold.state,
            )
            for fold in FOLDS
        ],
    )

    cur.execute(
        """
        CREATE TEMP TABLE task_3457_duplicate_show_map AS
        SELECT
            old_show.id AS old_show_id,
            new_show.id AS new_show_id,
            f.new_id AS canonical_club_id,
            f.old_id AS old_club_id,
            old_show.date,
            old_show.room
        FROM task_3457_folds f
        JOIN shows old_show ON old_show.club_id = f.old_id
        LEFT JOIN shows new_show
          ON new_show.club_id = f.new_id
         AND new_show.date = old_show.date
         AND new_show.room IS NOT DISTINCT FROM old_show.room
        """
    )


def _ensure_future_routing(cur: RealDictCursor) -> dict[str, int]:
    counts: dict[str, int] = {}
    cur.execute(
        """
        INSERT INTO club_aliases (
            club_id,
            alias_name,
            normalized_alias_name,
            city,
            state,
            normalized_city,
            normalized_state,
            source,
            verified,
            created_at,
            updated_at
        )
        SELECT
            f.new_id,
            f.alias_name,
            btrim(regexp_replace(replace(lower(f.alias_name), '&', ' and '), '[^a-z0-9]+', ' ', 'g')),
            f.city,
            f.state,
            btrim(regexp_replace(lower(f.city), '[^a-z0-9]+', ' ', 'g')),
            lower(f.state),
            %s,
            TRUE,
            NOW(),
            NOW()
        FROM task_3457_folds f
        ON CONFLICT (normalized_alias_name, normalized_city, normalized_state)
        DO UPDATE SET
            club_id = EXCLUDED.club_id,
            alias_name = EXCLUDED.alias_name,
            city = EXCLUDED.city,
            state = EXCLUDED.state,
            source = EXCLUDED.source,
            verified = TRUE,
            updated_at = NOW()
        """,
        (ALIAS_SOURCE,),
    )
    counts["aliases_upserted"] = cur.rowcount

    cur.execute(
        """
        WITH duplicate_sources AS (
            SELECT
                ss.id,
                ss.platform,
                f.new_id,
                f.old_id,
                ROW_NUMBER() OVER (
                    PARTITION BY f.new_id, ss.platform
                    ORDER BY ss.priority, ss.id
                ) AS duplicate_rank,
                COALESCE((
                    SELECT MAX(existing.priority)
                    FROM scraping_sources existing
                    WHERE existing.club_id = f.new_id
                      AND existing.platform = ss.platform
                      AND existing.id <> ss.id
                ), -1) AS max_existing_priority
            FROM scraping_sources ss
            JOIN task_3457_folds f ON f.old_id = ss.club_id
        ),
        assigned_sources AS (
            SELECT
                id,
                new_id,
                old_id,
                max_existing_priority + duplicate_rank AS new_priority
            FROM duplicate_sources
        )
        UPDATE scraping_sources ss
        SET club_id = a.new_id,
            priority = a.new_priority,
            enabled = false,
            metadata = COALESCE(ss.metadata, '{}'::jsonb)
                || jsonb_build_object(
                    'task_3457_disposition',
                    'moved disabled duplicate source from club ' || a.old_id || ' to club ' || a.new_id
                ),
            updated_at = NOW()
        FROM assigned_sources a
        WHERE ss.id = a.id
        """
    )
    counts["duplicate_sources_moved_to_canonical"] = cur.rowcount

    cur.execute(
        """
        UPDATE scraping_sources ss
        SET enabled = false,
            metadata = COALESCE(ss.metadata, '{}'::jsonb)
                || jsonb_build_object(
                    'task_3457_disposition',
                    'disabled source remaining on duplicate club ' || f.old_id || ' after fold into club ' || f.new_id
                ),
            updated_at = NOW()
        FROM task_3457_folds f
        WHERE ss.club_id = f.old_id
        """
    )
    counts["remaining_duplicate_sources_disabled"] = cur.rowcount
    return counts


def _apply_show_updates(cur: RealDictCursor) -> dict[str, int]:
    counts: dict[str, int] = {}

    cur.execute(
        """
        INSERT INTO lineup_items (show_id, comedian_id, role)
        SELECT m.new_show_id, li.comedian_id, li.role
        FROM lineup_items li
        JOIN task_3457_duplicate_show_map m ON m.old_show_id = li.show_id
        WHERE m.new_show_id IS NOT NULL
        ON CONFLICT (show_id, comedian_id) DO NOTHING
        """
    )
    counts["lineup_items_copied"] = cur.rowcount

    cur.execute(
        """
        INSERT INTO tagged_shows (show_id, tag_id)
        SELECT m.new_show_id, ts.tag_id
        FROM tagged_shows ts
        JOIN task_3457_duplicate_show_map m ON m.old_show_id = ts.show_id
        WHERE m.new_show_id IS NOT NULL
        ON CONFLICT (show_id, tag_id) DO NOTHING
        """
    )
    counts["tagged_shows_copied"] = cur.rowcount

    cur.execute(
        """
        INSERT INTO tickets (purchase_url, price, sold_out, show_id, type)
        SELECT t.purchase_url, t.price, t.sold_out, m.new_show_id, t.type
        FROM tickets t
        JOIN task_3457_duplicate_show_map m ON m.old_show_id = t.show_id
        WHERE m.new_show_id IS NOT NULL
        ON CONFLICT (show_id, type) DO NOTHING
        """
    )
    counts["tickets_copied"] = cur.rowcount

    cur.execute(
        """
        DELETE FROM sent_notifications sn
        USING task_3457_duplicate_show_map m,
              sent_notifications existing
        WHERE m.new_show_id IS NOT NULL
          AND sn.show_id = m.old_show_id
          AND existing.user_id = sn.user_id
          AND existing.comedian_id = sn.comedian_id
          AND existing.show_id = m.new_show_id
          AND existing.notification_type = sn.notification_type
        """
    )
    counts["conflicting_sent_notifications_deleted"] = cur.rowcount

    cur.execute(
        """
        UPDATE sent_notifications sn
        SET show_id = m.new_show_id
        FROM task_3457_duplicate_show_map m
        WHERE m.new_show_id IS NOT NULL
          AND sn.show_id = m.old_show_id
        """
    )
    counts["sent_notifications_repointed"] = cur.rowcount

    cur.execute(
        """
        UPDATE ticket_purchase_click_events tpce
        SET show_id = m.new_show_id,
            club_id = m.canonical_club_id
        FROM task_3457_duplicate_show_map m
        WHERE m.new_show_id IS NOT NULL
          AND tpce.show_id = m.old_show_id
        """
    )
    counts["click_events_repointed_to_existing_show"] = cur.rowcount

    cur.execute(
        """
        DELETE FROM shows s
        USING task_3457_duplicate_show_map m
        WHERE s.id = m.old_show_id
          AND m.new_show_id IS NOT NULL
        """
    )
    counts["colliding_duplicate_shows_deleted"] = cur.rowcount

    cur.execute(
        """
        UPDATE shows s
        SET club_id = m.canonical_club_id
        FROM task_3457_duplicate_show_map m
        WHERE s.id = m.old_show_id
          AND m.new_show_id IS NULL
        """
    )
    counts["noncolliding_shows_moved"] = cur.rowcount

    cur.execute(
        """
        UPDATE ticket_purchase_click_events tpce
        SET club_id = f.new_id
        FROM task_3457_folds f
        WHERE tpce.club_id = f.old_id
        """
    )
    counts["click_events_club_repointed"] = cur.rowcount
    return counts


def _apply_club_reference_updates(cur: RealDictCursor) -> dict[str, int]:
    counts: dict[str, int] = {}

    cur.execute(
        """
        INSERT INTO favorite_clubs (profile_id, club_id)
        SELECT fc.profile_id, f.new_id
        FROM favorite_clubs fc
        JOIN task_3457_folds f ON f.old_id = fc.club_id
        ON CONFLICT (profile_id, club_id) DO NOTHING
        """
    )
    counts["favorite_clubs_inserted"] = cur.rowcount

    cur.execute(
        """
        DELETE FROM favorite_clubs fc
        USING task_3457_folds f
        WHERE fc.club_id = f.old_id
        """
    )
    counts["duplicate_favorite_clubs_deleted"] = cur.rowcount

    cur.execute(
        """
        INSERT INTO production_company_venues (production_company_id, club_id)
        SELECT pcv.production_company_id, f.new_id
        FROM production_company_venues pcv
        JOIN task_3457_folds f ON f.old_id = pcv.club_id
        ON CONFLICT (production_company_id, club_id) DO NOTHING
        """
    )
    counts["production_company_venues_inserted"] = cur.rowcount

    cur.execute(
        """
        DELETE FROM production_company_venues pcv
        USING task_3457_folds f
        WHERE pcv.club_id = f.old_id
        """
    )
    counts["duplicate_production_company_venues_deleted"] = cur.rowcount

    cur.execute(
        """
        INSERT INTO tagged_clubs (club_id, tag_id)
        SELECT f.new_id, tc.tag_id
        FROM tagged_clubs tc
        JOIN task_3457_folds f ON f.old_id = tc.club_id
        WHERE NOT EXISTS (
            SELECT 1
            FROM tagged_clubs existing
            WHERE existing.club_id = f.new_id
              AND existing.tag_id = tc.tag_id
        )
        """
    )
    counts["tagged_clubs_inserted"] = cur.rowcount

    cur.execute(
        """
        DELETE FROM tagged_clubs tc
        USING task_3457_folds f
        WHERE tc.club_id = f.old_id
        """
    )
    counts["duplicate_tagged_clubs_deleted"] = cur.rowcount

    cur.execute(
        """
        DELETE FROM email_subscriptions es
        USING task_3457_folds f, email_subscriptions existing
        WHERE es.club_id = f.old_id
          AND existing.club_id = f.new_id
        """
    )
    counts["conflicting_email_subscriptions_deleted"] = cur.rowcount

    cur.execute(
        """
        UPDATE email_subscriptions es
        SET club_id = f.new_id
        FROM task_3457_folds f
        WHERE es.club_id = f.old_id
        """
    )
    counts["email_subscriptions_moved"] = cur.rowcount

    cur.execute(
        """
        UPDATE processed_emails pe
        SET club_id = f.new_id
        FROM task_3457_folds f
        WHERE pe.club_id = f.old_id
        """
    )
    counts["processed_emails_moved"] = cur.rowcount

    cur.execute(
        """
        UPDATE club_image_assets cia
        SET club_id = f.new_id
        FROM task_3457_folds f
        WHERE cia.club_id = f.old_id
          AND NOT (cia.is_active AND EXISTS (
              SELECT 1
              FROM club_image_assets existing
              WHERE existing.club_id = f.new_id
                AND existing.is_active
          ))
        """
    )
    counts["club_image_assets_moved"] = cur.rowcount

    cur.execute(
        """
        UPDATE club_image_assets cia
        SET is_active = false
        FROM task_3457_folds f
        WHERE cia.club_id = f.old_id
          AND cia.is_active
        """
    )
    counts["duplicate_active_club_images_deactivated"] = cur.rowcount

    cur.execute(
        """
        UPDATE scraper_run_clubs src
        SET club_id = f.new_id
        FROM task_3457_folds f
        WHERE src.club_id = f.old_id
        """
    )
    counts["scraper_run_clubs_moved"] = cur.rowcount
    return counts


def _close_duplicate_clubs(cur: RealDictCursor) -> dict[str, int]:
    counts: dict[str, int] = {}
    cur.execute(
        """
        UPDATE clubs c
        SET name = f.closed_name,
            visible = false,
            status = 'closed',
            closed_at = COALESCE(c.closed_at, NOW())
        FROM task_3457_folds f
        WHERE c.id = f.old_id
        """
    )
    counts["duplicate_clubs_closed"] = cur.rowcount

    cur.execute(
        """
        UPDATE clubs
        SET total_shows = (SELECT COUNT(*) FROM shows WHERE shows.club_id = clubs.id)
        WHERE id IN (
            SELECT new_id FROM task_3457_folds
            UNION
            SELECT old_id FROM task_3457_folds
        )
        """
    )
    counts["club_totals_recomputed"] = cur.rowcount
    return counts


def _apply(cur: RealDictCursor) -> dict[str, int]:
    counts: dict[str, int] = {}
    _create_temp_tables(cur)
    counts.update(_ensure_future_routing(cur))
    counts.update(_apply_show_updates(cur))
    counts.update(_apply_club_reference_updates(cur))
    counts.update(_close_duplicate_clubs(cur))
    return counts


def run(dry_run: bool) -> dict[str, Any]:
    log: dict[str, Any] = {
        "task_id": TASK_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "folds": [
            {
                "canonical_id": fold.canonical_id,
                "duplicate_id": fold.duplicate_id,
                "canonical_name": fold.canonical_name,
                "duplicate_name": fold.duplicate_name,
                "city": fold.city,
                "state": fold.state,
            }
            for fold in FOLDS
        ],
    }
    with get_transaction() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            log["validated"] = _validate(cur)
            log["before"] = _snapshot(cur)
            log["counts"] = _apply(cur)
            log["after"] = _snapshot(cur)
            if dry_run:
                conn.rollback()
            else:
                RECOVERY_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
                RECOVERY_LOG_PATH.write_text(
                    json.dumps(log, indent=2, sort_keys=True, default=_json_default) + "\n",
                    encoding="utf-8",
                )
    return log


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fold duplicate national-chain Comedy Zone club rows (TASK-3457)."
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()

    log = run(dry_run=args.dry_run)
    print(json.dumps(log, indent=2, sort_keys=True, default=_json_default))
    if args.dry_run:
        print("DRY RUN: no database rows were changed and no recovery log was written.")
    else:
        print(f"Wrote recovery log: {RECOVERY_LOG_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
