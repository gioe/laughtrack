#!/usr/bin/env python3
"""Discover candidate comedian tour source URLs with Brave Search.

This experimental script searches tour-intent queries for canonical comedians
with historical shows and reports likely tour source URLs. It is intentionally
read-only: dry-run mode is explicit in the output, and non-dry-run mode still
only reports candidates until a later task defines persistence semantics.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from psycopg2.extras import RealDictCursor

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from laughtrack.adapters.db import create_connection
from laughtrack.core.clients.brave.search import BraveSearchClient
from laughtrack.core.clients.google.custom_search import SearchResult
from laughtrack.foundation.infrastructure.logger.logger import Logger


_GET_TOUR_DISCOVERY_CANDIDATES = """
    SELECT c.uuid, c.name, c.total_shows
    FROM comedians c
    WHERE c.parent_comedian_id IS NULL
      AND c.total_shows > 0
      AND NULLIF(BTRIM(c.name), '') IS NOT NULL
      AND NOT EXISTS (
          SELECT 1
          FROM comedian_deny_list d
          WHERE LOWER(BTRIM(d.name)) = LOWER(BTRIM(c.name))
      )
"""

_ORDER_AND_LIMIT = """
    ORDER BY c.popularity DESC NULLS LAST, c.total_shows DESC NULLS LAST, c.name
    LIMIT %s
