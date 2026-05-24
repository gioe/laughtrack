#!/usr/bin/env python3
"""Discover comedian podcast candidates from Apple's iTunes podcast search."""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from dotenv import dotenv_values

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from laughtrack.adapters.db import get_connection
from laughtrack.core.itunes_podcast_discovery import (
    ItunesPodcastCandidate,
    PodcastDiscoveryComedian,
    candidate_is_denied,
    discover_candidates_for_comedians,
    load_active_deny_list,
    upsert_candidate_with_conn,
)
from laughtrack.foundation.infrastructure.logger.logger import Logger


@dataclass(frozen=True)
class PodcastSnapshot:
    itunes_podcasts: int
    itunes_candidate_reviews: int


@dataclass(frozen=True)
class SearchSummary:
    processed: int
    candidates: int
    written: int
    failed: int


_GET_DISCOVERY_COMEDIANS_SQL = """
    SELECT
        c.id,
        c.name,
        COALESCE(
            array_remove(array_agg(a.name ORDER BY a.name), NULL),
            ARRAY[]::text[]
        ) AS aliases
    FROM comedians c
    LEFT JOIN comedians a ON a.parent_comedian_id = c.id
        AND NULLIF(BTRIM(a.name), '') IS NOT NULL
    WHERE c.parent_comedian_id IS NULL
      AND NULLIF(BTRIM(c.name), '') IS NOT NULL
      AND NOT EXISTS (
          SELECT 1
          FROM comedian_deny_list d
          WHERE LOWER(BTRIM(d.name)) = LOWER(BTRIM(c.name))
      )
      {extra_filter}
    GROUP BY c.id, c.name
    ORDER BY c.popularity DESC NULLS LAST, c.total_shows DESC NULLS LAST, c.id
"""

_GET_SNAPSHOT_SQL = """
    SELECT
        COUNT(*) FILTER (WHERE p.source = 'itunes') AS itunes_podcasts,
        (
            SELECT COUNT(*)
            FROM podcast_candidate_reviews r
            WHERE r.source = 'itunes'
        ) AS itunes_candidate_reviews
    FROM podcasts p
"""


def _load_env_defaults(path: Path = Path(".env")) -> None:
    for key, value in dotenv_values(path).items():
        if value:
            # iTunes search is public, but this keeps DB env behavior aligned with sibling scripts.
            os.environ.setdefault(key, value)


def load_target_comedians(
    *,
    comedian_ids: Optional[list[int]],
    comedian_names: Optional[list[str]],
    limit: Optional[int],
    include_reviewed: bool,
) -> list[PodcastDiscoveryComedian]:
    filters: list[str] = []
    params: list[Any] = []
    if comedian_ids:
        filters.append("AND c.id = ANY(%s::int[])")
        params.append(comedian_ids)
    if comedian_names:
        filters.append("AND c.name = ANY(%s::text[])")
        params.append(comedian_names)
    if not include_reviewed:
        filters.extend(
            [
                """AND NOT EXISTS (
          SELECT 1
          FROM comedian_podcasts cp
          WHERE cp.comedian_id = c.id
            AND cp.review_status = 'accepted'
      )""",
                """AND NOT EXISTS (
          SELECT 1
          FROM podcast_candidate_reviews r
          WHERE r.comedian_id = c.id
      )""",
            ]
        )

    sql = _GET_DISCOVERY_COMEDIANS_SQL.format(extra_filter="\n      ".join(filters))
    if limit:
        sql += "\n    LIMIT %s"
        params.append(int(limit))

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(params) if params else None)
            return [PodcastDiscoveryComedian(int(row[0]), str(row[1]), list(row[2] or [])) for row in cur.fetchall()]


def load_snapshot(conn: Any) -> PodcastSnapshot:
    with conn.cursor() as cur:
        cur.execute(_GET_SNAPSHOT_SQL)
        row = cur.fetchone() or (0, 0)
    return PodcastSnapshot(itunes_podcasts=int(row[0] or 0), itunes_candidate_reviews=int(row[1] or 0))


def _print_snapshot(label: str, snapshot: PodcastSnapshot) -> None:
    print(f"=== {label} ===")
    print(f"itunes_podcasts: {snapshot.itunes_podcasts}")
    print(f"itunes_candidate_reviews: {snapshot.itunes_candidate_reviews}")


