"""Public generator API bridging normalization and rendering."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .normalization import normalize_metrics
from .renderer import render_full_html


def generate_html_dashboard(metrics: List[Dict[str, Any]], output_file: str) -> None:
    """Generate dashboard HTML.

    Parameters
    ----------
    metrics : list of dicts
        Raw metric snapshots (heterogeneous schema tolerated).
    output_file : str
        Destination HTML path (parent directories created automatically).
    """
    sessions = normalize_metrics(metrics)
    html = render_full_html(sessions)
    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
