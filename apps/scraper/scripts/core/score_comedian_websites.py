#!/usr/bin/env python3
"""
Score comedian website confidence — how likely is the stored URL to be
the comedian's actual personal/official website?

Outputs a CSV with columns: comedian, website, confidence, signals

Confidence levels:
  high   — almost certainly the comedian's own site
  medium — probably correct but worth a spot-check
  low    — likely wrong (venue page, aggregator, unrelated domain)

Usage:
    python -m scripts.core.score_comedian_websites
    python -m scripts.core.score_comedian_websites --below medium
    python -m scripts.core.score_comedian_websites --below low
"""

import argparse
import csv
import os
import sys
from collections import Counter
from pathlib import Path

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from laughtrack.adapters.db import get_connection
from laughtrack.utilities.domain.comedian.website_confidence import score_website


def main():
    parser = argparse.ArgumentParser(
        description="Score comedian website confidence levels",
    )
    parser.add_argument("--below", choices=["high", "medium", "low"],
                        help="Only output rows below this confidence level")
    parser.add_argument("--output", type=str, help="Output file path (default: stdout)")
    args = parser.parse_args()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT name, website, website_scrape_strategy
                FROM comedians
                WHERE website IS NOT NULL AND website <> ''
                ORDER BY name
            """)
            rows = cur.fetchall()

    scores = []
    for name, website, strategy in rows:
        has_events = strategy in ("json_ld", "json_ld_subpage")
        s = score_website(name, website, has_events=has_events)
        scores.append((name, website, s))

    # Filter if requested
    if args.below:
        level_order = {"low": 0, "medium": 1, "high": 2}
        threshold = level_order[args.below]
        scores = [(n, w, s) for n, w, s in scores if level_order[s.confidence] < threshold]

    # Sort: low confidence first
    level_priority = {"low": 0, "medium": 1, "high": 2}
    scores.sort(key=lambda t: (level_priority[t[2].confidence], t[0]))

    out = open(args.output, "w", newline="") if args.output else sys.stdout
    try:
        w = csv.writer(out)
        w.writerow(["comedian", "website", "confidence", "points", "signals"])
        for name, website, s in scores:
            w.writerow([name, website, s.confidence, s.points, "; ".join(s.signals)])

        # Summary to stderr
        counts = Counter(s.confidence for _, _, s in scores)
        total = len(scores)
        print(f"\nConfidence breakdown ({total} total):", file=sys.stderr)
        for level in ("high", "medium", "low"):
            c = counts.get(level, 0)
            print(f"  {level:8s} {c:5d}  ({c*100//total if total else 0}%)", file=sys.stderr)
    finally:
        if args.output:
            out.close()
            print(f"Written to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
