#!/usr/bin/env python3
"""Discover candidate comedian tour source URLs with Brave Search.

This experimental script searches tour-intent queries for canonical comedians
with historical shows and reports likely tour source URLs. It is intentionally
read-only: dry-run mode is explicit in the output, and non-dry-run mode still
only reports candidates until a later task defines persistence semantics.
"""

from __future__ import annotations

import argparse
import json
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


TICKETING_DOMAINS = (
    "ticketmaster.com",
    "eventbrite.com",
    "axs.com",
    "seatgeek.com",
    "livenation.com",
    "ticketweb.com",
    "tixr.com",
    "dice.fm",
    "etix.com",
    "showclix.com",
    "ticketleap.com",
    "ticketsauce.com",
    "ticketspice.com",
)
AGENCY_DOMAINS = (
    "caa.com",
    "wmeagency.com",
    "unitedtalent.com",
    "icmpartners.com",
    "gersh.com",
    "apa-agency.com",
    "levitytalent.com",
    "33andwest.com",
)
SOCIAL_LINK_BIO_DOMAINS = (
    "instagram.com",
    "tiktok.com",
    "facebook.com",
    "x.com",
    "twitter.com",
    "youtube.com",
    "linktr.ee",
    "beacons.ai",
    "bio.site",
    "hoo.be",
    "solo.to",
    "komi.io",
)
TOUR_PATH_TERMS = ("tour", "date", "show", "event", "ticket", "calendar", "schedule")


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

_GET_TOUR_SOURCE_COVERAGE = """
    WITH canonical AS (
        SELECT
            c.uuid,
            c.name,
            c.total_shows,
            c.website,
            c.website_scraping_url,
            c.website_scrape_strategy,
            c.bandsintown_id,
            c.songkick_id,
            EXISTS (
                SELECT 1
                FROM comedian_deny_list d
                WHERE LOWER(BTRIM(d.name)) = LOWER(BTRIM(c.name))
            ) AS is_denied
        FROM comedians c
        WHERE c.parent_comedian_id IS NULL
          AND NULLIF(BTRIM(c.name), '') IS NOT NULL
    )
    SELECT
        COUNT(*) AS canonical_count,
        COUNT(*) FILTER (WHERE NOT is_denied) AS non_deny_listed_count,
        COUNT(*) FILTER (WHERE NOT is_denied AND total_shows > 0) AS historical_show_count,
        COUNT(*) FILTER (
            WHERE NOT is_denied
              AND NULLIF(BTRIM(COALESCE(website, '')), '') IS NOT NULL
        ) AS website_count,
        COUNT(*) FILTER (
            WHERE NOT is_denied
              AND NULLIF(BTRIM(COALESCE(website_scraping_url, '')), '') IS NOT NULL
        ) AS scraping_url_count,
        COUNT(*) FILTER (
            WHERE NOT is_denied
              AND NULLIF(BTRIM(COALESCE(website_scrape_strategy, '')), '') IS NOT NULL
              AND website_scrape_strategy NOT IN ('none', 'json_ld_empty')
        ) AS event_bearing_strategy_count,
        COUNT(*) FILTER (
            WHERE NOT is_denied
              AND NULLIF(BTRIM(COALESCE(bandsintown_id, '')), '') IS NOT NULL
        ) AS bandsintown_id_count,
        COUNT(*) FILTER (
            WHERE NOT is_denied
              AND NULLIF(BTRIM(COALESCE(songkick_id, '')), '') IS NOT NULL
        ) AS songkick_id_count,
        COUNT(*) FILTER (
            WHERE NOT is_denied
              AND (
                  NULLIF(BTRIM(COALESCE(bandsintown_id, '')), '') IS NOT NULL
                  OR NULLIF(BTRIM(COALESCE(songkick_id, '')), '') IS NOT NULL
              )
        ) AS tour_id_count
    FROM canonical
"""


@dataclass(frozen=True)
class TourDiscoveryCandidate:
    uuid: str
    name: str
    total_shows: int


@dataclass(frozen=True)
class TourSourceCoverageMetrics:
    canonical_count: int
    non_deny_listed_count: int
    historical_show_count: int
    website_count: int
    scraping_url_count: int
    event_bearing_strategy_count: int
    bandsintown_id_count: int
    songkick_id_count: int
    tour_id_count: int
    candidate_source_count: int = 0
    candidate_source_comedian_count: int = 0
    candidate_bandsintown_source_count: int = 0
    candidate_songkick_source_count: int = 0
    candidate_official_source_count: int = 0
    candidate_ticketing_source_count: int = 0

    @classmethod
    def from_mapping(cls, mapping: dict[str, object]) -> "TourSourceCoverageMetrics":
        return cls(**{field: int(mapping.get(field) or 0) for field in cls.__dataclass_fields__})

    def to_dict(self) -> dict[str, int]:
        return {field: int(getattr(self, field)) for field in self.__dataclass_fields__}

    def with_candidates(self, candidates: list["TourSourceCandidate"]) -> "TourSourceCoverageMetrics":
        counts = self.to_dict()
        counts.update(
            {
                "candidate_source_count": len(candidates),
                "candidate_source_comedian_count": len({candidate.comedian_uuid for candidate in candidates}),
                "candidate_bandsintown_source_count": sum(1 for c in candidates if c.source_type == "bandsintown"),
                "candidate_songkick_source_count": sum(1 for c in candidates if c.source_type == "songkick"),
                "candidate_official_source_count": sum(1 for c in candidates if c.source_type == "official_tour"),
                "candidate_ticketing_source_count": sum(1 for c in candidates if c.source_type == "ticketing"),
            }
        )
        return TourSourceCoverageMetrics.from_mapping(counts)


