"""Integration test for dashboard HTML generation with nested metrics schema.

Validates that the modular generator handles the newer nested metrics structure
and produces expected content in the HTML output.
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime

from laughtrack.core.dashboard import generate_html_dashboard


def test_generate_html_dashboard_nested_schema(tmp_path: Path) -> None:
    metrics = [
        {
            "session": {"exported_at": "2025-09-08T20:40:53.665234"},
            "shows": {
                "scraped": 378,
                "saved": 374,
                "inserted": 0,
                "updated": 374,
                "failed_save": 0,
                "skipped_dedup": 4,
                "validation_failed": 0,
                "db_errors": 0,
            },
            "clubs": {"processed": 1, "successful": 1, "failed": 0},
            "errors": {"total": 0},
            # Provided success_rate (will be recalculated but shouldn't break parsing)
            "success_rate": 98.94,
            "per_club_stats": [
                {"club": "The Broadway Comedy Club", "num_shows": 378, "success": True},
            ],
            "error_details": [],
            "duplicate_show_details": [
                {
                    "club_id": 20,
                    "club_name": "The Broadway Comedy Club",
                    "date": "2025-09-21T19:00:00-04:00",
                    "room": "Main Room",
                    "kept": {
                        "name": "Sample Show",
                        "show_page_url": "https://example.com/kept",
                    },
                    "dropped": [
                        {
                            "name": "Duplicate Show",
                            "show_page_url": "https://example.com/dup1",
                        }
                    ],
                }
            ],
        }
    ]

    out_file = tmp_path / "dashboard.html"
    generate_html_dashboard(metrics, str(out_file))
    html = out_file.read_text(encoding="utf-8")

    # Core sanity checks
    assert "Scraper Metrics Dashboard" in html
    assert "378" in html  # scraped count appears
    assert "374" in html  # saved/updated
    # Success rate formatted to one decimal place (≈98.9%)
    assert "98.9%" in html or "98.9%".replace("%", "") in html
    # Dedup widget rendered
    assert "Deduped Shows" in html
    assert "Sample Show" in html
    # Club stats appear
    assert "The Broadway Comedy Club" in html
