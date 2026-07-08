#!/usr/bin/env python3
"""
Fold duplicate club records audited in TASK-3045 through TASK-3049.

This applies the safe plans recorded by the five no-code duplicate club audits:

  * 4841 -> 4497  V Theater
  * 4616 -> 4597  Saxe Theater
  * 6796 -> 1039  Punch Line Sacramento, with one show mapped to Callback Bar 4564
  * 6802 -> 173   Laugh Factory Reno
  * 6779 -> 198   Punch Line Houston

Usage:
    cd apps/scraper
    make run-script SCRIPT=scripts/core/fold_audited_duplicate_clubs_2026_06_21.py ARGS='--dry-run'
    make run-script SCRIPT=scripts/core/fold_audited_duplicate_clubs_2026_06_21.py
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
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


TASK_ID = 3150
ALIAS_SOURCE = "TASK-3150"
RECOVERY_LOG_PATH = _root / "docs" / "audits" / "task-3150-audited-duplicate-club-folds.json"


@dataclass(frozen=True)
class FoldSpec:
    task_ref: str
    canonical_id: int
    duplicate_id: int
    canonical_name: str
    duplicate_name: str
    city: str
    state: str
    aliases: tuple[str, ...]
    alternate_target_club_ids: tuple[int, ...] = field(default_factory=tuple)

    @property
    def closed_name(self) -> str:
        return f"{self.duplicate_name} (duplicate of club {self.canonical_id}; folded from club {self.duplicate_id})"


FOLDS: tuple[FoldSpec, ...] = (
    FoldSpec(
        task_ref="TASK-3045",
        canonical_id=4497,
        duplicate_id=4841,
        canonical_name="V Theater at Planet Hollywood Inside the Miracle Mile Mall",
        duplicate_name="V theater at Planet Hollywood Las Vegas",
        city="Las Vegas",
        state="NV",
        aliases=(
            "V theater at Planet Hollywood Las Vegas",
            "V Theater - Planet Hollywood Resort & Casino",
        ),
    ),
    FoldSpec(
        task_ref="TASK-3046",
        canonical_id=4597,
        duplicate_id=4616,
        canonical_name="Saxe Theater at Planet Hollywood Inside the Miracle Mile Mall",
        duplicate_name="Planet Hollywood-Saxe Theater",
        city="Las Vegas",
        state="NV",
        aliases=(
            "Planet Hollywood-Saxe Theater",
            "Saxe Theater - Planet Hollywood Resort & Casino",
        ),
    ),
    FoldSpec(
        task_ref="TASK-3047",
        canonical_id=1039,
        duplicate_id=6796,
        canonical_name="Punch Line Sacramento",
        duplicate_name="Punch Line Comedy Club - Sacramento",
        city="Sacramento",
        state="CA",
        aliases=("Punch Line Comedy Club - Sacramento",),
        alternate_target_club_ids=(4564,),
    ),
    FoldSpec(
        task_ref="TASK-3048",
        canonical_id=173,
        duplicate_id=6802,
        canonical_name="Laugh Factory Reno",
        duplicate_name="Laugh Factory at the Silver Legacy Casino",
        city="Reno",
        state="NV",
        aliases=(
            "Laugh Factory at the Silver Legacy Casino",
            "Laugh Factory at Silver Legacy Casino",
        ),
    ),
    FoldSpec(
        task_ref="TASK-3049",
        canonical_id=198,
        duplicate_id=6779,
        canonical_name="Punch Line Comedy Club Houston",
        duplicate_name="Punch Line Houston",
        city="Houston",
        state="TX",
        aliases=("Punch Line Houston",),
    ),
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
        ids.update(fold.alternate_target_club_ids)
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
                (SELECT COUNT(*) FROM ticket_purchase_click_events WHERE club_id = ANY(%s)) AS click_events,
                (SELECT COUNT(*) FROM favorite_clubs WHERE club_id = ANY(%s)) AS favorite_clubs,
                (SELECT COUNT(*) FROM email_subscriptions WHERE club_id = ANY(%s)) AS email_subscriptions,
                (SELECT COUNT(*) FROM tagged_clubs WHERE club_id = ANY(%s)) AS tagged_clubs,
                (SELECT COUNT(*) FROM production_company_venues WHERE club_id = ANY(%s)) AS production_company_venues,
                (SELECT COUNT(*) FROM processed_emails WHERE club_id = ANY(%s)) AS processed_emails,
                (SELECT COUNT(*) FROM club_image_assets WHERE club_id = ANY(%s)) AS club_image_assets,
                (SELECT COUNT(*) FROM scraper_run_clubs WHERE club_id = ANY(%s)) AS scraper_run_clubs
            """,
            (duplicate_ids, duplicate_ids, duplicate_ids, duplicate_ids, duplicate_ids, duplicate_ids, duplicate_ids, duplicate_ids, duplicate_ids),
        ),
    }


