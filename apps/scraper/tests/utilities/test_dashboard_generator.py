"""Basic smoke test for the modular dashboard generator."""
from __future__ import annotations

from pathlib import Path
from datetime import datetime
from laughtrack.core.dashboard import generate_html_dashboard


def test_generate_html_dashboard_smoke(tmp_path: Path) -> None:
    now_iso = datetime.utcnow().isoformat()
    metrics = [{
        "session": {"exported_at": now_iso},
        "shows": {"scraped": 10, "saved": 9, "inserted": 7, "updated": 2, "failed_save": 0, "skipped_dedup": 1, "validation_failed": 0, "db_errors": 0},
        "clubs": {"processed": 3, "successful": 3, "failed": 0},
        "errors": {"total": 0},
        "success_rate": 90.0,
        "per_club_stats": [
            {"club": "Club A", "num_shows": 5, "success": True},
            {"club": "Club B", "num_shows": 3, "success": True},
            {"club": "Club C", "num_shows": 2, "success": True},
        ],
        "error_details": [],
        "duplicate_show_details": [],
    }]
    out_file = tmp_path / "dash.html"
    generate_html_dashboard(metrics, str(out_file))
    text = out_file.read_text(encoding="utf-8")
    assert "<html" in text.lower()
    assert "Scraper Metrics Dashboard" in text