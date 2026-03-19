"""CLI multi-run trend viewer — prints a tabular summary of the last N scraper runs."""

import argparse
import json
from datetime import datetime
from pathlib import Path

METRICS_DIR = Path(__file__).parent.parent.parent / "metrics"
DEFAULT_RUNS = 10
COL_WIDTHS = (22, 14, 15, 12)
HEADERS = ("Timestamp", "Clubs Passed", "Shows Scraped", "Errors")


def _fmt_ts(exported_at: str) -> str:
    try:
        dt = datetime.fromisoformat(exported_at)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return str(exported_at)


def _load_run(path: Path) -> dict | None:
    try:
        with path.open() as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _divider(widths: tuple[int, ...]) -> str:
    return "+" + "+".join("-" * (w + 2) for w in widths) + "+"


def _row(values: tuple, widths: tuple[int, ...]) -> str:
    cells = [" {:<{}} ".format(v, w) for v, w in zip(values, widths)]
    return "|" + "|".join(cells) + "|"


def print_table(runs: list[dict]) -> None:
    div = _divider(COL_WIDTHS)
    print(div)
    print(_row(HEADERS, COL_WIDTHS))
    print(div)
    for run in runs:
        session = run.get("session", {})
        clubs = run.get("clubs", {})
        shows = run.get("shows", {})
        errors = run.get("errors", {})

        ts = _fmt_ts(session.get("exported_at", ""))
        clubs_passed = clubs.get("successful", 0)
        shows_scraped = shows.get("scraped", 0)
        error_count = errors.get("total", 0)

        print(_row((ts, clubs_passed, shows_scraped, error_count), COL_WIDTHS))
    print(div)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Show a tabular summary of the last N scraper runs."
    )
    parser.add_argument(
        "-n",
        "--runs",
        type=int,
        default=DEFAULT_RUNS,
        metavar="N",
        help=f"Number of most-recent runs to display (default: {DEFAULT_RUNS})",
    )
    parser.add_argument(
        "--metrics-dir",
        type=Path,
        default=METRICS_DIR,
        help="Path to the metrics/ directory",
    )
    args = parser.parse_args()

    metrics_dir: Path = args.metrics_dir
    if not metrics_dir.exists():
        print(f"No metrics directory found at {metrics_dir}")
        return

    files = sorted(metrics_dir.glob("metrics_*.json"))
    if not files:
        print(f"No metrics files found in {metrics_dir}")
        return

    recent = files[-args.runs :]
    runs = [r for f in recent if (r := _load_run(f)) is not None]

    if not runs:
        print("No readable metrics files found.")
        return

    print(f"\nLast {len(runs)} scraper run(s):\n")
    print_table(runs)
    print()


if __name__ == "__main__":
    main()
