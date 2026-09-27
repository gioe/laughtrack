"""Production-shaped input fixtures for the read-only recurring audit."""

from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("audit_scraping_data", ROOT / "scripts/core/audit_scraping_data.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
NOW = datetime(2030, 6, 1, tzinfo=timezone.utc)
UNTIL = NOW + timedelta(days=30)


def show(id=1, **values):
    row = dict(
        id=id,
        club_id=10,
        name="A real performance",
        date=NOW + timedelta(days=1),
        room="Main",
        show_page_url=f"https://tickets.example/events/{id}",
        last_scraped_date=NOW,
        last_scraped_by="venue_scraper",
        scraped_by_organizer_id=None,
        zip_code="10001",
        country="US",
        club_type="club",
        timezone="America/New_York",
        has_enabled_source=True,
    )
    row.update(values)
    return row


def report(**data):
    return audit.analyze_snapshot(data, as_of=NOW, until=UNTIL)


def test_customer_facing_anomaly_metrics():
    shows = [
        show(1),
        show(2, club_id=11, show_page_url="https://tickets.example/events/1"),
        show(
            3, show_page_url="https://tickets.example/events/3", room="Old", last_scraped_date=NOW - timedelta(days=30)
        ),
        show(4, show_page_url="https://tickets.example/events/3", room="New"),
        show(5, club_id=12, zip_code=None),
        show(6, club_id=12, zip_code=""),
    ]
    metrics = report(
        shows=shows,
        lineups=[
            {"comedian_id": 99, "name": "School Girls; OR, The African Mean Girls Play", "show_id": 1},
            {"comedian_id": 99, "name": "School Girls; OR, The African Mean Girls Play", "show_id": 2},
            {"comedian_id": 100, "name": "Sarah Silverman", "show_id": 1},
        ],
    )["metrics"]
    assert metrics["suspicious_lineup_identities"]["count"] == 1
    assert metrics["suspicious_lineup_identities"]["affected_show_count"] == 2
    assert metrics["cross_venue_event_candidates"]["affected_show_count"] == 2
    assert metrics["stale_room_duplicate_candidates"]["affected_show_count"] == 2
    assert metrics["missing_zip_us"]["count"] == 1
    assert metrics["missing_zip_us"]["affected_show_count"] == 2


def test_different_event_ids_and_shared_calendars_are_not_duplicates():
    rows = [
        show(1, room="Old"),
        show(2, room="New"),
        show(3, show_page_url="https://venue.example/calendar", club_id=20),
        show(4, show_page_url="https://venue.example/calendar", club_id=21),
    ]
    metrics = report(shows=rows)["metrics"]
    assert metrics["cross_venue_event_candidates"]["count"] == 0
    assert metrics["room_duplicate_candidates"]["count"] == 0
    assert audit.event_identity("https://www.eventbrite.com/e/old-title-12345") == audit.event_identity(
        "https://eventbrite.com/e/new-title-12345"
    )
    assert audit.event_identity("https://sesh.example/event-detail.php?id=12") != audit.event_identity(
        "https://sesh.example/event-detail.php?id=13"
    )


def test_timezone_and_aggregate_confounds():
    rows = [
        show(1, timezone=None, has_enabled_source=False, last_scraped_by="next_stop_comedy"),
        show(2, timezone="UTC"),
        show(3, timezone="Not/AZone"),
        show(4),
    ]
    metrics = report(shows=rows)["metrics"]
    assert metrics["unknown_local_time"]["sample_show_ids"] == [1, 3]
    assert metrics["local_midnight_candidates"]["sample_show_ids"] == [2]
    assert metrics["aggregate_covered_without_direct_source"]["sample_show_ids"] == [1]
    assert metrics["unverified_source_coverage"]["count"] == 0


def test_run_health_recovery_classification():
    base = dict(success=True, errors=0, fetches_failed=0, fetches_ok=2, num_shows=10, bot_block_detected=True)
    rows = [
        dict(base, club_id=1),
        dict(base, club_id=2, num_shows=0),
        dict(base, club_id=3, fetches_failed=1),
        dict(base, club_id=4, num_shows=0, bot_block_detected=False, success=False),
        {"club_id": 5, "num_shows": 10, "success": True},
    ]
    metrics = report(runs=rows)["metrics"]
    for category in ["recovered_productive", "blocked_empty", "partial_productive", "failed", "unknown"]:
        assert metrics["run_health_" + category]["count"] == 1
    assert metrics["run_health_healthy_productive"]["count"] == 0


def test_social_identity_review_preserves_distinct_roots_and_linked_aliases():
    rows = [
        dict(id=735, parent_comedian_id=None, instagram_account="sarahennessey", show_ids=[1]),
        dict(id=165737, parent_comedian_id=None, instagram_account=" @SaraHennessey ", show_ids=[]),
        dict(id=1, parent_comedian_id=None, instagram_account="realcomic", show_ids=[2]),
        dict(id=2, parent_comedian_id=1, parent_visible=True, instagram_account="realcomic", show_ids=[3]),
        dict(id=3, parent_comedian_id=4, parent_visible=False, show_ids=[4]),
    ]
    original = json.dumps(rows, sort_keys=True)
    metrics = report(shows=[show(i) for i in range(1, 5)], identities=rows)["metrics"]
    assert metrics["unlinked_social_handle_identities"]["sample_ids"] == [735, 165737]
    assert metrics["unlinked_social_handle_identities"]["affected_show_count"] == 1
    assert metrics["visible_alias_hidden_parent"]["sample_ids"] == [3]
    assert metrics["visible_alias_hidden_parent"]["affected_show_count"] == 1
    assert json.dumps(rows, sort_keys=True) == original


def test_podcast_duration_policy_and_provenance():
    def group(id, lo, hi, count):
        return dict(
            podcast_id=id,
            source="podcast_index",
            provenance="rss_duration_evidence",
            minimum_seconds=lo,
            maximum_seconds=hi,
            episode_count=count,
            sample_episode_id=id,
        )

    data = [group(1, 86401, 3000000, 1002), group(2, 21601, 86400, 282), group(3, 0, 0, 1301)]
    metrics = report(durations=data)["metrics"]
    assert metrics["podcast_duration_over_day"]["count"] == 1002
    assert metrics["podcast_duration_valid_long_form"]["count"] == 282
    assert metrics["podcast_duration_valid_long_form"]["status"] == "info"
    assert metrics["podcast_duration_nonpositive"]["count"] == 1301
    assert metrics["podcast_duration_over_day"]["groups"][0]["provenance"] == "rss_duration_evidence"


def test_exports_allowlist_fields_and_never_retain_nested_credentials():
    secret = "SYNTHETIC-DO-NOT-EXPORT"
    metadata = {"api_key": secret, "nested": {"password": secret, "token": secret}}
    row = show(
        1, metadata=metadata, source_payload=metadata, show_page_url="https://tickets.example/events/1?token=" + secret
    )
    data = report(
        shows=[row], sources=[metadata], runs=[dict(club_id=1, num_shows=0, metadata=metadata, error_message=secret)]
    )
    encoded = json.dumps(data)
    assert secret not in encoded
    assert "api_key" not in encoded and "source_payload" not in encoded


def test_examples_are_bounded_without_truncating_counts():
    data = {"shows": [show(i, zip_code=None, club_id=i) for i in range(30)]}
    result = audit.analyze_snapshot(data, as_of=NOW, until=UNTIL, sample_limit=3)
    metric = result["metrics"]["missing_zip_us"]
    assert metric["count"] == 30 and metric["affected_show_count"] == 30
    assert len(metric["sample_ids"]) == len(metric["sample_show_ids"]) == 3


def test_cli_writes_same_safe_report_and_returns_zero_for_findings(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(
        audit, "collect_snapshot", lambda now, until: {"shows": [show(date=now + timedelta(days=1), zip_code=None)]}
    )
    target = tmp_path / "report.json"
    assert audit.main(["--json", "--output", str(target)]) == 0
    assert json.loads(target.read_text()) == json.loads(capsys.readouterr().out)


def test_cli_failure_does_not_leak_driver_credentials(monkeypatch, capsys):
    def broken(*args):
        raise RuntimeError("postgres://user:SYNTHETIC-PASSWORD@host")

    monkeypatch.setattr(audit, "collect_snapshot", broken)
    assert audit.main(["--json"]) == 1
    captured = capsys.readouterr()
    assert not captured.out
    assert "SYNTHETIC" not in captured.err


def test_collection_uses_read_only_repeatable_snapshot(monkeypatch):
    calls = []

    class Cursor:
        description = []

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def execute(self, sql, params=None):
            calls.append(sql)

        def fetchall(self):
            return []

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def cursor(self):
            return Cursor()

        def rollback(self):
            calls.append("ROLLBACK")

    def connect(**kwargs):
        assert kwargs == {"autocommit": False}
        return Connection()

    monkeypatch.setattr(audit, "get_connection", connect)
    audit.collect_snapshot(NOW, UNTIL)
    assert calls[0] == "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"
    assert calls[-1] == "ROLLBACK"


def test_global_validation_failures_are_reported_without_club_attribution():
    result = report(persistence=[dict(run_id=1473, run_type="scraper", shows_saved=200, shows_validation_failed=80)])
    assert result["metrics"]["run_persistence_failures"]["count"] == 1
    assert result["metrics"]["run_persistence_failures"]["affected_show_count"] == 0
    assert result["run_persistence"][0]["shows_validation_failed"] == 80


def test_one_recent_aggregate_write_establishes_venue_coverage():
    rows = [
        show(1, has_enabled_source=False, last_scraped_by="next_stop_comedy"),
        show(2, has_enabled_source=False, last_scraped_date=NOW - timedelta(days=30)),
    ]
    metrics = report(shows=rows)["metrics"]
    assert metrics["aggregate_covered_without_direct_source"]["affected_show_count"] == 2
    assert metrics["unverified_source_coverage"]["count"] == 0