def _print_candidate(candidate: ItunesPodcastCandidate) -> None:
    print(
        f"  candidate comedian_id={candidate.comedian_id} podcast={candidate.title!r} "
        f"author={candidate.author_name!r} confidence={candidate.confidence:.2f} "
        f"band={candidate.evidence.get('confidence_band')} collection_id={candidate.source_podcast_id} "
        f"feed_url={candidate.feed_url}"
    )


def search_itunes_podcasts(
    *,
    dry_run: bool,
    confirm: bool,
    limit: Optional[int],
    comedian_ids: Optional[list[int]],
    comedian_names: Optional[list[str]],
    max_results: int,
    country: str,
    request_delay: float,
    include_reviewed: bool,
    min_confidence: float,
) -> SearchSummary:
    if dry_run == confirm:
        raise ValueError("choose exactly one of dry_run or confirm")

    _load_env_defaults()
    comedians = load_target_comedians(
        comedian_ids=comedian_ids,
        comedian_names=comedian_names,
        limit=limit,
        include_reviewed=include_reviewed,
    )
    if not comedians:
        print("No comedians matched.")
        return SearchSummary(processed=0, candidates=0, written=0, failed=0)

    candidates, failed = discover_candidates_for_comedians(
        comedians,
        max_results=max_results,
        country=country,
        request_delay=request_delay,
    )
    candidates = [candidate for candidate in candidates if candidate.confidence >= min_confidence]

    with get_connection(autocommit=False) as conn:
        before = load_snapshot(conn)
        _print_snapshot("BEFORE", before)
        written = 0
        try:
            with conn.cursor() as cur:
                deny_keys, deny_urls = load_active_deny_list(cur)
            eligible_candidates = []
            for candidate in candidates:
                denied = candidate_is_denied(candidate, deny_keys, deny_urls)
                if denied:
                    Logger.info(
                        f"[itunes-podcasts] skipping deny-listed feed for comedian "
                        f"{candidate.comedian_id} collection_id={candidate.source_podcast_id} "
                        f"feed_url={candidate.feed_url}"
                    )
                    continue
                eligible_candidates.append(candidate)

            for candidate in eligible_candidates:
                if dry_run:
                    _print_candidate(candidate)
                    continue
                result = upsert_candidate_with_conn(conn, candidate)
                written += 1
                Logger.info(
                    f"[itunes-podcasts] {result.action} comedian_id={candidate.comedian_id} "
                    f"podcast_id={result.podcast_id} collection_id={candidate.source_podcast_id}"
                )

            if dry_run:
                print(f"\n--dry-run: {len(eligible_candidates)} writes planned (none applied).")
            else:
                conn.commit()
        except Exception:
            if not dry_run:
                conn.rollback()
            raise

        after = before if dry_run else load_snapshot(conn)
        print()
        _print_snapshot("AFTER", after)

    return SearchSummary(
        processed=len(comedians),
        candidates=len(eligible_candidates),
        written=written,
        failed=failed,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Discover comedian podcast candidates from Apple's iTunes podcast search",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Search and print planned writes without changing DB")
    mode.add_argument("--confirm", action="store_true", help="Write podcasts and podcast_candidate_reviews rows")
    parser.add_argument("--limit", type=int, default=100, help="Max canonical comedians to process")
    parser.add_argument("--comedian-ids", type=int, nargs="*", default=None)
    parser.add_argument("--comedian-names", nargs="*", default=None)
    parser.add_argument("--max-results", type=int, default=10, help="Max iTunes results per search term")
    parser.add_argument("--country", default="US", help="iTunes storefront country")
    parser.add_argument("--request-delay", type=float, default=0.25, help="Delay between iTunes requests")
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.8,
        help="Only write candidates at or above this confidence score",
    )
    parser.add_argument(
        "--include-reviewed",
        action="store_true",
        help="Include comedians that already have accepted podcast links or review history",
    )
    args = parser.parse_args()

    if args.dry_run == args.confirm:
        parser.error("choose exactly one of --dry-run or --confirm")

    try:
        summary = search_itunes_podcasts(
            dry_run=args.dry_run,
            confirm=args.confirm,
            limit=args.limit,
            comedian_ids=args.comedian_ids,
            comedian_names=args.comedian_names,
            max_results=args.max_results,
            country=args.country,
            request_delay=args.request_delay,
            include_reviewed=args.include_reviewed,
            min_confidence=args.min_confidence,
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
