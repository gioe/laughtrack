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
    discovery_attempt_status,
    discover_candidates_for_comedian,
    load_active_deny_list,
    record_discovery_attempt,
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
    attempted: int
    candidates: int
    written: int
    failed: int
    blocked: int
    stopped_early: bool = False


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
    retry_attempted: bool = False,
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
    if not retry_attempted:
        filters.append(
            """AND NOT EXISTS (
          SELECT 1
          FROM comedian_podcast_discovery_attempts a
          WHERE a.comedian_id = c.id
            AND a.source = 'itunes'
            AND a.status IN ('candidates_found', 'no_candidates')
      )"""
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
    retry_attempted: bool,
    max_consecutive_403: int,
    progress_interval: int,
) -> SearchSummary:
    if dry_run == confirm:
        raise ValueError("choose exactly one of dry_run or confirm")

    _load_env_defaults()
    comedians = load_target_comedians(
        comedian_ids=comedian_ids,
        comedian_names=comedian_names,
        limit=limit,
        include_reviewed=include_reviewed,
        retry_attempted=retry_attempted,
    )
    if not comedians:
        print("No comedians matched.")
        return SearchSummary(processed=0, attempted=0, candidates=0, written=0, failed=0, blocked=0)

    with get_connection(autocommit=False) as conn:
        before = load_snapshot(conn)
        _print_snapshot("BEFORE", before)
        with conn.cursor() as cur:
            deny_keys, deny_urls = load_active_deny_list(cur)

    processed = 0
    attempted = 0
    candidate_count = 0
    written = 0
    failed = 0
    blocked = 0
    planned = 0
    consecutive_403 = 0
    stopped_early = False

    for comedian in comedians:
        processed += 1
        attempted += 1
        candidates, failures = discover_candidates_for_comedian(
            comedian,
            max_results=max_results,
            country=country,
            request_delay=request_delay,
        )
        candidates = [candidate for candidate in candidates if candidate.confidence >= min_confidence]
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

        candidate_count += len(eligible_candidates)
        failure_count = len(failures)
        blocked_count = sum(1 for failure in failures if failure.status_code == 403)
        failed += failure_count
        blocked += blocked_count
        if blocked_count and not eligible_candidates:
            consecutive_403 += 1
        else:
            consecutive_403 = 0

        last_error = failures[-1].message if failures else None
        status = discovery_attempt_status(len(eligible_candidates), failure_count, blocked_count)
        evidence = {
            "comedian_name": comedian.name,
            "aliases": comedian.aliases,
            "max_results": max_results,
            "country": country,
            "min_confidence": min_confidence,
            "failures": [failure.__dict__ for failure in failures],
        }

        if dry_run:
            for candidate in eligible_candidates:
                _print_candidate(candidate)
            planned += len(eligible_candidates)
        else:
            with get_connection(autocommit=False) as conn:
                try:
                    record_discovery_attempt(
                        conn,
                        comedian,
                        status=status,
                        candidates_found=len(eligible_candidates),
                        error_count=failure_count,
                        last_error=last_error,
                        evidence=evidence,
                    )
                    for candidate in eligible_candidates:
                        result = upsert_candidate_with_conn(conn, candidate)
                        written += 1
                        Logger.info(
                            f"[itunes-podcasts] {result.action} comedian_id={candidate.comedian_id} "
                            f"podcast_id={result.podcast_id} collection_id={candidate.source_podcast_id}"
                        )
                    conn.commit()
                except Exception:
                    conn.rollback()
                    raise

        if progress_interval > 0 and (processed % progress_interval == 0 or processed == len(comedians)):
            print(
                f"progress: {processed}/{len(comedians)} processed, {candidate_count} candidates, "
                f"{written if not dry_run else planned} {'written' if not dry_run else 'planned'}, "
                f"{failed} failures, {blocked} blocked"
            )

        if max_consecutive_403 > 0 and consecutive_403 >= max_consecutive_403:
            stopped_early = True
            print(f"stopping early after {consecutive_403} consecutive iTunes 403 failures")
            break

    with get_connection(autocommit=False) as conn:
        after = before if dry_run else load_snapshot(conn)
        print()
        _print_snapshot("AFTER", after)

    if dry_run:
        print(f"\n--dry-run: {planned} writes planned (none applied).")

    return SearchSummary(
        processed=processed,
        attempted=attempted,
        candidates=candidate_count,
        written=written,
        failed=failed,
        blocked=blocked,
        stopped_early=stopped_early,
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
    parser.add_argument(
        "--request-delay",
        type=float,
        default=3.2,
        help="Delay between iTunes requests; Apple documents roughly 20 Search API calls/minute",
    )
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
    parser.add_argument(
        "--retry-attempted",
        action="store_true",
        help="Include comedians already attempted by this iTunes discovery backfill",
    )
    parser.add_argument(
        "--max-consecutive-403",
        type=int,
        default=5,
        help="Stop early after this many consecutive comedians hit iTunes 403 failures; 0 disables",
    )
    parser.add_argument(
        "--progress-interval",
        type=int,
        default=25,
        help="Print progress every N comedians; 0 disables progress output",
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
            retry_attempted=args.retry_attempted,
            max_consecutive_403=args.max_consecutive_403,
            progress_interval=args.progress_interval,
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
