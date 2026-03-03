"""Read-only access to persisted metrics snapshots."""

from __future__ import annotations
from typing import List, Optional

from laughtrack.foundation.utilities.path.utils import ProjectPaths
from laughtrack.core.models.metrics import ScrapingMetricsSnapshot


class MetricsRepository:
    def __init__(self) -> None:
        self.metrics_dir = ProjectPaths.get_metrics_dir()

    def get_latest_snapshot(self) -> Optional[ScrapingMetricsSnapshot]:
        snaps = self._load_metrics_snapshots(count=1)
        return snaps[0] if snaps else None

    def get_recent_snapshots(self, count: int = 10) -> List[ScrapingMetricsSnapshot]:
        return self._load_metrics_snapshots(count=count)

    def _load_metrics_snapshots(self, count: Optional[int] = None) -> List[ScrapingMetricsSnapshot]:
        import glob
        metrics_files = glob.glob(str(self.metrics_dir / "metrics_*.json"))
        metrics_files.sort(reverse=True)
        if count is not None:
            metrics_files = metrics_files[:count]

        snaps: List[ScrapingMetricsSnapshot] = []
        for file in metrics_files:
            try:
                snap: Optional[ScrapingMetricsSnapshot] = ScrapingMetricsSnapshot.from_file(file)
                if snap is not None:
                    snaps.append(snap)
            except Exception:  # pragma: no cover - resilience
                continue
        return snaps

__all__ = ["MetricsRepository"]