def _create_temp_tables(cur: RealDictCursor) -> None:
    cur.execute(
        """
        CREATE TEMP TABLE task_3150_folds (
            task_ref TEXT NOT NULL,
            new_id INTEGER NOT NULL,
            old_id INTEGER NOT NULL,
            old_name TEXT NOT NULL,
            closed_name TEXT NOT NULL,
            city TEXT NOT NULL,
            state TEXT NOT NULL
        ) ON COMMIT DROP
        """
    )
    execute_values(
        cur,
        """
        INSERT INTO task_3150_folds (
            task_ref, new_id, old_id, old_name, closed_name, city, state
        )
        VALUES %s
        """,
        [
            (
                fold.task_ref,
                fold.canonical_id,
                fold.duplicate_id,
                fold.duplicate_name,
                fold.closed_name,
                fold.city,
                fold.state,
            )
            for fold in FOLDS
        ],
    )

    cur.execute(
        """
        CREATE TEMP TABLE task_3150_aliases (
            new_id INTEGER NOT NULL,
            alias_name TEXT NOT NULL,
            city TEXT NOT NULL,
            state TEXT NOT NULL
        ) ON COMMIT DROP
        """
    )
    execute_values(
        cur,
        "INSERT INTO task_3150_aliases (new_id, alias_name, city, state) VALUES %s",
        [
            (fold.canonical_id, alias_name, fold.city, fold.state)
            for fold in FOLDS
            for alias_name in fold.aliases
        ],
    )

    cur.execute(
        """
        CREATE TEMP TABLE task_3150_alternate_target_clubs (
            old_id INTEGER NOT NULL,
            target_id INTEGER NOT NULL
        ) ON COMMIT DROP
        """
    )
    alternate_targets = [
        (fold.duplicate_id, target_id)
        for fold in FOLDS
        for target_id in fold.alternate_target_club_ids
    ]
    if alternate_targets:
        execute_values(
            cur,
            "INSERT INTO task_3150_alternate_target_clubs (old_id, target_id) VALUES %s",
            alternate_targets,
        )

    cur.execute(
        """
        CREATE TEMP TABLE task_3150_duplicate_show_map AS
        SELECT
            old_show.id AS old_show_id,
            COALESCE(new_show.id, alternate_show.id) AS new_show_id,
            COALESCE(new_show.club_id, alternate_show.club_id, f.new_id) AS target_club_id,
            f.old_id AS old_club_id,
            f.new_id AS canonical_club_id,
            old_show.date,
            old_show.room,
            old_show.show_page_url
        FROM task_3150_folds f
        JOIN shows old_show ON old_show.club_id = f.old_id
        LEFT JOIN shows new_show
          ON new_show.club_id = f.new_id
         AND new_show.date = old_show.date
         AND new_show.room IS NOT DISTINCT FROM old_show.room
        LEFT JOIN LATERAL (
            SELECT target_show.id, target_show.club_id
            FROM task_3150_alternate_target_clubs alt
            JOIN shows target_show ON target_show.club_id = alt.target_id
            WHERE alt.old_id = f.old_id
              AND target_show.date = old_show.date
              AND target_show.room IS NOT DISTINCT FROM old_show.room
              AND target_show.show_page_url = old_show.show_page_url
            ORDER BY target_show.id
            LIMIT 1
        ) alternate_show ON new_show.id IS NULL
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
            a.new_id,
            a.alias_name,
            btrim(regexp_replace(replace(lower(a.alias_name), '&', ' and '), '[^a-z0-9]+', ' ', 'g')),
            a.city,
            a.state,
            btrim(regexp_replace(lower(a.city), '[^a-z0-9]+', ' ', 'g')),
            lower(a.state),
            %s,
            TRUE,
            NOW(),
            NOW()
        FROM task_3150_aliases a
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
                f.task_ref,
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
            JOIN task_3150_folds f ON f.old_id = ss.club_id
        ),
        assigned_sources AS (
            SELECT
                id,
                new_id,
                old_id,
                task_ref,
                max_existing_priority + duplicate_rank AS new_priority
            FROM duplicate_sources
        )
        UPDATE scraping_sources ss
        SET club_id = a.new_id,
            priority = a.new_priority,
            enabled = false,
            metadata = COALESCE(ss.metadata, '{}'::jsonb)
                || jsonb_build_object(
                    'task_3150_disposition',
                    'moved disabled duplicate source from club ' || a.old_id || ' to club ' || a.new_id,
                    'task_3150_source_task',
                    a.task_ref
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
                    'task_3150_disposition',
                    'disabled source remaining on duplicate club ' || f.old_id || ' after fold into club ' || f.new_id,
                    'task_3150_source_task',
                    f.task_ref
                ),
            updated_at = NOW()
        FROM task_3150_folds f
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
        JOIN task_3150_duplicate_show_map m ON m.old_show_id = li.show_id
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
        JOIN task_3150_duplicate_show_map m ON m.old_show_id = ts.show_id
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
        JOIN task_3150_duplicate_show_map m ON m.old_show_id = t.show_id
        WHERE m.new_show_id IS NOT NULL
        ON CONFLICT (show_id, type) DO NOTHING
        """
    )
    counts["tickets_copied"] = cur.rowcount

    cur.execute(
        """
        DELETE FROM sent_notifications sn
        USING task_3150_duplicate_show_map m,
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
        FROM task_3150_duplicate_show_map m
        WHERE m.new_show_id IS NOT NULL
          AND sn.show_id = m.old_show_id
        """
    )
    counts["sent_notifications_repointed"] = cur.rowcount

    cur.execute(
        """
        UPDATE ticket_purchase_click_events tpce
        SET show_id = m.new_show_id,
            club_id = m.target_club_id
        FROM task_3150_duplicate_show_map m
        WHERE m.new_show_id IS NOT NULL
          AND tpce.show_id = m.old_show_id
        """
    )
    counts["click_events_repointed_to_existing_show"] = cur.rowcount

    cur.execute(
        """
        DELETE FROM shows s
        USING task_3150_duplicate_show_map m
        WHERE s.id = m.old_show_id
          AND m.new_show_id IS NOT NULL
        """
    )
    counts["colliding_duplicate_shows_deleted"] = cur.rowcount

    cur.execute(
        """
        UPDATE shows s
        SET club_id = m.canonical_club_id
        FROM task_3150_duplicate_show_map m
        WHERE s.id = m.old_show_id
          AND m.new_show_id IS NULL
        """
    )
    counts["noncolliding_shows_moved"] = cur.rowcount

    cur.execute(
        """
        UPDATE ticket_purchase_click_events tpce
        SET club_id = f.new_id
        FROM task_3150_folds f
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
        JOIN task_3150_folds f ON f.old_id = fc.club_id
        ON CONFLICT (profile_id, club_id) DO NOTHING
        """
    )
    counts["favorite_clubs_inserted"] = cur.rowcount

    cur.execute(
        """
        DELETE FROM favorite_clubs fc
        USING task_3150_folds f
        WHERE fc.club_id = f.old_id
        """
    )
    counts["duplicate_favorite_clubs_deleted"] = cur.rowcount

    cur.execute(
        """
        INSERT INTO production_company_venues (production_company_id, club_id)
        SELECT pcv.production_company_id, f.new_id
        FROM production_company_venues pcv
        JOIN task_3150_folds f ON f.old_id = pcv.club_id
        ON CONFLICT (production_company_id, club_id) DO NOTHING
        """
    )
    counts["production_company_venues_inserted"] = cur.rowcount

    cur.execute(
        """
        DELETE FROM production_company_venues pcv
        USING task_3150_folds f
        WHERE pcv.club_id = f.old_id
        """
    )
    counts["duplicate_production_company_venues_deleted"] = cur.rowcount

    cur.execute(
        """
        INSERT INTO tagged_clubs (club_id, tag_id)
        SELECT f.new_id, tc.tag_id
        FROM tagged_clubs tc
        JOIN task_3150_folds f ON f.old_id = tc.club_id
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
        USING task_3150_folds f
        WHERE tc.club_id = f.old_id
        """
    )
    counts["duplicate_tagged_clubs_deleted"] = cur.rowcount

    cur.execute(
        """
        DELETE FROM email_subscriptions es
        USING task_3150_folds f, email_subscriptions existing
        WHERE es.club_id = f.old_id
          AND existing.club_id = f.new_id
        """
    )
    counts["conflicting_email_subscriptions_deleted"] = cur.rowcount

    cur.execute(
        """
        UPDATE email_subscriptions es
        SET club_id = f.new_id
        FROM task_3150_folds f
        WHERE es.club_id = f.old_id
        """
    )
    counts["email_subscriptions_moved"] = cur.rowcount

    cur.execute(
        """
        UPDATE processed_emails pe
        SET club_id = f.new_id
        FROM task_3150_folds f
        WHERE pe.club_id = f.old_id
        """
    )
    counts["processed_emails_moved"] = cur.rowcount

    cur.execute(
        """
        UPDATE club_image_assets cia
        SET club_id = f.new_id
        FROM task_3150_folds f
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
        FROM task_3150_folds f
        WHERE cia.club_id = f.old_id
          AND cia.is_active
        """
    )
    counts["duplicate_active_club_images_deactivated"] = cur.rowcount

    cur.execute(
        """
        UPDATE scraper_run_clubs src
        SET club_id = f.new_id
        FROM task_3150_folds f
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
        FROM task_3150_folds f
        WHERE c.id = f.old_id
        """
    )
    counts["duplicate_clubs_closed"] = cur.rowcount

    cur.execute(
        """
        UPDATE clubs
        SET total_shows = (SELECT COUNT(*) FROM shows WHERE shows.club_id = clubs.id)
        WHERE id IN (
            SELECT new_id FROM task_3150_folds
            UNION
            SELECT old_id FROM task_3150_folds
            UNION
            SELECT target_id FROM task_3150_alternate_target_clubs
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
        "source_tasks": [fold.task_ref for fold in FOLDS],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
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
        description="Fold duplicate club records audited in TASK-3045 through TASK-3049."
    )
    parser.add_argument("--dry-run", action="store_true")
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
