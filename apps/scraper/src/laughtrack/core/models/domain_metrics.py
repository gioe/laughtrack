"""Per-domain scraping observability metrics.

Tracks per-club request outcomes accumulated in-memory during a scrape_all run.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


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

    @property
    def success_rate(self) -> float:
        """Success rate as a percentage (0.0–100.0). ok / total."""
        if self.total == 0:
            return 100.0
        return (self.ok / self.total) * 100.0

    def as_log_dict(self) -> Dict:
        return {
            "club": self.club_name,
            "total": self.total,
            "ok": self.ok,
            "none_resp": self.none_resp,
            "error": self.error,
            "success_rate_pct": round(self.success_rate, 1),
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

    def merge(self, other: "ScrapingRunSummary") -> "ScrapingRunSummary":
        """Combine two summaries into one (e.g. venue clubs + production companies)."""
        combined = ScrapingRunSummary()
        combined.per_club = self.per_club + other.per_club
        return combined

    def below_threshold(self, threshold_pct: float) -> List[DomainRequestMetrics]:
        """Return clubs whose success rate is below *threshold_pct*."""
        return [m for m in self.per_club if m.success_rate < threshold_pct]
