"""Startup validation for scraper configuration.

Logs warnings for clubs that are missing a scraper key or whose key does not
match any discovered scraper implementation. Intended to be called once before
batch scraping begins.
"""

from __future__ import annotations

from typing import Iterable, List, Tuple

from laughtrack.app.scraper_resolver import ScraperResolver
from laughtrack.foundation.infrastructure.logger.logger import Logger


def validate_scraper_keys_for_clubs(clubs: Iterable) -> None:
    """Validate that each enabled scraping source resolves to a scraper class.

    Iterates every ``club.scraping_sources`` row with ``enabled=True`` (not just
    the primary) so a fallback source whose ``scraper_key`` was just folded onto
    a generic via migration but whose code never landed (the failure mode that
    triggers TASK-2097-style audits) gets flagged at startup, before nine clubs
    silently emit zero shows for a nightly cycle.
    """
    discovered_keys = set(ScraperResolver().keys())

    missing: List = []
    unknown: List[Tuple[object, str, int]] = []  # (club, key, priority)

    for club in clubs:
        sources = [s for s in getattr(club, "scraping_sources", []) or [] if getattr(s, "enabled", False)]
        if not sources:
            missing.append(club)
            continue
        for source in sources:
            key = getattr(source, "scraper_key", None)
            if not key:
                missing.append(club)
                continue
            if key not in discovered_keys:
                unknown.append((club, key, getattr(source, "priority", 0)))

    if missing:
        Logger.warn(
            f"{len(missing)} club(s) missing scraper key; they will be skipped",
            {"clubs": [getattr(c, "name", "-") for c in missing]},
        )
    if unknown:
        Logger.warn(
            f"{len(unknown)} enabled scraping source(s) have unknown scraper keys; they will be skipped",
            {
                "unknown": [
                    {"club": getattr(c, "name", "-"), "key": k, "priority": p}
                    for c, k, p in unknown
                ],
                "known_keys": sorted(discovered_keys),
            },
        )

    for club in missing:
        with Logger.use_context(getattr(club, "as_context", lambda: {})()):
            Logger.warn("Club has no enabled scraping source with a scraper key; skipping")

    for club, key, priority in unknown:
        with Logger.use_context(getattr(club, "as_context", lambda: {})()):
            Logger.warn(
                f"No scraper found for configured key '{key}' (priority={priority}); source will be skipped"
            )
