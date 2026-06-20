#!/usr/bin/env python3
"""
Classify and disposition remaining non-venue club rows (TASK-3031).

Background
----------
The club address audit found rows that are not physical venues but still lived
in clubs with synthetic addresses: producer/aggregator rows such as Kricket
Comedy, Coastal Entertainment Productions, and Comedy Shows Near Me; the Big
Pine Comedy Festival multi-venue festival row; and an Eventbrite source whose
public location is disclosed only after booking.

TASK-3028 introduced source_targets for non-venue platform triggers, but the
single-venue Eventbrite path still writes shows to its input Club-shaped object.
Moving the secret-location Eventbrite source to source_targets would therefore
risk attaching shows to a source_target id. The safe disposition here is to stop
these remaining non-venue rows from being treated as venue scraper triggers
while preserving their dependent rows and producer/festival identity.

What this script does
---------------------
1. Validates the target clubs, producer rows, dependent shows, and scraping
   sources still have the expected shape.
2. Reclassifies producer rows as hidden club_type='producer' rows whose durable
   public identity lives in production_companies.
3. Leaves Big Pine Comedy Festival as club_type='festival' and keeps its
   SeatEngine source enabled, because festivals are intentionally represented in
   clubs with a non-club club_type.
4. Reclassifies the secret-location Eventbrite row as hidden
   club_type='secret_location' and disables its venue-owned source.
5. Disables the venue-owned producer/secret-location scraping_sources and
   annotates every modified source under metadata.task_3031_non_venue_disposition.
   Club rows do not have a metadata column, so their descriptions receive a
   TASK-3031 annotation instead.

Idempotent: only writes when a target row differs from the planned state.

Usage
-----
    cd apps/scraper
    make run-script SCRIPT=scripts/core/disposition_non_venue_club_rows_2026_06_20.py ARGS='--dry-run'
    make run-script SCRIPT=scripts/core/disposition_non_venue_club_rows_2026_06_20.py
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

load_dotenv(_root / ".env")

from laughtrack.adapters.db import get_transaction

_TASK_ID = 3031
_METADATA_KEY = "task_3031_non_venue_disposition"
_DESCRIPTION_MARKER = "TASK-3031 disposition:"


@dataclass(frozen=True)
class ClubDisposition:
    club_id: int
    name: str
    target_visible: bool
    target_club_type: str
    target_address: str
    classification: str
    source_ids_to_disable: tuple[int, ...] = ()
    expected_production_company: str | None = None
    expected_scraper_source_id: int | None = None
    keep_source_enabled_reason: str | None = None


_DISPOSITIONS: tuple[ClubDisposition, ...] = (
    ClubDisposition(
        club_id=539,
        name="Kricket Comedy",
        target_visible=False,
        target_club_type="producer",
        target_address="Roving producer across NJ, PA, DE, and MD",
        classification="production_company_preserved",
        source_ids_to_disable=(308,),
        expected_production_company="Kricket Comedy",
        expected_scraper_source_id=308,
    ),
    ClubDisposition(
        club_id=556,
        name="Coastal Entertainment Productions",
        target_visible=False,
        target_club_type="producer",
        target_address="Roving producer across Coastal Entertainment markets",
        classification="production_company_preserved",
        source_ids_to_disable=(306,),
        expected_production_company="Coastal Entertainment Productions",
        expected_scraper_source_id=306,
    ),
    ClubDisposition(
        club_id=573,
        name="Big Pine Comedy Festival",
        target_visible=True,
        target_club_type="festival",
        target_address="Festival based in Chandler, AZ",
        classification="festival_preserved_in_clubs",
        expected_scraper_source_id=360,
        keep_source_enabled_reason=(
            "Festival rows are intentionally represented in clubs with "
            "club_type='festival'; keep the SeatEngine source enabled."
        ),
    ),
    ClubDisposition(
        club_id=620,
        name="Comedy Shows Near Me",
        target_visible=False,
        target_club_type="producer",
        target_address="Roving producer across DC, MD, and VA",
        classification="production_company_preserved",
        source_ids_to_disable=(207,),
        expected_production_company="Comedy Shows Near Me",
        expected_scraper_source_id=207,
    ),
    ClubDisposition(
        club_id=8735,
        name="Address in Booking details",
        target_visible=False,
        target_club_type="secret_location",
        target_address="Secret location in Miami, FL",
        classification="secret_location_eventbrite_retained_hidden",
        source_ids_to_disable=(5882,),
        expected_scraper_source_id=5882,
    ),
)

_SOURCE_EXPECTATIONS: dict[int, dict[str, Any]] = {
    308: {"club_id": 539, "platform": "seatengine", "scraper_key": "seatengine"},
    306: {"club_id": 556, "platform": "seatengine", "scraper_key": "seatengine"},
    360: {"club_id": 573, "platform": "seatengine", "scraper_key": "seatengine"},
    207: {"club_id": 620, "platform": "seatengine", "scraper_key": "seatengine"},
    5882: {"club_id": 8735, "platform": "eventbrite", "scraper_key": "eventbrite"},
}


def _load_metadata(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, str):
        return json.loads(raw)
    return dict(raw)


def _description_with_marker(description: str | None, note: str) -> str:
    existing = (description or "").strip()
    if _DESCRIPTION_MARKER in existing:
        return existing
    if existing:
        return f"{existing}\n\n{note}"
    return note


def _metadata_payload(disposition: ClubDisposition, source_id: int) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "task_id": _TASK_ID,
        "club_id": disposition.club_id,
        "club_name": disposition.name,
        "source_id": source_id,
        "classification": disposition.classification,
        "disposition": "disabled_venue_owned_non_venue_trigger",
        "rationale": (
            "This club row is not a physical venue. Its identity is preserved "
            "through the classified club_type and, where applicable, the "
            "matching production_companies row; the venue-owned source should "
            "not run as a venue scraper trigger."
        ),
    }
    if disposition.target_club_type == "secret_location":
        payload["rationale"] = (
            "This Eventbrite source represents a show whose location is "
            "disclosed after booking. It cannot be safely moved to "
            "source_targets until the single-source Eventbrite path can attach "
            "shows to a real venue rather than the proxy input object."
        )
    return payload


def _fetch_rows(cur: RealDictCursor) -> tuple[dict[int, Any], dict[int, Any], dict[str, Any], dict[int, Any]]:
    club_ids = [d.club_id for d in _DISPOSITIONS]
    source_ids = sorted(_SOURCE_EXPECTATIONS)
    producer_names = sorted(d.expected_production_company for d in _DISPOSITIONS if d.expected_production_company)

    cur.execute(
        """
        SELECT id, name, address, visible, status, club_type, description, total_shows
        FROM clubs
        WHERE id = ANY(%s)
        """,
        (club_ids,),
    )
    clubs = {row["id"]: row for row in cur.fetchall()}

    cur.execute(
        """
        SELECT id, club_id, source_target_id, platform::text AS platform, scraper_key,
               source_url, eventbrite_id, priority, enabled, metadata
        FROM scraping_sources
        WHERE id = ANY(%s)
        """,
        (source_ids,),
    )
    sources = {row["id"]: row for row in cur.fetchall()}

    cur.execute(
        """
        SELECT pc.id, pc.name, pc.visible, pc.website, pc.scraping_url,
               COUNT(s.id) AS stamped_shows
        FROM production_companies pc
        LEFT JOIN shows s ON s.production_company_id = pc.id
        WHERE pc.name = ANY(%s)
        GROUP BY pc.id
        """,
        (producer_names,),
    )
    producers = {row["name"]: row for row in cur.fetchall()}

    cur.execute(
        """
        SELECT c.id AS club_id,
               COUNT(s.id) AS shows,
               COUNT(s.id) FILTER (WHERE s.date > NOW()) AS future_shows,
               COUNT(s.id) FILTER (WHERE s.production_company_id IS NOT NULL) AS producer_stamped_shows
        FROM clubs c
        LEFT JOIN shows s ON s.club_id = c.id
        WHERE c.id = ANY(%s)
        GROUP BY c.id
        """,
        (club_ids,),
    )
    show_counts = {row["club_id"]: row for row in cur.fetchall()}
    return clubs, sources, producers, show_counts


def _validate_shape(
    clubs: dict[int, Any],
    sources: dict[int, Any],
    producers: dict[str, Any],
    show_counts: dict[int, Any],
) -> list[str]:
    problems: list[str] = []

    for disposition in _DISPOSITIONS:
        club = clubs.get(disposition.club_id)
        if club is None:
            problems.append(f"clubs.id={disposition.club_id} missing")
            continue
        if club["name"] != disposition.name:
            problems.append(f"clubs.id={disposition.club_id} name={club['name']!r} " f"(expected {disposition.name!r})")
        if club["status"] != "active":
            problems.append(f"clubs.id={disposition.club_id} status={club['status']!r} (expected 'active')")
        if disposition.name == "Big Pine Comedy Festival" and club["club_type"] != "festival":
            problems.append(
                f"clubs.id={disposition.club_id} club_type={club['club_type']!r} " "(expected pre-classified festival)"
            )

        counts = show_counts.get(disposition.club_id)
        if counts is None or counts["shows"] == 0:
            problems.append(f"clubs.id={disposition.club_id} has no dependent shows")
        if disposition.expected_production_company:
            producer = producers.get(disposition.expected_production_company)
            if producer is None:
                problems.append(f"production_companies.name={disposition.expected_production_company!r} missing")
            elif counts and producer["stamped_shows"] != counts["shows"]:
                problems.append(
                    f"production company {producer['name']!r} stamped_shows="
                    f"{producer['stamped_shows']} but club shows={counts['shows']}"
                )

        if disposition.expected_scraper_source_id is None:
            continue
        source = sources.get(disposition.expected_scraper_source_id)
        if source is None:
            problems.append(f"scraping_sources.id={disposition.expected_scraper_source_id} missing")
            continue
        expected_source = _SOURCE_EXPECTATIONS[disposition.expected_scraper_source_id]
        for key, expected in expected_source.items():
            if source[key] != expected:
                problems.append(f"scraping_sources.id={source['id']} {key}={source[key]!r} " f"(expected {expected!r})")
        if source["source_target_id"] is not None:
            problems.append(
                f"scraping_sources.id={source['id']} already has source_target_id=" f"{source['source_target_id']}"
            )

    return problems


def _planned_club_updates(clubs: dict[int, Any]) -> list[tuple[ClubDisposition, dict[str, Any]]]:
    updates: list[tuple[ClubDisposition, dict[str, Any]]] = []
    for disposition in _DISPOSITIONS:
        club = clubs[disposition.club_id]
        note = f"{_DESCRIPTION_MARKER} classified as {disposition.classification}; " f"not a physical venue club row."
        target = {
            "visible": disposition.target_visible,
            "club_type": disposition.target_club_type,
            "address": disposition.target_address,
            "description": _description_with_marker(club["description"], note),
        }
        if any(club[key] != value for key, value in target.items()):
            updates.append((disposition, target))
    return updates


def _planned_source_updates(
    sources: dict[int, Any],
) -> list[tuple[ClubDisposition, int, dict[str, Any]]]:
    updates: list[tuple[ClubDisposition, int, dict[str, Any]]] = []
    for disposition in _DISPOSITIONS:
        for source_id in disposition.source_ids_to_disable:
            source = sources[source_id]
            metadata = _load_metadata(source["metadata"])
            next_metadata = dict(metadata)
            next_metadata[_METADATA_KEY] = _metadata_payload(disposition, source_id)
            target = {"enabled": False, "metadata": next_metadata}
            if source["enabled"] is not False or metadata.get(_METADATA_KEY) != target["metadata"][_METADATA_KEY]:
                updates.append((disposition, source_id, target))
    return updates


def _print_snapshot(
    title: str,
    clubs: dict[int, Any],
    sources: dict[int, Any],
    show_counts: dict[int, Any],
) -> None:
    print(f"=== {title} ===")
    for disposition in _DISPOSITIONS:
        club = clubs[disposition.club_id]
        counts = show_counts[disposition.club_id]
        print(
            f"club {club['id']:>4} {club['name']!r}: visible={club['visible']} "
            f"type={club['club_type']!r} address={club['address']!r} "
            f"shows={counts['shows']} future={counts['future_shows']}"
        )
        if disposition.expected_scraper_source_id is not None:
            source = sources[disposition.expected_scraper_source_id]
            metadata = _load_metadata(source["metadata"])
            print(
                f"  source {source['id']:>4}: platform={source['platform']!r} "
                f"key={source['scraper_key']!r} enabled={source['enabled']} "
                f"has_task_metadata={_METADATA_KEY in metadata}"
            )


def run(dry_run: bool) -> int:
    with get_transaction() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            clubs, sources, producers, show_counts = _fetch_rows(cur)
            problems = _validate_shape(clubs, sources, producers, show_counts)
            if problems:
                print("ABORT: shape mismatch - refusing to write:", file=sys.stderr)
                for problem in problems:
                    print(f"  {problem}", file=sys.stderr)
                return 1

            _print_snapshot("BEFORE", clubs, sources, show_counts)
            club_updates = _planned_club_updates(clubs)
            source_updates = _planned_source_updates(sources)

            print()
            print("Classifications:")
            for disposition in _DISPOSITIONS:
                source_note = disposition.keep_source_enabled_reason or (
                    f"disable source ids {list(disposition.source_ids_to_disable)}"
                )
                print(
                    f"  club {disposition.club_id}: {disposition.classification}; "
                    f"target type={disposition.target_club_type!r}; {source_note}"
                )

            print()
            print(f"Planned writes: {len(club_updates)} club updates, " f"{len(source_updates)} source updates.")
            if not club_updates and not source_updates:
                print("No changes needed (idempotent re-run).")
                return 0
            if dry_run:
                print("--dry-run: no DB write performed.")
                conn.rollback()
                return 0

            for disposition, target in club_updates:
                cur.execute(
                    """
                    UPDATE clubs
                    SET visible = %s,
                        club_type = %s,
                        address = %s,
                        description = %s
                    WHERE id = %s
                    """,
                    (
                        target["visible"],
                        target["club_type"],
                        target["address"],
                        target["description"],
                        disposition.club_id,
                    ),
                )

            for _, source_id, target in source_updates:
                cur.execute(
                    """
                    UPDATE scraping_sources
                    SET enabled = %s,
                        metadata = %s::jsonb,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (target["enabled"], json.dumps(target["metadata"]), source_id),
                )

            clubs_after, sources_after, _, show_counts_after = _fetch_rows(cur)
            _print_snapshot("AFTER", clubs_after, sources_after, show_counts_after)

            cur.execute("""
                SELECT id, name, address, visible, club_type
                FROM clubs
                WHERE address ILIKE '%Multiple venues%'
                   OR address ILIKE '%Production company office%'
                   OR address ILIKE '%Address disclosed after booking%'
                   OR address ILIKE '%Platform trigger%'
                ORDER BY id
                """)
            residual_synthetic = cur.fetchall()
            if residual_synthetic:
                print("ABORT: residual synthetic address rows remain:", file=sys.stderr)
                for row in residual_synthetic:
                    print(
                        f"  {row['id']} {row['name']!r} address={row['address']!r} "
                        f"visible={row['visible']} type={row['club_type']!r}",
                        file=sys.stderr,
                    )
                raise RuntimeError("residual synthetic address rows remain")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()
    return run(dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
