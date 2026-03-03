"""Startup validation for scraper configuration.

Logs warnings for clubs that are missing a scraper key or whose key does not
match any discovered scraper implementation. Intended to be called once before
batch scraping begins.
"""

from __future__ import annotations

from typing import Iterable

from laughtrack.app.scraper_resolver import ScraperResolver
from laughtrack.foundation.infrastructure.logger.logger import Logger


def validate_scraper_keys_for_clubs(clubs: Iterable) -> None:
    """Validate that each club has a valid scraper key.

    - Warn if a club has no scraper key configured
    - Warn if a club's scraper key doesn't match any discovered scraper
    - Emit a concise summary so operators can fix configuration quickly
    """
    discovered_keys = set(ScraperResolver().keys())

    missing = []
    unknown = []

    for club in clubs:
        key = getattr(club, "scraper", None)
        if not key:
            missing.append(club)
            continue
        if key not in discovered_keys:
            unknown.append((club, key))

    # Summaries first
    if missing:
        Logger.warn(
            f"{len(missing)} club(s) missing scraper key; they will be skipped",
            {"clubs": [getattr(c, "name", "-") for c in missing]},
        )
    if unknown:
        Logger.warn(
            f"{len(unknown)} club(s) have unknown scraper keys; they will be skipped",
            {"unknown": [{"club": getattr(c, "name", "-"), "key": k} for c, k in unknown], "known_keys": sorted(discovered_keys)},
        )

    # Per-club context warnings for easier tracing in logs
    for club in missing:
        with Logger.use_context(getattr(club, "as_context", lambda: {})()):
            Logger.warn("Club has no scraper key configured; skipping")

    for club, key in unknown:
        with Logger.use_context(getattr(club, "as_context", lambda: {})()):
            Logger.warn(f"No scraper found for configured key '{key}'; skipping")