@dataclass(frozen=True)
class TourSourceEvidence:
    matched_domain: str
    name_match: str
    query_intent: str
    url_path: str
    snippet: str = ""


@dataclass(frozen=True)
class TourSourceCandidate:
    comedian_uuid: str
    comedian_name: str
    url: str
    query: str
    rank: int
    source_type: str
    confidence: str
    evidence: TourSourceEvidence
    is_scraping_url_candidate: bool
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


def load_tour_source_coverage_metrics() -> TourSourceCoverageMetrics:
    """Return current comedian tour-source discovery coverage counts."""
    conn = create_connection(autocommit=True)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(_GET_TOUR_SOURCE_COVERAGE)
            row = cur.fetchone()
    finally:
        conn.close()

    return TourSourceCoverageMetrics.from_mapping(dict(row or {}))


def _hostname(url: str) -> str:
    return (urlparse(url).hostname or "").lower().removeprefix("www.")


def _domain_matches(hostname: str, domains: tuple[str, ...]) -> bool:
    return any(hostname == domain or hostname.endswith(f".{domain}") for domain in domains)


def _query_intent(query: str) -> str:
    normalized = query.lower()
    if "bandsintown" in normalized:
        return "bandsintown"
    if "songkick" in normalized:
        return "songkick"
    if "ticket" in normalized:
        return "tickets"
    if any(term in normalized for term in ("tour", "upcoming", "show", "date")):
        return "tour"
    return "unknown"


def _name_match(result: SearchResult, comedian_name: str) -> str:
    parsed = urlparse(result.link)
    haystack = " ".join([result.title, result.snippet, parsed.path]).lower()
    tokens = _name_tokens(comedian_name)
    if not tokens:
        return "none"
    token_hits = sum(1 for token in tokens if token in haystack)
    if token_hits == len(tokens):
        return "all"
    if token_hits:
        return "partial"
    return "none"


def _has_tour_signal(result: SearchResult) -> bool:
    parsed = urlparse(result.link)
    path = parsed.path.lower()
    text = " ".join([result.title, result.snippet]).lower()
    return any(term in path or term in text for term in TOUR_PATH_TERMS)


def _source_type(result: SearchResult) -> str:
    url = result.link
    hostname = (urlparse(url).hostname or "").lower().removeprefix("www.")
    if hostname.endswith("bandsintown.com"):
        return "bandsintown"
    if hostname.endswith("songkick.com"):
        return "songkick"
    if _domain_matches(hostname, TICKETING_DOMAINS):
        return "ticketing"
    if _domain_matches(hostname, AGENCY_DOMAINS):
        return "agency"
    if _domain_matches(hostname, SOCIAL_LINK_BIO_DOMAINS):
        return "social_link_bio"
    if _has_tour_signal(result):
        return "official_tour"
    return "unknown"


def _name_tokens(name: str) -> list[str]:
    return [token for token in name.lower().replace("-", " ").split() if len(token) > 1]


def _confidence(result: SearchResult, comedian_name: str, source_type: str) -> str:
    parsed = urlparse(result.link)
    haystack = " ".join([result.title, result.snippet, parsed.path]).lower()
    token_hits = sum(1 for token in _name_tokens(comedian_name) if token in haystack)
    if source_type in {"bandsintown", "songkick"} and token_hits:
        return "high"
    if source_type == "official_tour" and token_hits >= 2:
        return "high"
    if token_hits:
        return "medium"
    return "low"


