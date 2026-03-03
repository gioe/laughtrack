"""Legacy dashboard generator retained for reference (unused)."""

from __future__ import annotations
from typing import Optional
from laughtrack.core.models.metrics import ScrapingMetricsSnapshot


class MetricsDashboard:  # pragma: no cover - legacy
    def render(self, snap: Optional[ScrapingMetricsSnapshot]) -> str:
        if not snap:
            return "<p>No metrics data available for dashboard.</p>"
        # Simplified legacy output. Original verbose HTML retained in git history.
        latest = snap
        return (
            f"<div><h3>Legacy Metrics Dashboard</h3>"
            f"<p>Shows scraped: {latest.shows.scraped} | Saved: {latest.shows.saved} | Errors: {latest.errors.total}</p>"
            f"<p>Success Rate: {latest.success_rate:.1f}%</p></div>"
        )

__all__ = ["MetricsDashboard"]
