"""
Data models for scraping results.

This module contains result classes used during the scraping process,
providing structured representations of individual club results and
aggregated scraping operation results.
"""

from dataclasses import dataclass
from typing import List, Optional

from laughtrack.core.entities.show.model import Show
from laughtrack.core.models.metrics import PerClubStat, ErrorDetail


@dataclass
class ClubScrapingResult:
    """Result of scraping a single club."""

    club_name: str
    shows: List[Show]
    execution_time: float
    error: Optional[str] = None
    club_id: Optional[int] = None
    error_log_count: int = 0
    # scraper_key of the producing scraper (e.g. 'live_nation', 'etix',
    # 'tour_dates'). Forwarded into ShowHandler.insert_shows so each persisted
    # row records its producer in shows.last_scraped_by — the attribution that
    # TASK-2032's orphan audit had to reverse-engineer from URL patterns.
    scraper_key: Optional[str] = None
    # Fetch-layer diagnostics populated by the base scraper from ScrapeDiagnostics.
    # Let /triage-nightly categorize 0-show results without a manual rerun.
    http_status: Optional[int] = None
    bot_block_detected: bool = False
    bot_block_signature: Optional[str] = None
    bot_block_provider: Optional[str] = None
    bot_block_type: Optional[str] = None
    bot_block_source: Optional[str] = None
    bot_block_stage: Optional[str] = None
    playwright_fallback_used: bool = False
    items_before_filter: Optional[int] = None
    # Per-stage counters used by the per-venue outcome classifier in
    # DomainRequestMetrics — let the run-end summary distinguish a genuinely
    # empty calendar from a fetch/parse failure.
    targets_collected: Optional[int] = None
    fetches_ok: Optional[int] = None
    fetches_failed: Optional[int] = None
    # True when every enabled scraping_source's scraper_key for this club
    # failed to resolve against the runtime scraper registry. Distinguishes
    # config drift (unmerged module, renamed key, gitignored file) from a
    # legitimate zero-shows scrape so the entry script can exit non-zero.
    config_error: bool = False

    @property
    def num_shows(self) -> int:
        """Number of shows scraped from this club."""
        return len(self.shows)

    @property
    def success(self) -> bool:
        """Whether the scraping was successful (no error occurred)."""
        return self.error is None


@dataclass
class ScrapingSessionResult:
    """
    Structured result from scraping operations.

    Aggregates results from multiple clubs and provides comprehensive
    statistics and metrics for the entire scraping operation.

    Provides better type safety, readability, and maintainability
    compared to the previous tuple-based approach.
    """

    shows: List["Show"]
    errors: List[ErrorDetail]
    per_club_stats: List[PerClubStat]

    @property
    def total_shows(self) -> int:
        """Total number of shows scraped across all clubs."""
        return len(self.shows)

    @property
    def total_errors(self) -> int:
        """Total number of errors encountered during scraping."""
        return len(self.errors)

    @property
    def successful_clubs(self) -> int:
        """Number of clubs scraped successfully (without errors)."""
        return len([stat for stat in self.per_club_stats if getattr(stat, "success", False)])

    @property
    def total_clubs(self) -> int:
        """Total number of clubs processed during scraping."""
        return len(self.per_club_stats)

    @property
    def success_rate(self) -> float:
        """Success rate as a percentage (0.0 to 100.0)."""
        if self.total_clubs == 0:
            return 0.0
        return (self.successful_clubs / self.total_clubs) * 100.0
