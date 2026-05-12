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


# ---------------------------------------------------------------------------
# DB loader
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Status classification — covers criterion 7032
# ---------------------------------------------------------------------------

def test_status_ready_for_specific_platform_marker():
    r = _result(platform="squarespace", matched_marker="Static.SQUARESPACE_CONTEXT")
    assert r.status == mod.STATUS_READY


def test_status_review_for_generic_json_ld_marker():
    r = _result(platform="json_ld", matched_marker='"@type":"Event"')
    assert r.status == mod.STATUS_REVIEW


def test_status_no_website_when_website_missing():
    r = _result(website="", error="no_website")
    assert r.status == mod.STATUS_NO_WEBSITE


def test_status_fetch_error_for_http_failure():
    r = _result(error="http_403", http_status=403)
    assert r.status == mod.STATUS_FETCH_ERROR


def test_status_unknown_when_fetched_but_no_marker():
    r = _result()
    assert r.status == mod.STATUS_UNKNOWN


def test_print_report_groups_all_five_states(capsys):
    mod._print_report(
        [
            _result(name="Ready Club", platform="squarespace", matched_marker="Static.SQUARESPACE_CONTEXT"),
            _result(name="Review Club", platform="json_ld", matched_marker='"@type":"Event"'),
            _result(name="No Website Club", website="", error="no_website"),
            _result(name="Fetch Error Club", error="http_403", http_status=403),
            _result(name="Unknown Club"),
        ]
    )

    output = capsys.readouterr().out
    # Header / summary line uses the new bucket names
    assert "TOUR-DATE ONBOARDING QUEUE" in output
    assert "Ready:" in output
    assert "Review:" in output
    assert "No website:" in output
    assert "Fetch error:" in output
    assert "Unknown:" in output
    # Each state has a section
    assert "READY FOR ONBOARDING" in output
    assert "REVIEW NEEDED" in output
    assert "NO WEBSITE" in output
    assert "FETCH ERROR" in output
    assert "UNKNOWN" in output


def test_print_report_surfaces_evidence_for_operator_triage(capsys):
    mod._print_report(
        [
            _result(name="Ready Club", platform="squarespace", matched_marker="Static.SQUARESPACE_CONTEXT"),
        ]
    )
    output = capsys.readouterr().out
    # Evidence line includes the matched marker and the website URL so the
    # operator can pick the right SCRAPERS.md section without re-running.
    assert "Static.SQUARESPACE_CONTEXT" in output
    assert "platform=squarespace" in output
    assert "url=https://example.test" in output


# ---------------------------------------------------------------------------
# Task creation — covers criteria 7029 and 7030
# ---------------------------------------------------------------------------

def test_create_onboarding_tasks_only_for_ready_results(monkeypatch):
    calls: list[list[str]] = []

    def fake_run(cmd, **_kwargs):
        calls.append(list(cmd))

        class _Result:
            returncode = 0
            stdout = '{"duplicates":[],"recently_closed":[]}'
            stderr = ""

        return _Result()

    monkeypatch.setattr(mod, "_resolve_tusk_binary", lambda: "/fake/tusk")
    monkeypatch.setattr(mod.subprocess, "run", fake_run)

    created = mod._create_onboarding_tasks(
        [
            _result(name="Ready Club", club_id=1, platform="squarespace",
                    matched_marker="Static.SQUARESPACE_CONTEXT"),
            _result(name="Review Club", club_id=2, platform="json_ld",
                    matched_marker='"@type":"Event"'),
            _result(name="No Website Club", club_id=3, website="", error="no_website"),
            _result(name="Fetch Error Club", club_id=4, error="http_403", http_status=403),
            _result(name="Unknown Club", club_id=5),
        ]
    )

    assert created == 1
    insert_calls = [c for c in calls if "task-insert" in c]
    assert len(insert_calls) == 1
    inserted_summary = insert_calls[0][2]
    assert "Ready Club" in inserted_summary
    # No tasks created for review/no-website/fetch-error/unknown
    assert all("Review Club" not in arg for arg in [a for c in insert_calls for a in c])
    assert all("Unknown Club" not in arg for arg in [a for c in insert_calls for a in c])


