"""Discover comedian websites via web search APIs.

Queries a search provider for '{name} comedian official website', filters out
social media / ticketing / reference sites, and writes the best candidate URL
to comedian.website with website_discovery_source set to the provider name.

Prioritizes comedians by popularity (highest first, website IS NULL).
Supports multiple search providers (Brave, Google Custom Search).
"""

from dataclasses import dataclass
from typing import List, Optional, Protocol
from urllib.parse import urlparse

from laughtrack.core.clients.google.custom_search import (
    GoogleCustomSearchClient,
    SearchResult,
)
from laughtrack.infrastructure.database.connection import create_connection
from laughtrack.foundation.infrastructure.logger.logger import Logger


class SearchClient(Protocol):
    """Protocol for web search clients used by the discovery service."""

    @property
    def is_configured(self) -> bool: ...

    @property
    def queries_remaining(self) -> int: ...

    @property
    def source_name(self) -> str: ...

    def search(self, query: str, num_results: int = 10) -> List[SearchResult]: ...


@dataclass
class DiscoveryResult:
    """Result of a website discovery attempt for one comedian."""

    uuid: str
    name: str
    website: Optional[str]
    source: str = "google_search"
    skipped: bool = False
    reason: str = ""


# SQL: get comedians without websites, ordered by popularity DESC
# Excludes comedians already marked as 'none_found' to avoid re-querying
_GET_COMEDIANS_WITHOUT_WEBSITE = """
    SELECT uuid, name, popularity
    FROM comedians
    WHERE (website IS NULL OR website = '')
      AND (website_discovery_source IS NULL OR website_discovery_source != 'none_found')
    ORDER BY popularity DESC NULLS LAST
"""

_GET_COMEDIANS_WITHOUT_WEBSITE_LIMITED = """
    SELECT uuid, name, popularity
    FROM comedians
    WHERE (website IS NULL OR website = '')
      AND (website_discovery_source IS NULL OR website_discovery_source != 'none_found')
    ORDER BY popularity DESC NULLS LAST
    LIMIT %s
"""

_UPDATE_COMEDIAN_WEBSITE = """
    UPDATE comedians
    SET website = %s,
        website_discovery_source = %s
    WHERE uuid = %s
"""

_MARK_NO_WEBSITE_FOUND = """
    UPDATE comedians
    SET website_discovery_source = 'none_found'
    WHERE uuid = %s
"""


def _name_tokens(name: str) -> List[str]:
    """Split a name into lowercase tokens for fuzzy matching."""
    return [t for t in name.lower().split() if len(t) > 1]


def _name_in_text(tokens: List[str], text: str) -> bool:
    """Check if all name tokens appear in text (case-insensitive)."""
    text_lower = text.lower()
    return all(t in text_lower for t in tokens)


def _name_in_domain(tokens: List[str], hostname: str) -> bool:
    """Check if name tokens appear in the domain (stripped of separators)."""
    # e.g. "mikesmithcomedy.com" → "mikesmithcomedy"
    domain_base = hostname.lower().removeprefix("www.").split(".")[0]
    # Check joined name: "mikesmith" in "mikesmithcomedy"
    joined = "".join(tokens)
    if joined in domain_base:
        return True
    # Check last name at minimum (more common in domains)
    if len(tokens) >= 2 and tokens[-1] in domain_base:
        return True
    return False


def _score_result(result: SearchResult, name_tokens: List[str]) -> int:
    """Score a search result by confidence that it belongs to the comedian.

    Returns 0 for low confidence (no name signal), higher is better.
    """
    score = 0
    hostname = urlparse(result.link).hostname or ""

    if _name_in_domain(name_tokens, hostname):
        score += 3
    if _name_in_text(name_tokens, result.title):
        score += 2
    if _name_in_text(name_tokens, result.snippet):
        score += 1

    return score


def _pick_best_url(results: List[SearchResult], comedian_name: str) -> Optional[str]:
    """Select the best URL from search results using a confidence heuristic.

    Scores each result by whether the comedian's name appears in the domain,
    title, or snippet. Returns the highest-scoring result above the confidence
    threshold, or None if no result is confident enough.
    """
    tokens = _name_tokens(comedian_name)
    if not tokens:
        return None

    best_url: Optional[str] = None
    best_score = 0

    for result in results:
        if GoogleCustomSearchClient.is_excluded_domain(result.link):
            continue

        parsed = urlparse(result.link)
        if parsed.scheme not in ("http", "https"):
            continue

        score = _score_result(result, tokens)
        if score > best_score:
            best_score = score
            best_url = result.link

    if best_score == 0:
        Logger.info(f"No confident match for '{comedian_name}' — all results scored 0")
        return None

    return best_url


