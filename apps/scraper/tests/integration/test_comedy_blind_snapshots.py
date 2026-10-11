"""Blind collection boundaries and cumulative evidence integrity."""

import asyncio
import ast
import json
from pathlib import Path

import pytest

from scripts.core import collect_comedy_blind_snapshots as collector


@pytest.fixture
def baseline():
    return json.loads(collector.BASELINE.read_text())


def event(eid, oid=1, venue="53"):
    return {
        "id": oid,
        "event": {
            "id": eid,
            "name": "Unlabeled program",
            "venue_id": venue,
            "talents": [{"id": 3, "name": "Raw artist", "secret": "never copy"}],
        },
        "start_date_time": "2027-01-01T20:00:00Z",
        "csrf": "never copy",
    }


class Client:
    headers = {}

    def __init__(self, sid, events):
        self.sid, self.events = sid, events
        self.detail_calls = 0

    async def fetch_json(self, url, headers):
        return {"data": self.events}

    async def fetch_venue_details(self, venue):
        return {"website": "https://goodnightscomedy.com"}

    def _build_public_show_url(self, oid):
        return f"https://goodnightscomedy.com/shows/{oid}"

    async def collect_event_descriptions(self, events):
        self.detail_calls += 1
        return [
            {
                **e,
                "_comedy_event_detail": {
                    "status": "collected",
                    "text": "Unlabeled event description",
                    "event_id": str(e["event"]["id"]),
                    "show_id": str(e["id"]),
                    "csrf": "never copy",
                },
            }
            for e in events
        ]


def clients(events):
    return {sid: Client(sid, events if sid == 192 else []) for sid in collector.COHORT}


def test_exclusions_distinct_groups_and_immutable_repeated_runs(baseline):
    old = next(int(e["event_id"]) for e in baseline["excluded_groups"] if e["source_id"] == 192)
    cs = clients([event(old), event(999001, 2), event(999001, 3)])
    history, report = asyncio.run(collector.collect(cs, baseline, None, "first"))
    assert report["new_groups"] == 1
    assert len(history["snapshots"][0]["evidence"]["provider_occurrences"]) == 2
    assert "never copy" not in json.dumps(history)
    frozen = json.dumps(history, sort_keys=True)
    repeated, report = asyncio.run(collector.collect(clients([event(999001, 4)]), baseline, history, "second"))
    assert report["new_groups"] == 0
    assert repeated["snapshots"] == history["snapshots"]
    assert json.dumps(history, sort_keys=True) == frozen
    assert len(repeated["runs"]) == 2
    with pytest.raises(ValueError, match="Run identity"):
        asyncio.run(collector.collect(cs, baseline, repeated, "second"))


def test_digest_baseline_and_duplicate_history_rejected(baseline):
    history, _ = asyncio.run(collector.collect(clients([event(999001)]), baseline, None, "first"))
    history["snapshots"][0]["evidence"]["detail"]["text"] = "changed"
    with pytest.raises(ValueError, match="digest"):
        collector.load_history(baseline, history)
    with pytest.raises(ValueError, match="baseline/version"):
        collector.load_history(baseline, {"version": 0})
    with pytest.raises(ValueError, match="173"):
        collector.load_history({"excluded_groups": []})


def test_group_budget_and_detail_failure_are_explicit(baseline):
    class FailedDetail(Client):
        async def collect_event_descriptions(self, events):
            return [{**e, "_comedy_event_detail": {"status": "failed", "error_type": "TimeoutError"}} for e in events]

    cs = clients([])
    cs[192] = FailedDetail(192, [event(999000 + i, i + 1) for i in range(51)])
    history, report = asyncio.run(collector.collect(cs, baseline, None, "first"))
    assert len(history["snapshots"]) == 50
    assert report["sources"][0]["deferred_by_budget"] == 1
    assert report["sources"][0]["detail_status"] == {"failed": 50}


