#!/usr/bin/env python3
"""
Interactively select a metrics JSON file from the metrics/ directory and render the HTML dashboard from it.

Usage:
  ./select_metrics_dashboard.py             # interactive picker, writes to dashboard.html
  ./select_metrics_dashboard.py --file F    # render a specific metrics file
  ./select_metrics_dashboard.py --output O  # custom output path
"""

from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from laughtrack.foundation.utilities.path.utils import ProjectPaths


def _list_metrics_files() -> List[Path]:
    metrics_dir = ProjectPaths.get_metrics_dir()
    files = sorted(metrics_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files


def _human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.1f}{unit}"
        size /= 1024.0
    return f"{size:.1f}TB"


def _pick_file(files: List[Path]) -> Path | None:
    print("📁 Available metrics files (most recent first). You can type a filter before choosing.\n")

    # Optional interactive filter
    try:
        filter_str = input("Filter (substring, e.g. '20250901'; Enter for all): ").strip()
    except (EOFError, KeyboardInterrupt):
        return None

    display_files = files
    if filter_str:
        needle = filter_str.lower()
        display_files = [p for p in files if needle in p.name.lower()]
        if not display_files:
            print("❌ No files match that filter.")
            return None

    for idx, p in enumerate(display_files, start=1):
        mtime = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        size = _human_size(p.stat().st_size)
        print(f"  {idx:2d}) {p.name}    [{size}, modified {mtime}]")
    print("")

    try:
        choice = input("Select a file by number (Enter for 1, or 'q' to quit): ").strip()
    except (EOFError, KeyboardInterrupt):
        return None

    if choice.lower() in {"q", "quit", "exit"}:
        return None
    if choice == "":
        return display_files[0]
    try:
        i = int(choice)
        if 1 <= i <= len(display_files):
            return display_files[i - 1]
    except ValueError:
        pass
    print("❌ Invalid selection.")
    return None


def _load_metrics_from_file(path: Path) -> List[Dict[str, Any]]:
    with open(path, "r") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        return [data]
    else:
        raise ValueError(f"Unsupported JSON in {path}: expected dict or list, got {type(data).__name__}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Select a metrics file and render the dashboard")
    parser.add_argument("--file", "-f", type=str, default=None, help="Path to a metrics JSON file (skip selection)")
    parser.add_argument("--output", "-o", type=str, default=None, help="Output HTML path (default: dashboard.html)")
    parser.add_argument("--filter", "-F", type=str, default=None, help="Substring filter applied to file names during selection")
    args = parser.parse_args()

    if args.file:
        path = Path(args.file).expanduser().resolve()
        if not path.exists():
            print(f"❌ File not found: {path}")
            sys.exit(1)
    else:
        files = _list_metrics_files()
        if not files:
            print("❌ No metrics files found. Run a scraping session first.")
            sys.exit(1)
        # If CLI filter is provided, pre-filter before entering the picker
        if args.filter:
            needle = args.filter.lower()
            files = [p for p in files if needle in p.name.lower()]
            if not files:
                print("❌ No files match the provided --filter.")
                sys.exit(1)
        path = _pick_file(files)
        if not path:
            print("ℹ️  No file selected. Exiting.")
            sys.exit(0)

    try:
        metrics = _load_metrics_from_file(path)
    except Exception as e:
        print(f"❌ Failed to load metrics: {e}")
        sys.exit(1)

    # Ensure project root is on sys.path so 'scripts.*' imports resolve when running this file directly
    project_root = ProjectPaths.get_project_root()
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # Import new core implementation (legacy shim retained for a short period)
    from laughtrack.core.dashboard import generate_html_dashboard  # type: ignore

    output_path = ProjectPaths.resolve_output_path(args.output)
    print(f"🛠️  Rendering dashboard from: {path.name}")
    generate_html_dashboard(metrics, str(output_path))
    uri = output_path.resolve().as_uri()
    print(f"🌐 Opening dashboard: {uri}")
    try:
        webbrowser.open_new_tab(uri)
    except Exception:
        # Non-fatal; just show the link
        pass


if __name__ == "__main__":
    main()
