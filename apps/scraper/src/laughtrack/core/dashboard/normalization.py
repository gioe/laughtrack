"""Normalization utilities for dashboard metrics.

Parses heterogeneous raw metric snapshots (current structured export or legacy
flat forms) into a minimal list of session dicts containing only:

    {"datetime": datetime, "snapshot": ScrapingMetricsSnapshot}

All downstream code consumes the attached `ScrapingMetricsSnapshot` dataclass
instead of flattened "scraper.*" keys (now removed). This ensures a single
authoritative translation layer lives here and keeps the renderer/builders
simple and type-oriented.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List

from laughtrack.core.models.metrics import ScrapingMetricsSnapshot

def _session_dict_from_snapshot(s: ScrapingMetricsSnapshot) -> Dict[str, Any]:
    """Return minimal session dict: only datetime and attached snapshot.

    All downstream consumers (builders/renderer) will use the snapshot rather
    than flattened "scraper.*" keys.
    """
    return {"datetime": s.datetime, "snapshot": s}


def normalize_metrics(raw: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize heterogeneous metric snapshots into session dicts with snapshots.

    Skips malformed entries; order returned newest-first by datetime.
    """
    sessions: List[Dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):  # ignore invalid entries silently
            continue
        snap = ScrapingMetricsSnapshot.from_dict(item)
        if not snap:
            continue
        sessions.append(_session_dict_from_snapshot(snap))
    sessions.sort(key=lambda s: s.get("datetime") or datetime.min, reverse=True)
    return sessions