def test_calendar_timeout_and_wrong_venue_abort_without_history_mutation(baseline):
    class Failed(Client):
        async def fetch_json(self, *args, **kwargs):
            raise asyncio.TimeoutError

    prior = collector.load_history(baseline)
    cs = clients([])
    cs[192] = Failed(192, [])
    with pytest.raises(asyncio.TimeoutError):
        asyncio.run(collector.collect(cs, baseline, prior, "first"))
    assert prior["runs"] == []
    with pytest.raises(ValueError, match="identity/venue"):
        asyncio.run(collector.collect(clients([event(999001, venue="451")]), baseline, prior, "first"))


def test_source_identity_and_routing_fail_closed():
    row = {
        "id": 192,
        "club_id": 61,
        "enabled": True,
        "scraper_key": "seatengine",
        "platform": "seatengine",
        "seatengine_id": 53,
        "metadata": {},
        "source_url": "https://goodnightscomedy.com",
    }
    assert collector.validate_source(row).id == 192
    for delta in (
        {"club_id": 62},
        {"enabled": False},
        {"seatengine_id": 54},
        {"metadata": {"seatengine_venue_routes": {}}},
        {"source_target_id": 99},
    ):
        with pytest.raises(ValueError):
            collector.validate_source({**row, **delta})


def test_artifact_restore_requires_bootstrap_and_existing_latest_archive(tmp_path, monkeypatch):
    monkeypatch.setattr(collector, "gh", lambda args: json.dumps([{"workflow_runs": []}]))
    with pytest.raises(ValueError, match="bootstrap"):
        collector.restore("gioe/laughtrack", tmp_path / "missing")
    collector.restore("gioe/laughtrack", tmp_path / "first", bootstrap=True)
    assert (tmp_path / "first/bootstrap.json").exists()

    def missing(args):
        return (
            json.dumps([{"workflow_runs": [{"id": 5, "run_number": 1}]}])
            if "--paginate" in args
            else json.dumps({"artifacts": []})
        )

    monkeypatch.setattr(collector, "gh", missing)
    with pytest.raises(ValueError, match="missing/expired"):
        collector.restore("gioe/laughtrack", tmp_path / "lost", bootstrap=True)


def test_readonly_boundary_and_no_classifier_imports():
    source = Path(collector.__file__).read_text()
    tree = ast.parse(source)
    imports = [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    assert not any("eligibility" in name or "show.handler" in name or "review_store" in name for name in imports)
    assert "READ ONLY" in source
    assert "ShowHandler" not in source


def test_local_evidence_cannot_be_overwritten(tmp_path):
    path = tmp_path / "evidence.json"
    collector.write_new(path, {"one": 1})
    with pytest.raises(FileExistsError):
        collector.write_new(path, {"one": 2})
    assert json.loads(path.read_text()) == {"one": 1}


def test_restore_uses_latest_success_and_exact_immutable_attempt(tmp_path, monkeypatch, baseline):
    calls = []
    prior = collector.load_history(baseline)

    def fake_gh(args):
        calls.append(args)
        if "--paginate" in args:
            return json.dumps(
                [
                    {
                        "workflow_runs": [
                            {"id": 100, "run_number": 7, "run_attempt": 2},
                            {"id": 101, "run_number": 6, "run_attempt": 1},
                        ]
                    }
                ]
            )
        if args[0] == "api":
            return json.dumps({"artifacts": [{"name": "comedy-blind-history-100-2", "expired": False}]})
        Path(args[-1], "history.json").write_text(json.dumps(prior))
        return ""

    monkeypatch.setattr(collector, "gh", fake_gh)
    collector.restore("gioe/laughtrack", tmp_path / "prior")
    assert calls[-1][2] == "100"
    assert "comedy-blind-history-100-2" in calls[-1]
    assert collector.load_history(baseline, json.loads((tmp_path / "prior/history.json").read_text())) == prior


def test_public_url_with_secret_query_is_never_fetched(baseline):
    cs = clients([event(999001)])
    cs[192]._build_public_show_url = lambda oid: f"https://goodnightscomedy.com/shows/{oid}?token=secret"
    with pytest.raises(ValueError, match="Unreviewed public event URL"):
        asyncio.run(collector.collect(cs, baseline, None, "first"))
    assert cs[192].detail_calls == 0
