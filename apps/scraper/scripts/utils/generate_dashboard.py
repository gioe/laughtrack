#!/usr/bin/env python3
"""CLI wrapper for metrics dashboard generation (now primary entry point).

Legacy `generate_html_dashboard.py` has been removed; this wrapper invokes the
modular implementation in `laughtrack.core.dashboard`.
"""
from __future__ import annotations
import argparse
from typing import List, Dict, Any
from laughtrack.foundation.utilities.path.utils import ProjectPaths
from laughtrack.core.dashboard import generate_html_dashboard as _generate


def generate_html_dashboard(metrics: List[Dict[str, Any]], output_file: str) -> None:  # shim
    _generate(metrics, output_file)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate HTML dashboard for scraping metrics")
    parser.add_argument("--output", "-o", default=None, help="Output HTML file (default: dashboard.html at project root)")
    args = parser.parse_args()
    metrics = ProjectPaths.load_metrics_files()
    if not metrics:
        print("❌ No metrics data found. Run a scraping session first.")
        return
    out_path = ProjectPaths.resolve_output_path(args.output)
    generate_html_dashboard(metrics, str(out_path))
    print(f"🌐 Open the dashboard: file://{out_path.absolute()}")


if __name__ == "__main__":  # pragma: no cover
    main()