def test_create_onboarding_tasks_skips_when_dupes_check_returns_match(monkeypatch):
    calls: list[list[str]] = []

    def fake_run(cmd, **_kwargs):
        calls.append(list(cmd))

        class _Result:
            returncode = 0
            stdout = '{"duplicates":[{"id":99,"summary":"Onboard Existing Club"}],"recently_closed":[]}'
            stderr = ""

        return _Result()

    monkeypatch.setattr(mod, "_resolve_tusk_binary", lambda: "/fake/tusk")
    monkeypatch.setattr(mod.subprocess, "run", fake_run)

    created = mod._create_onboarding_tasks(
        [
            _result(name="Existing Club", club_id=77, platform="eventbrite",
                    matched_marker="eventbrite.com/e/"),
        ]
    )

    assert created == 0
    assert any("dupes" in c and "check" in c for c in calls)
    assert not any("task-insert" in c for c in calls)


def test_create_onboarding_tasks_uses_resolved_tusk_binary(monkeypatch):
    calls: list[list[str]] = []

    def fake_run(cmd, **_kwargs):
        calls.append(list(cmd))

        class _Result:
            returncode = 0
            stdout = '{"duplicates":[],"recently_closed":[]}'
            stderr = ""

        return _Result()

    monkeypatch.setattr(mod, "_resolve_tusk_binary", lambda: "/proj/.claude/bin/tusk")
    monkeypatch.setattr(mod.subprocess, "run", fake_run)

    mod._create_onboarding_tasks(
        [_result(name="Ready Club", club_id=1, platform="squarespace",
                 matched_marker="Static.SQUARESPACE_CONTEXT")]
    )

    # Every subprocess invocation must use the resolved project-local binary
    assert calls
    for cmd in calls:
        assert cmd[0] == "/proj/.claude/bin/tusk"


def test_resolve_tusk_binary_prefers_project_local(tmp_path, monkeypatch):
    # Construct a fake parent tree containing .claude/bin/tusk
    fake_root = tmp_path / "repo"
    bin_dir = fake_root / ".claude" / "bin"
    bin_dir.mkdir(parents=True)
    fake_tusk = bin_dir / "tusk"
    fake_tusk.write_text("#!/bin/sh\necho test\n")
    fake_tusk.chmod(0o755)
    fake_script = fake_root / "apps" / "scraper" / "scripts" / "core" / "audit_tour_date_clubs.py"
    fake_script.parent.mkdir(parents=True)
    fake_script.write_text("# fake")

    monkeypatch.setattr(mod, "__file__", str(fake_script))
    assert mod._resolve_tusk_binary() == str(fake_tusk)


def test_create_onboarding_task_description_mentions_club_id_and_platform_upgrade(monkeypatch):
    calls: list[list[str]] = []

    def fake_run(cmd, **_kwargs):
        calls.append(list(cmd))

        class _Result:
            returncode = 0
            stdout = '{"duplicates":[],"recently_closed":[]}'
            stderr = ""

        return _Result()

    monkeypatch.setattr(mod, "_resolve_tusk_binary", lambda: "/fake/tusk")
    monkeypatch.setattr(mod.subprocess, "run", fake_run)

    created = mod._create_onboarding_tasks(
        [
            _result(
                club_id=77,
                name="Upgrade Club",
                platform="eventbrite",
                matched_marker="eventbrite.com/e/",
                website="https://upgrade.example",
            )
        ]
    )

    assert created == 1
    insert_cmd = next(c for c in calls if "task-insert" in c)
    description = insert_cmd[3]
    criteria = " ".join(insert_cmd)
    assert "Club already in DB (id=77)" in description
    assert "Upgrade from tour_dates discovery to dedicated eventbrite scraper" in description
    assert "Upgrade club id=77 from tour_dates to 'eventbrite'" in criteria
    # Evidence is surfaced in the description for the operator
    assert "eventbrite.com/e/" in description