def _create_search_client() -> Optional[SearchClient]:
    """Create the best available search client.

    Tries Brave first (preferred), falls back to Google Custom Search.
    Returns None if no client is configured.
    """
    try:
        from laughtrack.core.clients.brave.search import BraveSearchClient
        brave = BraveSearchClient()
        if brave.is_configured:
            Logger.info(f"Using Brave Search (daily limit: {brave._daily_limit})")
            return brave
    except ImportError:
        pass

    google = GoogleCustomSearchClient()
    if google.is_configured:
        Logger.info("Using Google Custom Search")
        return google

    return None


def discover_websites(
    limit: Optional[int] = None,
    dry_run: bool = False,
    comedian_name: Optional[str] = None,
) -> List[DiscoveryResult]:
    """Discover websites for comedians without one.

    Args:
        limit: Maximum number of comedians to process. Defaults to the
               remaining daily quota.
        dry_run: If True, search but don't write to the database.
        comedian_name: If set, only process this comedian (partial match).

    Returns:
        List of DiscoveryResult for each comedian processed.
    """
    client = _create_search_client()

    if client is None:
        Logger.error("No search provider configured — set BRAVE_SEARCH_API_KEY or GOOGLE_CUSTOM_SEARCH_API_KEY + GOOGLE_CUSTOM_SEARCH_ENGINE_ID")
        return []

    conn = create_connection(autocommit=False)
    results: List[DiscoveryResult] = []

    try:
        with conn.cursor() as cur:
            if comedian_name:
                cur.execute(_GET_COMEDIANS_WITHOUT_WEBSITE_LIMITED, (1000,))
                rows = [
                    row for row in cur.fetchall()
                    if comedian_name.lower() in row[1].lower()
                ]
            else:
                effective_limit = limit if limit else client.queries_remaining
                cur.execute(_GET_COMEDIANS_WITHOUT_WEBSITE_LIMITED, (effective_limit,))
                rows = cur.fetchall()

            Logger.info(f"Found {len(rows)} comedians without websites to process")

            for uuid, name, popularity in rows:
                if client.queries_remaining <= 0:
                    Logger.warn("Daily query limit reached — stopping")
                    break

                try:
                    search_query = f"{name} comedian official website"
                    Logger.debug(f"Searching: {search_query}")

                    search_results = client.search(search_query)

                    if not search_results:
                        if not dry_run:
                            cur.execute(_MARK_NO_WEBSITE_FOUND, (uuid,))
                            conn.commit()
                        results.append(DiscoveryResult(
                            uuid=uuid, name=name, website=None,
                            skipped=True, reason="no search results",
                        ))
                        Logger.info(f"No search results for {name} — marked as none_found")
                        continue

                    best_url = _pick_best_url(search_results, name)

                    if not best_url:
                        if not dry_run:
                            cur.execute(_MARK_NO_WEBSITE_FOUND, (uuid,))
                            conn.commit()
                        results.append(DiscoveryResult(
                            uuid=uuid, name=name, website=None,
                            skipped=True, reason="no confident match",
                        ))
                        Logger.info(f"No suitable URL found for {name} — marked as none_found")
                        continue

                    result = DiscoveryResult(uuid=uuid, name=name, website=best_url, source=client.source_name)
                    results.append(result)

                    if dry_run:
                        Logger.info(f"[DRY RUN] {name} → {best_url}")
                    else:
                        cur.execute(_UPDATE_COMEDIAN_WEBSITE, (best_url, client.source_name, uuid))
                        conn.commit()
                        Logger.info(f"Updated {name} → {best_url}")

                except Exception as e:
                    Logger.warn(f"Failed to process comedian {name}: {e}")
                    results.append(DiscoveryResult(
                        uuid=uuid, name=name, website=None,
                        skipped=True, reason=f"error: {e}",
                    ))

    except Exception as e:
        Logger.error(f"Website discovery failed: {e}")
    finally:
        conn.close()

    found = sum(1 for r in results if r.website)
    skipped = sum(1 for r in results if r.skipped)
    Logger.info(f"Discovery complete: {found} websites found, {skipped} skipped, {client.queries_remaining} queries remaining")

    return results
