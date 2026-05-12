from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_repo_root = Path(__file__).resolve().parents[3]
_src_path = _repo_root / "src"
for _p in (str(_src_path), str(_repo_root)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from scripts.core import audit_tour_date_clubs as mod  # noqa: E402


class _FakeCursor:
    description = [
        ("id",),
        ("name",),
        ("city",),
        ("state",),
        ("website",),
    ]

    def __init__(self, rows: list[tuple[Any, ...]]):
        self.rows = rows
        self.executed: list[str] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query: str) -> None:
        self.executed.append(query)

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self.rows


class _FakeConnection:
    def __init__(self, rows: list[tuple[Any, ...]]):
        self.cursor_obj = _FakeCursor(rows)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return self.cursor_obj


def _result(**overrides: Any) -> mod.AuditResult:
    values = {
        "club_id": 42,
        "name": "Example Club",
        "city": "Austin",
        "state": "TX",
        "website": "https://example.test",
    }
    values.update(overrides)
    return mod.AuditResult(**values)


def test_load_tour_date_clubs_selects_enabled_scraping_sources(monkeypatch):
    conn = _FakeConnection([(42, "Example Club", "Austin", "TX", "https://example.test")])
    monkeypatch.setattr(mod, "get_connection", lambda: conn)

    rows = mod._load_tour_date_clubs()

    assert rows == [
        {
            "id": 42,
            "name": "Example Club",
            "city": "Austin",
            "state": "TX",
            "website": "https://example.test",
        }
    ]
    query = conn.cursor_obj.executed[0]
    assert "FROM clubs c" in query
    assert "JOIN scraping_sources ss ON ss.club_id = c.id" in query
    assert "ss.platform = 'tour_dates'" in query
    assert "ss.enabled = TRUE" in query
    assert "c.scraper" not in query
    assert "scraper = 'tour_dates'" not in query


def test_print_report_groups_all_audit_statuses(capsys):
    mod._print_report(
        [
            _result(name="Detected Club", platform="squarespace"),
            _result(name="No Website Club", website="", error="no_website"),
            _result(name="Fetch Error Club", error="http_403"),
            _result(name="Unknown Club"),
        ]
    )

    output = capsys.readouterr().out
    assert "TOUR-DATE CLUB AUDIT" in output
    assert "Platform detected:" in output
    assert "No website:" in output
    assert "Fetch errors:" in output
    assert "Unknown platform:" in output
    assert "ONBOARDING CANDIDATES" in output
    assert "NO WEBSITE" in output
    assert "FETCH ERRORS" in output
    assert "UNKNOWN PLATFORM" in output


def test_create_onboarding_task_mentions_club_id_and_platform_upgrade(monkeypatch):
    calls: list[list[str]] = []

    def fake_run(cmd, **_kwargs):
        calls.append(cmd)

        class _Result:
            returncode = 0
            stderr = ""

        return _Result()

    monkeypatch.setattr(mod.subprocess, "run", fake_run)

    created = mod._create_onboarding_tasks(
        [
            _result(
                club_id=77,
                name="Upgrade Club",
                platform="eventbrite",
                website="https://upgrade.example",
            )
        ]
    )

    assert created == 1
    cmd = calls[0]
    description = cmd[3]
    criteria = " ".join(cmd)
    assert "Club already in DB (id=77)" in description
    assert "Upgrade from tour_dates discovery to dedicated eventbrite scraper" in description
    assert "Upgrade club id=77 from tour_dates to 'eventbrite'" in criteria
