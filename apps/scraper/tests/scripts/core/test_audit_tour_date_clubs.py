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


def test_detects_newly_documented_platform_markers():
    etix_platform, etix_marker = mod._detect_platform_from_html(
        '<a href="https://www.etix.com/ticket/p/123">Tickets</a>'
    )
    assert (etix_platform, etix_marker) == ("etix", "etix.com")

    sellingticket_platform, sellingticket_marker = mod._detect_platform_from_html(
        '<a href="https://secure.sellingticket.com/design22/clients/list/'
        'index_byUserListAll.aspx?OrganizationID=64">'
    )
    assert (sellingticket_platform, sellingticket_marker) == (
        "sellingticket",
        "sellingticket.com",
    )


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


# ---------------------------------------------------------------------------
# SCRAPERS.md ↔ audit-marker consistency (covers criteria 7056, 7057)
#
# Catches the silent drift case where a new platform section is added to
# SCRAPERS.md without a corresponding entry in _HTML_PLATFORM_MARKERS or
# _WEBSITE_DOMAIN_PLATFORMS — onboarding candidates for that platform would
# otherwise fall into the audit script's `unknown` bucket and never surface.
# ---------------------------------------------------------------------------

_SCRAPERS_MD_PATH = _repo_root / "SCRAPERS.md"

# Map each `### <Section>` heading under "## Platform Sections" in
# apps/scraper/SCRAPERS.md to the platform key the audit script must surface
# (as a value in _HTML_PLATFORM_MARKERS or _WEBSITE_DOMAIN_PLATFORMS).
# Adding a new platform section without updating this mapping fails the
# `test_every_scrapers_md_section_is_known` test below — pick one of:
#   1. Add a marker to _HTML_PLATFORM_MARKERS / _WEBSITE_DOMAIN_PLATFORMS in
#      audit_tour_date_clubs.py, then record the (section -> key) pair here.
#   2. If the section can't be auto-detected (one-off venue scraper, no
#      reliable client-side signal), add it to _EXEMPT_PLATFORM_SECTIONS
#      with a brief reason instead.
_PLATFORM_SECTION_MARKER_KEY: dict[str, str] = {
    "Ticketmaster": "ticketmaster",
    "Eventbrite": "eventbrite",
    "Etix / Rockhouse Partners": "etix",
    "SeatEngine v1": "seatengine",
    "SeatEngine Classic (Legacy)": "seatengine",
    "SeatEngine v3": "seatengine",
    "Tixr": "tixr",
    "Tixr Webflow Day Card": "tixr",
    "Tockify": "tockify",
    "Squarespace": "squarespace",
    "Wix Events": "wix",
    "Crowdwork": "crowdwork",
    "VBO Tickets": "vbo_tickets",
    "Tribe Events Calendar (WordPress)": "tribe_events",
    "JSON-LD (Generic Fallback)": "json_ld",
    "SquadUP": "squadup",
    "Prekindle": "prekindle",
    "ThunderTix": "thundertix",
    "TicketSource": "ticketsource",
    "Humanitix": "humanitix",
    "Ninkashi": "ninkashi",
    "StageTime": "stagetime",
    "OvationTix": "ovationtix",
    "OpenDate": "opendate",
    "SimpleTix": "simpletix",
    "SellingTicket": "sellingticket",
}

# Headings under "## Platform Sections" that introduce a group of variants
# rather than a single detectable platform.
_META_PLATFORM_SECTIONS: frozenset[str] = frozenset({
    "SeatEngine — Identification Checklist",
})

# Platforms documented in SCRAPERS.md but intentionally NOT represented in the
# audit script's marker tables, with the reason recorded for future maintainers.
# Removing an entry here without adding a marker will fail the consistency test.
_EXEMPT_PLATFORM_SECTIONS: dict[str, str] = {
    "rhp-events (WordPress Plugin)": (
        "WordPress plugin variant — venues currently surface via the generic "
        "tribe_events bucket or via the JSON-LD fallback; dedicated marker is "
        "a follow-up"
    ),
    "Tixologi (Laugh Factory CMS)": (
        "Venue-specific (Laugh Factory Reno) — no generic Tixologi platform "
        "scraper exists, so onboarding does not branch on a tixologi key"
    ),
    "Netlify Functions (East Austin Comedy)": (
        "Venue-specific scraper hitting a custom /.netlify/functions endpoint "
        "— no generic platform to detect on other venues"
    ),
    "Vivenu": (
        "Vivenu venues are hosted on custom subdomains (e.g. "
        "tickets.thirdcoastcomedy.club) with no stable HTML marker on the "
        "venue's main site; adding a vivenu marker is a follow-up"
    ),
    "JetBook (Bubble.io)": (
        "Embedded via iframe src=jetbook.co/o_iframe/<slug> on the venue's own "
        "site; adding 'jetbook.co/o_iframe' as a marker is a follow-up"
    ),
    "Fienta": (
        "Events load client-side via JS calls to fienta.com/api — no static "
        "marker on the venue homepage; adding a fienta.com domain marker for "
        "buy-links is a follow-up"
    ),
    "Showpass": (
        "DB-only onboarding (no Python changes) — adding showpass.com as a "
        "marker is a follow-up"
    ),
    "TicketLeap": (
        "DB-only onboarding (no Python changes) — adding events.ticketleap.com "
        "as a marker is a follow-up"
    ),
    "Square Online (Weebly)": (
        "Venue-specific (Coral Gables) — Square Online detection signal "
        "(window.__BOOTSTRAP_STATE__ / squareMerchantId) is not implemented "
        "yet"
    ),
    "Shopify": (
        "Generic Shopify scraper exists, but no marker — adding "
        "cdn.shopify.com or '/collections/' as a marker is a follow-up"
    ),
}


