"""Aggregator for metrics-related dataclasses and snapshot logic.

The original large `metrics.py` module has been fully decomposed into
subpackages:
    - `metrics_parts` (atomic value objects / simple records)
    - `metrics_session` (session accumulation models)
    - `metrics_snapshot` (snapshot assembly & parsing)

This file re-exports the public surface for convenience:
`from laughtrack.core.models.metrics import PerClubStat, ScrapingMetricsSnapshot, ...`
"""

from .metrics_parts import (
    PerClubStat,
    ErrorDetail,
    DuplicateShow,
    DuplicateShowDetail,
)
from .metrics_session import ScrapingMetrics, DBOperationsSummary
from .metrics_snapshot import (
    SessionBlock,
    ShowsBlock,
    ClubsBlock,
    ErrorsBlock,
    ScrapingMetricsSnapshot,
)

__all__ = [
        "PerClubStat",
        "ErrorDetail",
        "DuplicateShow",
        "DuplicateShowDetail",
        "DBOperationsSummary",
        "SessionBlock",
        "ShowsBlock",
        "ClubsBlock",
        "ErrorsBlock",
        "ScrapingMetrics",
        "ScrapingMetricsSnapshot",
]