def _is_scraping_url_candidate(source_type: str, confidence: str) -> bool:
    if confidence == "low":
        return False
    return source_type in {"bandsintown", "songkick", "official_tour"}


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

    source_type = _source_type(result)
    name_match = _name_match(result, comedian.name)
    if source_type == "official_tour" and name_match == "none":
        source_type = "unknown"
    confidence = _confidence(result, comedian.name, source_type)
    evidence = TourSourceEvidence(
        matched_domain=_hostname(result.link),
        name_match=name_match,
        query_intent=_query_intent(query),
        url_path=parsed.path or "/",
        snippet=result.snippet,
    )

    return TourSourceCandidate(
        comedian_uuid=comedian.uuid,
        comedian_name=comedian.name,
        url=result.link,
        query=query,
        rank=rank,
        source_type=source_type,
        confidence=confidence,
        evidence=evidence,
        is_scraping_url_candidate=_is_scraping_url_candidate(source_type, confidence),
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


def compare_coverage_metrics(
    before: TourSourceCoverageMetrics,
    after: TourSourceCoverageMetrics,
) -> dict[str, int]:
    """Return field-by-field deltas between two coverage snapshots."""
    return {
        field: after.to_dict()[field] - before.to_dict()[field]
        for field in after.__dataclass_fields__
    }


def load_coverage_snapshot(path: Path) -> TourSourceCoverageMetrics:
    return TourSourceCoverageMetrics.from_mapping(json.loads(path.read_text()))


def write_coverage_snapshot(path: Path, metrics: TourSourceCoverageMetrics) -> None:
    path.write_text(json.dumps(metrics.to_dict(), indent=2, sort_keys=True) + "\n")


def print_tour_source_coverage_report(
    metrics: TourSourceCoverageMetrics,
    *,
    previous: Optional[TourSourceCoverageMetrics] = None,
) -> None:
    print("\nTour-source discovery coverage")
    print("=" * 72)

    rows = [
        ("canonical_count", "Canonical comedians", metrics.canonical_count),
        ("non_deny_listed_count", "Non-deny-listed comedians", metrics.non_deny_listed_count),
        ("historical_show_count", "Comedians with historical shows", metrics.historical_show_count),
        ("website_count", "Comedians with websites", metrics.website_count),
        ("scraping_url_count", "Comedians with scraping URLs", metrics.scraping_url_count),
        (
            "event_bearing_strategy_count",
            "Comedians with event-bearing strategies",
            metrics.event_bearing_strategy_count,
        ),
        ("bandsintown_id_count", "Comedians with Bandsintown IDs", metrics.bandsintown_id_count),
        ("songkick_id_count", "Comedians with Songkick IDs", metrics.songkick_id_count),
        ("tour_id_count", "Comedians with any tour ID", metrics.tour_id_count),
        ("candidate_source_count", "Candidate source URLs found in this run", metrics.candidate_source_count),
        (
            "candidate_source_comedian_count",
            "Candidate-source comedians in this run",
            metrics.candidate_source_comedian_count,
        ),
        (
            "candidate_bandsintown_source_count",
            "Candidate Bandsintown URLs",
            metrics.candidate_bandsintown_source_count,
        ),
        ("candidate_songkick_source_count", "Candidate Songkick URLs", metrics.candidate_songkick_source_count),
        ("candidate_official_source_count", "Candidate official URLs", metrics.candidate_official_source_count),
        ("candidate_ticketing_source_count", "Candidate ticketing URLs", metrics.candidate_ticketing_source_count),
    ]
    deltas = compare_coverage_metrics(previous, metrics) if previous else {}

    for field, label, value in rows:
        delta = deltas.get(field)
        suffix = f" ({delta:+d})" if previous and delta else ""
        print(f"{label}: {value}{suffix}")


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
            f"confidence={candidate.confidence} "
            f"scraping_url_candidate={str(candidate.is_scraping_url_candidate).lower()}"
        )
        print(
            "  "
            f"evidence=domain:{candidate.evidence.matched_domain} "
            f"name:{candidate.evidence.name_match} "
            f"intent:{candidate.evidence.query_intent} "
            f"path:{candidate.evidence.url_path}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Discover candidate comedian tour source URLs with Brave Search",
    )
    parser.add_argument("--limit", type=int, help="Maximum number of comedians to process")
    parser.add_argument("--comedian-name", type=str, help="Process comedians matching this name")
    parser.add_argument("--dry-run", action="store_true", help="Print candidate URLs without writing to the database")
    parser.add_argument("--coverage-only", action="store_true", help="Print current coverage metrics without Brave discovery")
    parser.add_argument("--coverage-report", action="store_true", help="Print coverage metrics alongside candidate URLs")
    parser.add_argument("--coverage-json", type=Path, help="Write coverage metrics to a JSON snapshot")
    parser.add_argument("--compare-coverage-json", type=Path, help="Compare coverage metrics against a prior JSON snapshot")
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
        should_report_coverage = (
            args.coverage_only
            or args.coverage_report
            or args.compare_coverage_json
            or args.coverage_json
        )
        previous = load_coverage_snapshot(args.compare_coverage_json) if args.compare_coverage_json else None
        if args.coverage_only:
            metrics = load_tour_source_coverage_metrics()
        else:
            candidates = discover_tour_sources(
                limit=args.limit,
                comedian_name=args.comedian_name,
                dry_run=args.dry_run,
            )
            metrics = (
                load_tour_source_coverage_metrics().with_candidates(candidates)
                if should_report_coverage
                else None
            )

        if should_report_coverage and metrics is not None:
            print_tour_source_coverage_report(metrics, previous=previous)

        if args.coverage_json and metrics is not None:
            write_coverage_snapshot(args.coverage_json, metrics)
    except KeyboardInterrupt:
        Logger.info("Operation cancelled")
        return 0
    except Exception as exc:
        Logger.error(f"Error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
