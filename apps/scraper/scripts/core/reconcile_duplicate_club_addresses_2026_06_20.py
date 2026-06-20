#!/usr/bin/env python3
"""
Reconcile duplicate physical-address club rows (TASK-3030).

Background
----------
The address audit found 40 normalized duplicate-address groups across active
club rows. Most are valid shared-location cases: multi-room comedy clubs,
rooms inside casinos/theaters, or independent venues inside a larger complex.
Several rows, however, are stale aliases or import artifacts that duplicate a
canonical venue and should not remain as active venue rows.

What this script does
---------------------
1. Validates every explicitly-handled club row still has the expected name.
2. Consolidates stale alias rows into canonical club rows without losing show
   attribution. Conflicting duplicate shows are deleted only after click events
   are repointed; non-conflicting shows move to the canonical club.
3. Closes hidden zero-show/import-artifact rows.
4. Disables sources attached to closed duplicate rows, stamping
   metadata.task_3030_duplicate_address_reconcile.
5. Annotates remaining intentional shared-location rows in clubs.description so
   the post-cleanup report distinguishes expected shared addresses from stale
   duplicates.

Idempotent: re-running after apply plans no writes.

Usage
-----
    cd apps/scraper
    make run-script SCRIPT=scripts/core/reconcile_duplicate_club_addresses_2026_06_20.py ARGS='--dry-run'
    make run-script SCRIPT=scripts/core/reconcile_duplicate_club_addresses_2026_06_20.py
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
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

_TASK_ID = 3030
_METADATA_KEY = "task_3030_duplicate_address_reconcile"
_DESCRIPTION_MARKER = "TASK-3030 duplicate-address classification:"


@dataclass(frozen=True)
class MergePair:
    old_id: int
    new_id: int
    old_name: str
    new_name: str
    classification: str
    rationale: str


@dataclass(frozen=True)
class CloseRow:
    club_id: int
    name: str
    canonical_id: int
    classification: str
    rationale: str


@dataclass(frozen=True)
class PreserveRow:
    club_id: int
    name: str
    classification: str
    rationale: str


_MERGES: tuple[MergePair, ...] = (
    MergePair(
        5315,
        5316,
        "The Fox - Spokane",
        "Martin Woldson Theater at the Fox",
        "alias_duplicate",
        "same venue and same Ticketmaster show; preserve clearer full venue name",
    ),
    MergePair(
        4637,
        4639,
        "Bushnell",
        "Bushnell Theatre/ Mortensen Hall",
        "alias_duplicate",
        "generic complex row duplicated the named Mortensen Hall row",
    ),
    MergePair(
        4643,
        5386,
        "The Clyde Theatre-IN",
        "The Clyde",
        "alias_duplicate",
        "Ticketmaster suffix row duplicated The Clyde show set",
    ),
    MergePair(
        4784,
        4781,
        "Belly Up",
        "Belly Up Tavern",
        "alias_duplicate",
        "short alias duplicated Belly Up Tavern shows",
    ),
    MergePair(
        5277,
        5347,
        "The Lobero",
        "Lobero Theatre",
        "alias_duplicate",
        "short alias duplicated Lobero Theatre shows",
    ),
    MergePair(
        5324,
        5326,
        "Bing Crosby Theatre",
        "Bing Crosby Theater",
        "alias_duplicate",
        "alternate spelling duplicated the same Ticketmaster event",
    ),
    MergePair(
        5370,
        5371,
        "Lensic Theatre",
        "Lensic Performing Arts Center",
        "alias_duplicate",
        "venue alias duplicated the same Lensic event",
    ),
    MergePair(
        4610,
        5384,
        "Speaker Jo Ann Davidson Theatre (formerly Capitol Theatre)",
        "Speaker Jo Ann Davidson Theatre",
        "alias_duplicate",
        "old parenthetical name duplicated the current venue row",
    ),
    MergePair(
        5427,
        5426,
        "Juanita K. Hammons Halls for the Performing Arts",
        "Juanita K. Hammons Hall",
        "alias_duplicate",
        "pluralized alias duplicated the named hall row",
    ),
    MergePair(
        5446,
        5445,
        "Luther Burbank Center",
        "Luther Burbank Center for the Arts",
        "alias_duplicate",
        "short alias duplicated the full venue row",
    ),
    MergePair(
        3333,
        2280,
        "2010 Waugh Dr",
        "The Riot Comedy Club",
        "stale_address_named_row",
        "address-only Eventbrite venue row contained Riot shows and is not a venue identity",
    ),
)

_CLOSE_ROWS: tuple[CloseRow, ...] = (
    CloseRow(
        3003,
        "Stardome",
        633,
        "stale_import_artifact",
        "hidden zero-show tour_dates row duplicates Stardome Comedy Club",
    ),
    CloseRow(
        3047,
        "US Hollywood Casino Joliet",
        2926,
        "stale_import_artifact",
        "hidden zero-show tour_dates row duplicates Hollywood Casino Joliet",
    ),
    CloseRow(
        8881,
        "The Bunker Theater",
        8879,
        "stale_hidden_placeholder",
        "hidden zero-show row shares JEST Improv suite and has no source to preserve",
    ),
)

_PRESERVE_ROWS: tuple[PreserveRow, ...] = (
    PreserveRow(
        4817,
        "Sound Waves at Hard Rock Hotel & Casino Atlantic City",
        "valid_multi_room",
        "distinct room at Hard Rock Atlantic City",
    ),
    PreserveRow(4672, "Hard Rock Live at Etess Arena", "valid_multi_room", "distinct room at Hard Rock Atlantic City"),
    PreserveRow(
        4846,
        "Voodoo Room at the House of Blues San Diego",
        "venue_within_venue",
        "room inside House of Blues San Diego",
    ),
    PreserveRow(5136, "House of Blues San Diego", "venue_within_venue", "parent venue distinct from Voodoo Room"),
    PreserveRow(
        6779, "Punch Line Houston", "venue_within_venue", "comedy room at same address as House of Blues Houston"
    ),
    PreserveRow(4674, "House of Blues Houston", "venue_within_venue", "parent venue distinct from Punch Line Houston"),
    PreserveRow(8829, "The Pack Theater", "valid_multi_room", "independent theater sharing the WGIS address"),
    PreserveRow(
        8830,
        "WGIS - World's Greatest Improv School",
        "valid_multi_room",
        "school/show venue sharing the Pack Theater address",
    ),
    PreserveRow(390, "Wiseguys Comedy Club - Salt Lake City", "valid_multi_room", "main Wiseguys venue"),
    PreserveRow(605, "Wiseguys - The Cabaret", "valid_multi_room", "named Wiseguys room"),
    PreserveRow(404, "Wiseguys - The Rickles Room", "valid_multi_room", "named Wiseguys room"),
    PreserveRow(4791, "Amaturo Theater at Broward Center", "valid_multi_room", "named Broward Center theater"),
    PreserveRow(5216, "Au-Rene Theater at the Broward Center", "valid_multi_room", "named Broward Center theater"),
    PreserveRow(2281, "Rudyard's", "venue_within_venue", "bar venue sharing address with Riot Comedy Club"),
    PreserveRow(2280, "The Riot Comedy Club", "venue_within_venue", "comedy club inside or associated with Rudyard's"),
    PreserveRow(6796, "Punch Line Comedy Club - Sacramento", "valid_multi_room", "main Punch Line Sacramento room"),
    PreserveRow(4564, "Punch Line Sacramento Callback Bar", "valid_multi_room", "named Callback Bar room"),
    PreserveRow(4693, "Reggies Bananna's Shack", "valid_multi_room", "named Reggies room"),
    PreserveRow(4708, "Reggies Music Joint", "valid_multi_room", "named Reggies room"),
    PreserveRow(4779, "The Sound", "venue_within_venue", "venue at Del Mar Fairgrounds address"),
    PreserveRow(4632, "Del Mar Fairgrounds", "venue_within_venue", "parent fairgrounds distinct from The Sound"),
    PreserveRow(4794, "IMAX THEATRE at TROPICANA", "valid_multi_room", "named Tropicana room"),
    PreserveRow(4669, "Tropicana Showroom at Tropicana Atlantic City", "valid_multi_room", "named Tropicana room"),
    PreserveRow(4581, "Mayo Civic Center Auditorium", "valid_multi_room", "named Mayo Civic Center room"),
    PreserveRow(
        5206, "CH Mayo Presentation Hall at Mayo Civic Center", "valid_multi_room", "named Mayo Civic Center room"
    ),
    PreserveRow(
        5291,
        "Jacksonville Center for the Performing Arts - Terry Theater",
        "valid_multi_room",
        "named Jacksonville Center theater",
    ),
    PreserveRow(
        5219,
        "Jacksonville Center for the Performing Arts - Moran Theater",
        "valid_multi_room",
        "named Jacksonville Center theater",
    ),
    PreserveRow(5112, "Seneca Niagara Resort & Casino Bears Den", "valid_multi_room", "named Seneca Niagara room"),
    PreserveRow(4981, "Seneca Niagara Resort & Casino Event Center", "valid_multi_room", "named Seneca Niagara room"),
    PreserveRow(
        4618, "Foundation Room at House of Blues Chicago", "venue_within_venue", "room inside House of Blues Chicago"
    ),
    PreserveRow(5319, "House of Blues Chicago", "venue_within_venue", "parent venue distinct from Foundation Room"),
    PreserveRow(4826, "Palazzo Theatre at The Venetian Resort", "valid_multi_room", "named Venetian room"),
    PreserveRow(4870, "The Venetian Theatre at The Venetian Resort", "valid_multi_room", "named Venetian room"),
    PreserveRow(4548, "Comedy Cellar at Rio Las Vegas", "venue_within_venue", "comedy club inside Rio"),
    PreserveRow(4552, "The Empire Strips Back Theater", "venue_within_venue", "separate theater inside Rio"),
    PreserveRow(4574, "Brad Garrett's Comedy Club", "venue_within_venue", "comedy club inside MGM Grand"),
    PreserveRow(4664, "MGM Grand Theater", "venue_within_venue", "theater inside MGM Grand"),
    PreserveRow(4562, "Underground Theater at MGM Grand", "venue_within_venue", "named MGM Grand theater"),
    PreserveRow(5156, "MGM Grand Garden Arena", "venue_within_venue", "arena inside MGM Grand"),
    PreserveRow(
        4964, "Spartanburg Memorial Auditorium", "venue_within_venue", "parent auditorium distinct from The Hall"
    ),
    PreserveRow(
        4646, "The Hall at Spartanburg Memorial Auditorium", "venue_within_venue", "named room inside auditorium"
    ),
    PreserveRow(4797, "Premier Theater at Foxwoods Resort Casino", "valid_multi_room", "named Foxwoods room"),
    PreserveRow(4642, "Great Cedar Showroom at Foxwoods Resort Casino", "valid_multi_room", "named Foxwoods room"),
    PreserveRow(
        6802, "Laugh Factory at the Silver Legacy Casino", "venue_within_venue", "comedy club inside Silver Legacy"
    ),
    PreserveRow(4571, "Silver Legacy Casino Reno", "venue_within_venue", "parent casino distinct from Laugh Factory"),
    PreserveRow(
        2290, "Bombs Away! Comedy at the Comet", "venue_within_venue", "producer/show brand at The Comet address"
    ),
    PreserveRow(2289, "The Comet", "venue_within_venue", "bar venue distinct from Bombs Away shows"),
    PreserveRow(
        4930, "Treasure Island Resort & Casino", "venue_within_venue", "parent resort distinct from amphitheater"
    ),
    PreserveRow(4882, "Treasure Island Amphitheater", "venue_within_venue", "amphitheater at resort address"),
    PreserveRow(5230, "Kravis Center - Dreyfoos Hall", "valid_multi_room", "named Kravis Center hall"),
    PreserveRow(5269, "Kravis Center", "venue_within_venue", "parent venue row distinct from Dreyfoos Hall"),
    PreserveRow(5242, "Tilles Center Concert Hall", "valid_multi_room", "named Tilles Center room"),
    PreserveRow(5327, "Tilles Center - Krasnoff Theater", "valid_multi_room", "named Tilles Center room"),
    PreserveRow(4912, "Neal S Blaisdell Concert Hall", "valid_multi_room", "named Blaisdell room"),
    PreserveRow(5442, "Neal S Blaisdell Arena", "valid_multi_room", "named Blaisdell room"),
    PreserveRow(4488, "Hobby Center", "venue_within_venue", "parent Hobby Center row"),
    PreserveRow(5418, "Zilkha Hall at the Hobby Center", "venue_within_venue", "named room inside Hobby Center"),
    PreserveRow(4554, "Hollywood Improv (The Main Room)", "valid_multi_room", "named Hollywood Improv room"),
    PreserveRow(4591, "Hollywood Improv (The Lab)", "valid_multi_room", "named Hollywood Improv room"),
    PreserveRow(4539, "Dudley Riggs Theatre", "valid_multi_room", "main Dudley Riggs venue"),
    PreserveRow(4821, "Dudley Riggs Theatre First Floor", "valid_multi_room", "named Dudley Riggs floor"),
    PreserveRow(5109, "Pantages Theater", "valid_multi_room", "named Tacoma theater"),
    PreserveRow(5175, "Theatre On the Square", "valid_multi_room", "named Tacoma theater"),
)


def _all_expected_names() -> dict[int, str]:
    expected: dict[int, str] = {}
    for item in _MERGES:
        expected[item.old_id] = item.old_name
        expected[item.new_id] = item.new_name
    for item in _CLOSE_ROWS:
        expected[item.club_id] = item.name
    for item in _PRESERVE_ROWS:
        expected[item.club_id] = item.name
    return expected


def _fetch_clubs(cur: RealDictCursor) -> dict[int, Any]:
    club_ids = sorted(_all_expected_names())
    cur.execute(
        """
        SELECT id, name, visible, status, closed_at, total_shows, description
        FROM clubs
        WHERE id = ANY(%s)
        """,
        (club_ids,),
    )
    return {row["id"]: row for row in cur.fetchall()}


def _fetch_duplicate_report(cur: RealDictCursor) -> list[Any]:
    cur.execute(
        """
        WITH normalized AS (
            SELECT
                id,
                name,
                visible,
                status,
                club_type,
                address,
                description,
                lower(regexp_replace(regexp_replace(coalesce(address, ''), '[^a-zA-Z0-9]+', ' ', 'g'), '\\s+', ' ', 'g')) AS norm_address
            FROM clubs
            WHERE status = 'active'
              AND coalesce(address, '') <> ''
        ),
        duplicate_groups AS (
            SELECT norm_address
            FROM normalized
            GROUP BY norm_address
            HAVING count(*) > 1
        )
        SELECT
            n.norm_address,
            count(*) AS rows,
            count(*) FILTER (WHERE visible) AS visible_rows,
            bool_and(coalesce(n.description, '') LIKE %s) AS all_classified,
            jsonb_agg(
                jsonb_build_object(
                    'id', n.id,
                    'name', n.name,
                    'visible', n.visible,
                    'club_type', n.club_type
                )
                ORDER BY n.visible DESC, n.name
            ) AS clubs
        FROM normalized n
        JOIN duplicate_groups dg ON dg.norm_address = n.norm_address
        GROUP BY n.norm_address
        ORDER BY visible_rows DESC, rows DESC, n.norm_address
        """,
        (f"%{_DESCRIPTION_MARKER}%",),
    )
    return cur.fetchall()


def _validate_shape(cur: RealDictCursor, clubs: dict[int, Any]) -> list[str]:
    problems: list[str] = []
    for club_id, expected_name in _all_expected_names().items():
        club = clubs.get(club_id)
        if club is None:
            problems.append(f"clubs.id={club_id} missing")
        elif club["name"] != expected_name:
            problems.append(f"clubs.id={club_id} name={club['name']!r} (expected {expected_name!r})")

    old_ids = [item.old_id for item in _MERGES]
    cur.execute(
        """
        WITH old_shows AS (
            SELECT s.id, s.club_id, s.date, s.room
            FROM shows s
            WHERE s.club_id = ANY(%s)
        )
        SELECT count(*) AS remaining_old_shows
        FROM old_shows
        """,
        (old_ids,),
    )
    remaining_old_shows = cur.fetchone()["remaining_old_shows"]
    if remaining_old_shows and any(clubs[club_id]["status"] != "active" for club_id in old_ids):
        problems.append("some merge-source clubs are closed but still have show rows; refusing idempotent run")
    return problems


def _create_temp_tables(cur: RealDictCursor) -> None:
    cur.execute("""
        CREATE TEMP TABLE task_3030_merges (
            old_id integer PRIMARY KEY,
            new_id integer NOT NULL,
            old_name text NOT NULL,
            new_name text NOT NULL,
            classification text NOT NULL,
            rationale text NOT NULL
        ) ON COMMIT DROP
        """)
    execute_values(
        cur,
        """
        INSERT INTO task_3030_merges
            (old_id, new_id, old_name, new_name, classification, rationale)
        VALUES %s
        """,
        [
            (
                item.old_id,
                item.new_id,
                item.old_name,
                item.new_name,
                item.classification,
                item.rationale,
            )
            for item in _MERGES
        ],
    )

    cur.execute("""
        CREATE TEMP TABLE task_3030_closes (
            club_id integer PRIMARY KEY,
            name text NOT NULL,
            canonical_id integer NOT NULL,
            classification text NOT NULL,
            rationale text NOT NULL
        ) ON COMMIT DROP
        """)
    execute_values(
        cur,
        """
        INSERT INTO task_3030_closes
            (club_id, name, canonical_id, classification, rationale)
        VALUES %s
        """,
        [
            (
                item.club_id,
                item.name,
                item.canonical_id,
                item.classification,
                item.rationale,
            )
            for item in _CLOSE_ROWS
        ],
    )

    cur.execute("""
        CREATE TEMP TABLE task_3030_preserve (
            club_id integer PRIMARY KEY,
            name text NOT NULL,
            classification text NOT NULL,
            rationale text NOT NULL
        ) ON COMMIT DROP
        """)
    execute_values(
        cur,
        """
        INSERT INTO task_3030_preserve
            (club_id, name, classification, rationale)
        VALUES %s
        """,
        [(item.club_id, item.name, item.classification, item.rationale) for item in _PRESERVE_ROWS],
    )


def _planned_counts(cur: RealDictCursor) -> dict[str, int]:
    cur.execute(
        """
        WITH duplicate_show_merges AS (
            SELECT old_show.id AS old_show_id
            FROM task_3030_merges m
            JOIN shows old_show ON old_show.club_id = m.old_id
            JOIN shows new_show
              ON new_show.club_id = m.new_id
             AND new_show.date = old_show.date
             AND new_show.room IS NOT DISTINCT FROM old_show.room
        )
        SELECT
            (SELECT count(*) FROM shows s JOIN task_3030_merges m ON m.old_id = s.club_id) AS old_shows,
            (SELECT count(*) FROM duplicate_show_merges) AS conflicting_shows,
            (SELECT count(*) FROM shows s JOIN task_3030_merges m ON m.old_id = s.club_id
             WHERE NOT EXISTS (SELECT 1 FROM duplicate_show_merges d WHERE d.old_show_id = s.id)) AS movable_shows,
            (SELECT count(*) FROM scraping_sources ss
             WHERE ss.club_id IN (
                 SELECT old_id FROM task_3030_merges
                 UNION
                 SELECT club_id FROM task_3030_closes
             )
             AND (ss.enabled = TRUE OR NOT (COALESCE(ss.metadata, '{}'::jsonb) ? %s))) AS source_updates,
            (SELECT count(*) FROM clubs c
             JOIN task_3030_preserve p ON p.club_id = c.id
             WHERE c.status = 'active'
               AND COALESCE(c.description, '') NOT LIKE %s) AS preserve_annotations,
            (SELECT count(*) FROM clubs c
             WHERE c.id IN (
                 SELECT old_id FROM task_3030_merges
                 UNION
                 SELECT club_id FROM task_3030_closes
             )
             AND (c.status <> 'closed' OR c.visible = TRUE OR c.total_shows <> 0
                  OR COALESCE(c.description, '') NOT LIKE %s)) AS close_updates
        """,
        (_METADATA_KEY, f"%{_DESCRIPTION_MARKER}%", f"%{_DESCRIPTION_MARKER}%"),
    )
    return dict(cur.fetchone())


def _apply_updates(cur: RealDictCursor) -> None:
    cur.execute("""
        CREATE TEMP TABLE task_3030_duplicate_show_merges AS
        SELECT
            old_show.id AS old_show_id,
            new_show.id AS new_show_id,
            m.old_id AS old_club_id,
            m.new_id AS new_club_id
        FROM task_3030_merges m
        JOIN shows old_show ON old_show.club_id = m.old_id
        JOIN shows new_show
          ON new_show.club_id = m.new_id
         AND new_show.date = old_show.date
         AND new_show.room IS NOT DISTINCT FROM old_show.room
        """)

    cur.execute("""
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
            m.new_id,
            m.old_name,
            btrim(regexp_replace(replace(lower(m.old_name), '&', ' and '), '[^a-z0-9]+', ' ', 'g')),
            new_club.city,
            new_club.state,
            btrim(regexp_replace(lower(coalesce(new_club.city, '')), '[^a-z0-9]+', ' ', 'g')),
            lower(coalesce(new_club.state, '')),
            'TASK-3030',
            TRUE,
            NOW(),
            NOW()
        FROM task_3030_merges m
        JOIN clubs new_club ON new_club.id = m.new_id
        ON CONFLICT (normalized_alias_name, normalized_city, normalized_state) DO NOTHING
        """)

    cur.execute("""
        UPDATE ticket_purchase_click_events tpce
        SET show_id = dsm.new_show_id,
            club_id = dsm.new_club_id
        FROM task_3030_duplicate_show_merges dsm
        WHERE tpce.show_id = dsm.old_show_id
        """)

    cur.execute("""
        UPDATE shows s
        SET club_id = m.new_id
        FROM task_3030_merges m
        WHERE s.club_id = m.old_id
          AND NOT EXISTS (
              SELECT 1
              FROM task_3030_duplicate_show_merges dsm
              WHERE dsm.old_show_id = s.id
          )
        """)

    cur.execute("""
        UPDATE ticket_purchase_click_events tpce
        SET club_id = m.new_id
        FROM task_3030_merges m
        WHERE tpce.club_id = m.old_id
        """)

    cur.execute("""
        INSERT INTO favorite_clubs (profile_id, club_id)
        SELECT fc.profile_id, m.new_id
        FROM favorite_clubs fc
        JOIN task_3030_merges m ON m.old_id = fc.club_id
        ON CONFLICT (profile_id, club_id) DO NOTHING
        """)
    cur.execute("""
        DELETE FROM favorite_clubs fc
        USING task_3030_merges m
        WHERE fc.club_id = m.old_id
        """)

    cur.execute("""
        INSERT INTO tagged_clubs (club_id, tag_id)
        SELECT m.new_id, tc.tag_id
        FROM tagged_clubs tc
        JOIN task_3030_merges m ON m.old_id = tc.club_id
        ON CONFLICT DO NOTHING
        """)
    cur.execute("""
        DELETE FROM tagged_clubs tc
        USING task_3030_merges m
        WHERE tc.club_id = m.old_id
        """)

    for table_name in ("club_image_assets", "processed_emails"):
        cur.execute(f"""
            UPDATE {table_name} target
            SET club_id = m.new_id
            FROM task_3030_merges m
            WHERE target.club_id = m.old_id
            """)

    for table_name in (
        "production_company_venues",
        "eventbrite_organizer_venues",
        "email_subscriptions",
    ):
        cur.execute(f"""
            UPDATE {table_name} target
            SET club_id = m.new_id
            FROM task_3030_merges m
            WHERE target.club_id = m.old_id
              AND NOT EXISTS (
                  SELECT 1
                  FROM {table_name} existing
                  WHERE existing.club_id = m.new_id
              )
            """)
        cur.execute(f"""
            DELETE FROM {table_name} target
            USING task_3030_merges m
            WHERE target.club_id = m.old_id
            """)

    cur.execute(
        """
        UPDATE scraping_sources ss
        SET
            enabled = FALSE,
            metadata = COALESCE(ss.metadata, '{}'::jsonb) || jsonb_build_object(
                %s,
                jsonb_build_object(
                    'task_id', %s,
                    'closed_club_id', ss.club_id,
                    'canonical_club_id', targets.canonical_id,
                    'classification', targets.classification,
                    'rationale', targets.rationale
                )
            ),
            updated_at = NOW()
        FROM (
            SELECT old_id AS club_id, new_id AS canonical_id, classification, rationale
            FROM task_3030_merges
            UNION ALL
            SELECT club_id, canonical_id, classification, rationale
            FROM task_3030_closes
        ) targets
        WHERE ss.club_id = targets.club_id
          AND (ss.enabled = TRUE OR NOT (COALESCE(ss.metadata, '{}'::jsonb) ? %s))
        """,
        (_METADATA_KEY, _TASK_ID, _METADATA_KEY),
    )

    cur.execute("""
        DELETE FROM shows s
        USING task_3030_duplicate_show_merges dsm
        WHERE s.id = dsm.old_show_id
        """)

    cur.execute(
        """
        UPDATE clubs c
        SET description = CASE
                WHEN COALESCE(c.description, '') LIKE %s THEN c.description
                ELSE concat_ws(
                    E'\n\n',
                    NULLIF(c.description, ''),
                    %s || ' ' || p.classification || '. ' || p.rationale || '.'
                )
            END
        FROM task_3030_preserve p
        WHERE c.id = p.club_id
          AND c.status = 'active'
        """,
        (f"%{_DESCRIPTION_MARKER}%", _DESCRIPTION_MARKER),
    )

    cur.execute(
        """
        UPDATE clubs c
        SET
            visible = FALSE,
            status = 'closed',
            closed_at = COALESCE(c.closed_at, NOW()),
            total_shows = 0,
            description = CASE
                WHEN COALESCE(c.description, '') LIKE %s THEN c.description
                ELSE concat_ws(
                    E'\n\n',
                    NULLIF(c.description, ''),
                    %s || ' ' || targets.classification || '. Consolidated into club '
                        || targets.canonical_id || ' by TASK-3030. ' || targets.rationale || '.'
                )
            END
        FROM (
            SELECT old_id AS club_id, new_id AS canonical_id, classification, rationale
            FROM task_3030_merges
            UNION ALL
            SELECT club_id, canonical_id, classification, rationale
            FROM task_3030_closes
        ) targets
        WHERE c.id = targets.club_id
        """,
        (f"%{_DESCRIPTION_MARKER}%", _DESCRIPTION_MARKER),
    )

    cur.execute("""
        UPDATE clubs c
        SET total_shows = counts.show_count
        FROM (
            SELECT club_id, count(*)::integer AS show_count
            FROM shows
            WHERE club_id IN (
                SELECT new_id FROM task_3030_merges
                UNION
                SELECT old_id FROM task_3030_merges
                UNION
                SELECT club_id FROM task_3030_closes
            )
            GROUP BY club_id
        ) counts
        WHERE c.id = counts.club_id
        """)
    cur.execute("""
        UPDATE clubs c
        SET total_shows = 0
        WHERE c.id IN (
            SELECT old_id FROM task_3030_merges
            UNION
            SELECT club_id FROM task_3030_closes
        )
        """)


def _assert_no_direct_refs(cur: RealDictCursor) -> None:
    cur.execute("""
        WITH closed_ids AS (
            SELECT old_id AS club_id FROM task_3030_merges
            UNION
            SELECT club_id FROM task_3030_closes
        )
        SELECT
            (SELECT count(*) FROM shows s JOIN closed_ids c ON c.club_id = s.club_id)
          + (SELECT count(*) FROM favorite_clubs fc JOIN closed_ids c ON c.club_id = fc.club_id)
          + (SELECT count(*) FROM tagged_clubs tc JOIN closed_ids c ON c.club_id = tc.club_id)
          + (SELECT count(*) FROM club_image_assets cia JOIN closed_ids c ON c.club_id = cia.club_id)
          + (SELECT count(*) FROM processed_emails pe JOIN closed_ids c ON c.club_id = pe.club_id)
          + (SELECT count(*) FROM production_company_venues pcv JOIN closed_ids c ON c.club_id = pcv.club_id)
          + (SELECT count(*) FROM eventbrite_organizer_venues eov JOIN closed_ids c ON c.club_id = eov.club_id)
          + (SELECT count(*) FROM email_subscriptions es JOIN closed_ids c ON c.club_id = es.club_id)
          + (SELECT count(*) FROM ticket_purchase_click_events tpce JOIN closed_ids c ON c.club_id = tpce.club_id)
          AS remaining_refs
        """)
    remaining_refs = cur.fetchone()["remaining_refs"]
    if remaining_refs:
        raise RuntimeError(f"{remaining_refs} direct dependent references remain on closed duplicate clubs")


def _assert_duplicate_groups_classified(cur: RealDictCursor) -> None:
    report = _fetch_duplicate_report(cur)
    unclassified = [row for row in report if not row["all_classified"]]
    if unclassified:
        for row in unclassified:
            print(
                f"UNCLASSIFIED duplicate group {row['norm_address']}: {row['clubs']}",
                file=sys.stderr,
            )
        raise RuntimeError(f"{len(unclassified)} active duplicate address groups remain unclassified")


def run(dry_run: bool) -> int:
    with get_transaction() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            clubs = _fetch_clubs(cur)
            problems = _validate_shape(cur, clubs)
            if problems:
                print("ABORT: shape mismatch - refusing to write:", file=sys.stderr)
                for problem in problems:
                    print(f"  {problem}", file=sys.stderr)
                return 1

            _create_temp_tables(cur)
            before_report = _fetch_duplicate_report(cur)
            plan = _planned_counts(cur)

            print("=== BEFORE ===")
            print(f"active duplicate address groups: {len(before_report)}")
            print(
                "planned: "
                f"{plan['old_shows']} old shows "
                f"({plan['conflicting_shows']} conflicting, {plan['movable_shows']} movable), "
                f"{plan['source_updates']} source updates, "
                f"{plan['close_updates']} club close updates, "
                f"{plan['preserve_annotations']} preserve annotations"
            )
            print("merge pairs:")
            for item in _MERGES:
                print(f"  {item.old_id} {item.old_name!r} -> {item.new_id} {item.new_name!r}")
            print("stale closes:")
            for item in _CLOSE_ROWS:
                print(f"  {item.club_id} {item.name!r} -> close; canonical {item.canonical_id}")

            if not any(plan.values()):
                _assert_duplicate_groups_classified(cur)
                print("No changes needed (idempotent re-run).")
                return 0

            if dry_run:
                print("--dry-run: no DB write performed.")
                conn.rollback()
                return 0

            _apply_updates(cur)
            _assert_no_direct_refs(cur)
            _assert_duplicate_groups_classified(cur)
            after_report = _fetch_duplicate_report(cur)
            print("=== AFTER ===")
            print(f"active duplicate address groups: {len(after_report)}")
            for row in after_report:
                print(
                    f"  {row['norm_address']}: rows={row['rows']} "
                    f"visible={row['visible_rows']} classified={row['all_classified']}"
                )

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()
    return run(dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