"""


@dataclass(frozen=True)
class TourDiscoveryCandidate:
    uuid: str
    name: str
    total_shows: int


@dataclass(frozen=True)
class TourSourceCandidate:
    comedian_uuid: str
    comedian_name: str
    url: str
    query: str
    rank: int
    source_type: str
    confidence: str
    title: str = ""
    snippet: str = ""


def build_tour_search_queries(comedian_name: str) -> list[str]:
    """Return the Brave queries used for one comedian."""
    return [
        f"{comedian_name} tour dates",
        f"{comedian_name} tickets upcoming shows",
        f"{comedian_name} upcoming shows",
        f"{comedian_name} Bandsintown",
        f"{comedian_name} Songkick",
    ]


def load_candidate_comedians(
    *,
    limit: Optional[int],
    comedian_name: Optional[str],
) -> list[TourDiscoveryCandidate]:
    """Load canonical, non-deny-listed comedians with historical shows."""
    query = _GET_TOUR_DISCOVERY_CANDIDATES
    params: list[object] = []

    if comedian_name:
        query += "      AND c.name ILIKE %s\n"
        params.append(f"%{comedian_name}%")

    query += _ORDER_AND_LIMIT
    params.append(limit if limit is not None else 25)

    conn = create_connection(autocommit=True)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, tuple(params))
            rows = cur.fetchall()
    finally:
        conn.close()

    return [
        TourDiscoveryCandidate(
            uuid=str(row["uuid"]),
            name=str(row["name"]),
            total_shows=int(row.get("total_shows") or 0),
        )
        for row in rows
    ]


def _source_type(url: str) -> str:
    hostname = (urlparse(url).hostname or "").lower().removeprefix("www.")
    if hostname.endswith("bandsintown.com"):
        return "bandsintown"
    if hostname.endswith("songkick.com"):
        return "songkick"
    if hostname.endswith(("ticketmaster.com", "eventbrite.com", "axs.com", "seatgeek.com", "livenation.com")):
        return "ticketing"
    return "official"


def _name_tokens(name: str) -> list[str]:
    return [token for token in name.lower().replace("-", " ").split() if len(token) > 1]


def _confidence(result: SearchResult, comedian_name: str, source_type: str) -> str:
    haystack = " ".join([result.title, result.snippet, result.link]).lower()
    token_hits = sum(1 for token in _name_tokens(comedian_name) if token in haystack)
    if source_type in {"bandsintown", "songkick"} and token_hits:
        return "high"
    if source_type == "official" and token_hits >= 2:
        return "high"
    if token_hits:
        return "medium"
    return "low"


def _candidate_from_result(
    *,
    comedian: TourDiscoveryCandidate,
    result: SearchResult,
    query: str,
    rank: int,
) -> Optional[TourSourceCandidate]:
    parsed = urlparse(result.link)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None

    source_type = _source_type(result.link)
    confidence = _confidence(result, comedian.name, source_type)
    if confidence == "low":
        return None

    return TourSourceCandidate(
        comedian_uuid=comedian.uuid,
        comedian_name=comedian.name,
        url=result.link,
        query=query,
        rank=rank,
        source_type=source_type,
        confidence=confidence,
        title=result.title,
        snippet=result.snippet,
    )


def _dedupe_candidates(candidates: list[TourSourceCandidate]) -> list[TourSourceCandidate]:
    seen: set[tuple[str, str]] = set()
    unique: list[TourSourceCandidate] = []
    for candidate in candidates:
        key = (candidate.comedian_uuid, candidate.url.rstrip("/"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique


def discover_tour_sources(
    *,
    limit: Optional[int],
    comedian_name: Optional[str],
    dry_run: bool,
) -> list[TourSourceCandidate]:
    """Search Brave for tour-source candidates and print a report."""
    client = BraveSearchClient()
    if not client.is_configured:
        Logger.error("Brave Search not configured - set BRAVE_SEARCH_API_KEY")
        return []

    candidates = load_candidate_comedians(limit=limit, comedian_name=comedian_name)
    discovered: list[TourSourceCandidate] = []

    for comedian in candidates:
        if client.queries_remaining <= 0:
            Logger.warn("Brave Search daily limit reached - stopping")
            break

        for query in build_tour_search_queries(comedian.name):
            if client.queries_remaining <= 0:
                break

            results = client.search(query, num_results=10)
            for rank, result in enumerate(results, start=1):
                candidate = _candidate_from_result(
                    comedian=comedian,
                    result=result,
                    query=query,
                    rank=rank,
                )
                if candidate:
                    discovered.append(candidate)

    discovered = _dedupe_candidates(discovered)
    print_tour_source_report(discovered, dry_run=dry_run)
    return discovered


def print_tour_source_report(candidates: list[TourSourceCandidate], *, dry_run: bool) -> None:
    mode = "DRY RUN" if dry_run else "REPORT ONLY"
    print(f"\n{mode} - {len(candidates)} candidate tour source URL(s)")
    print("=" * 72)

    if not candidates:
        print("No candidate tour source URLs found.")
        return

    for candidate in candidates:
        print(f"{candidate.comedian_name}: {candidate.url}")
        print(
            "  "
            f"query={candidate.query} "
            f"rank={candidate.rank} "
            f"source_type={candidate.source_type} "
            f"confidence={candidate.confidence}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Discover candidate comedian tour source URLs with Brave Search",
    )
    parser.add_argument("--limit", type=int, help="Maximum number of comedians to process")
    parser.add_argument("--comedian-name", type=str, help="Process comedians matching this name")
    parser.add_argument("--dry-run", action="store_true", help="Print candidate URLs without writing to the database")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show INFO-level logs")
    parser.add_argument("--debug", action="store_true", help="Show DEBUG-level logs")
    args = parser.parse_args()

    if args.debug:
        os.environ["LAUGHTRACK_LOG_CONSOLE_LEVEL"] = "DEBUG"
    elif args.verbose:
        current = os.environ.get("LAUGHTRACK_LOG_CONSOLE_LEVEL", "").upper()
        if current not in {"DEBUG", "INFO"}:
            os.environ["LAUGHTRACK_LOG_CONSOLE_LEVEL"] = "INFO"

    try:
        discover_tour_sources(
            limit=args.limit,
            comedian_name=args.comedian_name,
            dry_run=args.dry_run,
        )
    except KeyboardInterrupt:
        Logger.info("Operation cancelled")
        return 0
    except Exception as exc:
        Logger.error(f"Error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
