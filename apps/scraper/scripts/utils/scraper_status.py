"""Terminal health summary for the most recent scraper run."""

import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
_src = _root / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from laughtrack.foundation.utilities.path.utils import ProjectPaths  # noqa: E402


def find_latest_metrics(metrics_dir: Path) -> Path | None:
    if not metrics_dir.exists():
        return None
    files = sorted(metrics_dir.glob("metrics_*.json"))
    return files[-1] if files else None


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    minutes, secs = divmod(int(seconds), 60)
    if minutes < 60:
        return f"{minutes}m {secs}s"
    hours, mins = divmod(minutes, 60)
    return f"{hours}h {mins}m"


def print_summary(data: dict) -> None:
    session = data.get("session", {})
    shows = data.get("shows", {})
    clubs = data.get("clubs", {})
    error_details = data.get("error_details", [])

    exported_at = session.get("exported_at", "unknown")
    if exported_at != "unknown":
        try:
            dt = datetime.fromisoformat(exported_at)
            # Format without a timezone label — the stored timestamp is naive
            exported_at = dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass

    duration = session.get("duration_seconds")
    duration_str = format_duration(duration) if duration is not None else "unknown"

    total_clubs = clubs.get("processed", 0)
    successful = clubs.get("successful", 0)
    failed = clubs.get("failed", 0)
    shows_scraped = shows.get("scraped", 0)
    shows_saved = shows.get("saved", 0)
    success_rate = data.get("success_rate")

    print("=" * 60)
    print("  SCRAPER HEALTH SUMMARY")
    print("=" * 60)
    print(f"  Run timestamp : {exported_at}")
    print(f"  Duration      : {duration_str}")
    print(f"  Total clubs   : {total_clubs}")
    print(f"  Successful    : {successful}")
    print(f"  Failed        : {failed}")
    if success_rate is not None:
        print(f"  Show save rate: {success_rate:.1f}%")
    print(f"  Shows scraped : {shows_scraped}")
    print(f"  Shows saved   : {shows_saved}")

    if error_details:
        error_counts: Counter = Counter()
        for entry in error_details:
            msg = str(entry.get("error", "unknown error"))
            short = msg[:120] + "..." if len(msg) > 120 else msg
            error_counts[short] += 1

        print()
        print(f"  TOP ERRORS ({len(error_details)} total failures):")
        print("  " + "-" * 56)
        for msg, count in error_counts.most_common(5):
            print(f"  [{count}x] {msg}")

    print("=" * 60)


def main() -> None:
    metrics_dir = ProjectPaths.get_metrics_dir(create=False)

    # Also check relative to cwd for flexibility
    if not metrics_dir.exists():
        metrics_dir = Path("metrics")

    latest = find_latest_metrics(metrics_dir)

    if latest is None:
        print("No metrics files found in", metrics_dir)
        print("Run a scrape first: make scrape-all")
        sys.exit(1)

    with open(latest, encoding="utf-8") as f:
        data = json.load(f)

    print_summary(data)


if __name__ == "__main__":
    main()
