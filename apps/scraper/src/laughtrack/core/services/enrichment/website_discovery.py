"""Discover comedian websites via Google Custom Search.

Queries Google for '{name} comedian official website', filters out social media /
ticketing / reference sites, and writes the best candidate URL to comedian.website
with website_discovery_source='google_search'.

Prioritizes comedians by popularity (highest first, website IS NULL).
Respects Google Custom Search free tier (100 queries/day).
"""

from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urlparse

from laughtrack.core.clients.google.custom_search import (
    GoogleCustomSearchClient,
    SearchResult,
)
from laughtrack.core.data.db_connection import create_connection
from laughtrack.foundation.infrastructure.logger.logger import Logger


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
_GET_COMEDIANS_WITHOUT_WEBSITE = """
    SELECT uuid, name, popularity
    FROM comedians
    WHERE (website IS NULL OR website = '')
    ORDER BY popularity DESC NULLS LAST
"""

_GET_COMEDIANS_WITHOUT_WEBSITE_LIMITED = """
    SELECT uuid, name, popularity
    FROM comedians
    WHERE (website IS NULL OR website = '')
    ORDER BY popularity DESC NULLS LAST
    LIMIT %s
"""

_UPDATE_COMEDIAN_WEBSITE = """
    UPDATE comedians
    SET website = %s,
        website_discovery_source = %s
    WHERE uuid = %s
"""


def _pick_best_url(results: List[SearchResult], comedian_name: str) -> Optional[str]:
    """Select the best URL from search results.

    Filters out excluded domains and picks the first remaining result,
    which Google ranks by relevance.
    """
    for result in results:
        if GoogleCustomSearchClient.is_excluded_domain(result.link):
            continue

        # Basic sanity — must be a valid HTTP(S) URL
        parsed = urlparse(result.link)
        if parsed.scheme not in ("http", "https"):
            continue

        return result.link

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
    client = GoogleCustomSearchClient()

    if not client.is_configured:
        Logger.error("Google Custom Search not configured — set GOOGLE_CUSTOM_SEARCH_API_KEY and GOOGLE_CUSTOM_SEARCH_ENGINE_ID")
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
                        results.append(DiscoveryResult(
                            uuid=uuid, name=name, website=None,
                            skipped=True, reason="no search results",
                        ))
                        continue

                    best_url = _pick_best_url(search_results, name)

                    if not best_url:
                        results.append(DiscoveryResult(
                            uuid=uuid, name=name, website=None,
                            skipped=True, reason="all results excluded",
                        ))
                        Logger.debug(f"No suitable URL found for {name}")
                        continue

                    result = DiscoveryResult(uuid=uuid, name=name, website=best_url)
                    results.append(result)

                    if dry_run:
                        Logger.info(f"[DRY RUN] {name} → {best_url}")
                    else:
                        cur.execute(_UPDATE_COMEDIAN_WEBSITE, (best_url, "google_search", uuid))
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
