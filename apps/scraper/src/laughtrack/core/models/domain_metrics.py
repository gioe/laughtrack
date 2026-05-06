"""Per-domain scraping observability metrics.

Tracks per-club request outcomes accumulated in-memory during a scrape_all run.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class ScrapeOutcome(str, Enum):
    """Per-venue classification of a scrape result.

    The success-rate threshold alert previously fired on any zero-show venue,
    conflating bot-blocked / parser-rejected scrapes with legitimately empty
    calendars. ``outcome`` lets downstream filtering treat ``EMPTY_CALENDAR``
    as non-actionable while still routing ``DEGRADED`` and
    ``CLASSIFIER_REJECTED_ALL`` to alerts.
    """

    HEALTHY = "healthy"
    EMPTY_CALENDAR = "empty_calendar"
    CLASSIFIER_REJECTED_ALL = "classifier_rejected_all"
    DEGRADED = "degraded"


@dataclass
class DomainRequestMetrics:
    """In-memory counters for a single club's scraping outcomes."""

    club_name: str
    club_id: Optional[int] = None
    scraper_type: Optional[str] = None  # scraper key (e.g. "seatengine", "tessera")
    total: int = 0
    ok: int = 0          # successful scrape with shows
    none_resp: int = 0   # completed without error but returned no shows
    error: int = 0       # scrape raised an exception
    # Per-stage counters populated from ScrapeDiagnostics. Optional because
    # tests / older callers may construct DomainRequestMetrics without a real
    # scrape pipeline; defaults of 0 produce a DEGRADED outcome by design when
    # no signal is available, since "no fetches succeeded" is not safe to
    # silently classify as EMPTY_CALENDAR.
    targets_collected: int = 0
    fetches_ok: int = 0
    fetches_failed: int = 0
    items_before_filter: int = 0
    # A scraper can return non-None HTML for a 4xx body or a Cloudflare/DataDome
    # interstitial without raising — fetches_ok would tick up but no shows would
    # parse. Carrying bot_block_detected lets the outcome classifier downgrade
    # those silent failures to DEGRADED instead of misclassifying them as
    # EMPTY_CALENDAR and filtering them out of alerts.
    bot_block_detected: bool = False

    @property
    def success_rate(self) -> float:
        """Success rate as a percentage (0.0–100.0). ok / total."""
        if self.total == 0:
            return 100.0
        return (self.ok / self.total) * 100.0

    @property
    def outcome(self) -> ScrapeOutcome:
        """Classify this scrape using the per-stage counters.

        Priority order:
          1. HEALTHY — at least one OK scrape with shows.
          2. DEGRADED — exception raised, a fetch failed at the network
             layer, OR a bot-block (DataDome/Cloudflare/etc.) was detected
             during the scrape. The bot-block branch is what prevents a
             soft-failed venue (200 OK with an interstitial body) from
             silently classifying as EMPTY_CALENDAR and getting filtered
             out of alerts.
          3. EMPTY_CALENDAR — fetches completed cleanly, parser reached
             ``transform_data`` with zero candidates (``items_before_filter ==
             0``). Includes scrapers that ``return None`` from ``get_data``
             when a page legitimately has no events.
          4. CLASSIFIER_REJECTED_ALL — fetches completed cleanly and the
             parser saw candidates, but every one was filtered out before
             becoming a Show. Worth a parser look.
          5. DEGRADED fallback — no fetches succeeded and no exception
             surfaced; should not happen in practice, but classify as
             actionable rather than silently treating as empty.
        """
        if self.ok > 0:
            return ScrapeOutcome.HEALTHY
        if self.error > 0 or self.fetches_failed > 0 or self.bot_block_detected:
            return ScrapeOutcome.DEGRADED
        if self.fetches_ok > 0:
            if self.items_before_filter == 0:
                return ScrapeOutcome.EMPTY_CALENDAR
            return ScrapeOutcome.CLASSIFIER_REJECTED_ALL
        return ScrapeOutcome.DEGRADED

    def as_log_dict(self) -> Dict:
        return {
            "club": self.club_name,
            "total": self.total,
            "ok": self.ok,
            "none_resp": self.none_resp,
            "error": self.error,
            "success_rate_pct": round(self.success_rate, 1),
            "outcome": self.outcome.value,
        }


@dataclass
class ScrapingRunSummary:
    """Aggregate summary for a full scrape_all run.

    Note: clubs_ok / clubs_empty / clubs_errored are non-exclusive counts — a club
    can appear in more than one bucket (e.g. both ok and none_resp > 0). Their sum
    may exceed total_clubs. Use per_club for precise per-domain analysis.
    """

    per_club: List[DomainRequestMetrics] = field(default_factory=list)

    @property
    def total_clubs(self) -> int:
        return len(self.per_club)

    @property
    def clubs_ok(self) -> int:
        return sum(1 for m in self.per_club if m.ok > 0)

    @property
    def clubs_errored(self) -> int:
        return sum(1 for m in self.per_club if m.error > 0)

    @property
    def clubs_empty(self) -> int:
        return sum(1 for m in self.per_club if m.none_resp > 0 and m.ok == 0 and m.error == 0)

    @property
    def clubs_empty_calendar(self) -> int:
        """Clubs whose outcome classifier marks the calendar as legitimately empty."""
        return sum(1 for m in self.per_club if m.outcome == ScrapeOutcome.EMPTY_CALENDAR)

    @property
    def empty_calendar_clubs(self) -> List[DomainRequestMetrics]:
        """Per-club metrics for venues classified as EMPTY_CALENDAR (low-priority list)."""
        return [m for m in self.per_club if m.outcome == ScrapeOutcome.EMPTY_CALENDAR]

    def merge(self, other: "ScrapingRunSummary") -> "ScrapingRunSummary":
        """Combine two summaries into one (e.g. venue clubs + production companies)."""
        combined = ScrapingRunSummary()
        combined.per_club = self.per_club + other.per_club
        return combined

    def below_threshold(self, threshold_pct: float) -> List[DomainRequestMetrics]:
        """Return clubs whose success rate is below *threshold_pct*."""
        return [m for m in self.per_club if m.success_rate < threshold_pct]
