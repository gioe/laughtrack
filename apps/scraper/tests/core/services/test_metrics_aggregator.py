from laughtrack.core.models.results import ClubScrapingResult
from laughtrack.core.services.metrics.aggregator import MetricsAggregator


def _result(club_name: str, *, error: str | None) -> ClubScrapingResult:
    return ClubScrapingResult(club_name=club_name, shows=[], execution_time=1.0, error=error)


def test_aggregator_populates_per_club_success_rate():
    """TASK-2516: per-club success_rate must be a real number (100/0), not NULL.

    A single per-club scrape has only a binary outcome, so the persisted
    success_rate is 100 on success and 0 on failure. Leaving it None left the
    Grafana per-club trend panel and the HTML dashboard summary blank.
    """
    session = MetricsAggregator().aggregate(
        [
            _result("Good Club", error=None),
            _result("Bad Club", error="timeout"),
        ]
    )

    by_club = {stat.club: stat for stat in session.per_club_stats}
    assert by_club["Good Club"].success_rate == 100.0
    assert by_club["Bad Club"].success_rate == 0.0
    # Never leave it None — that is the bug this guards against.
    assert all(stat.success_rate is not None for stat in session.per_club_stats)