def _parse_platform_sections() -> list[str]:
    """Return the ordered list of `### <Section>` headings under '## Platform Sections'.

    Tracks fenced code blocks so a literal '### ' inside a markdown example does
    not register as a phantom section heading.
    """
    text = _SCRAPERS_MD_PATH.read_text()
    sections: list[str] = []
    in_platform_sections = False
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if line.startswith("## "):
            in_platform_sections = line.strip() == "## Platform Sections"
            continue
        if in_platform_sections and line.startswith("### "):
            sections.append(line[4:].strip())
    return sections


def _audit_marker_violations(sections: list[str]) -> list[str]:
    """Return SCRAPERS.md section names that have no marker AND no exemption."""
    known = (
        set(_PLATFORM_SECTION_MARKER_KEY)
        | set(_EXEMPT_PLATFORM_SECTIONS)
        | _META_PLATFORM_SECTIONS
    )
    return [s for s in sections if s not in known]


def _format_marker_violation_message(violations: list[str]) -> str:
    return (
        "New platform section(s) found in apps/scraper/SCRAPERS.md without a "
        "corresponding entry in audit_tour_date_clubs.py's marker tables OR "
        "in this test's exemption list:\n"
        + "\n".join(f"  - {s}" for s in violations)
        + "\n\nResolve by either (1) adding a marker to _HTML_PLATFORM_MARKERS "
        "or _WEBSITE_DOMAIN_PLATFORMS in audit_tour_date_clubs.py and "
        "recording the (section -> key) pair in _PLATFORM_SECTION_MARKER_KEY, "
        "OR (2) adding the section to _EXEMPT_PLATFORM_SECTIONS with a brief "
        "reason."
    )


def test_parse_platform_sections_returns_known_headings():
    sections = _parse_platform_sections()
    assert sections, (
        "Expected at least one `### ` heading under '## Platform Sections' in "
        "apps/scraper/SCRAPERS.md"
    )
    # Spot-check a few known sections so a parser regression surfaces clearly.
    for expected in ("Eventbrite", "Squarespace", "JSON-LD (Generic Fallback)"):
        assert expected in sections, f"Parser missed '{expected}' section"


def test_every_scrapers_md_section_is_known():
    sections = _parse_platform_sections()
    violations = _audit_marker_violations(sections)
    assert not violations, _format_marker_violation_message(violations)


def test_documented_marker_keys_exist_in_audit_script():
    marker_platforms = {platform for _, platform in mod._HTML_PLATFORM_MARKERS}
    marker_platforms |= set(mod._WEBSITE_DOMAIN_PLATFORMS.values())

    missing = [
        (section, key)
        for section, key in _PLATFORM_SECTION_MARKER_KEY.items()
        if key not in marker_platforms
    ]
    assert not missing, (
        "SCRAPERS.md sections expect these platform keys to exist in "
        "_HTML_PLATFORM_MARKERS or _WEBSITE_DOMAIN_PLATFORMS, but they're "
        "absent:\n"
        + "\n".join(f"  - section '{s}' -> key '{k}'" for s, k in missing)
        + "\n\nEither add the marker to audit_tour_date_clubs.py or update "
        "_PLATFORM_SECTION_MARKER_KEY in this test."
    )


def test_every_audit_marker_platform_is_documented():
    marker_platforms = {platform for _, platform in mod._HTML_PLATFORM_MARKERS}
    marker_platforms |= set(mod._WEBSITE_DOMAIN_PLATFORMS.values())

    documented_platforms = set(_PLATFORM_SECTION_MARKER_KEY.values())
    undocumented = sorted(marker_platforms - documented_platforms)

    assert not undocumented, (
        "audit_tour_date_clubs.py marker table platform(s) are not represented "
        "by any apps/scraper/SCRAPERS.md platform section mapping:\n"
        + "\n".join(f"  - {platform}" for platform in undocumented)
        + "\n\nResolve by either (1) adding a SCRAPERS.md platform section "
        "and recording its (section -> key) pair in "
        "_PLATFORM_SECTION_MARKER_KEY, OR (2) removing the stale marker from "
        "audit_tour_date_clubs.py."
    )


def test_exempt_platform_sections_have_non_empty_reasons():
    blank = [s for s, reason in _EXEMPT_PLATFORM_SECTIONS.items() if not reason.strip()]
    assert not blank, (
        "Exempt section(s) missing a reason in _EXEMPT_PLATFORM_SECTIONS:\n"
        + "\n".join(f"  - {s}" for s in blank)
    )


def test_unknown_section_message_names_the_missing_platform():
    violations = _audit_marker_violations(["Newly Added Platform Without Coverage"])
    assert violations == ["Newly Added Platform Without Coverage"]
    message = _format_marker_violation_message(violations)
    assert "Newly Added Platform Without Coverage" in message
