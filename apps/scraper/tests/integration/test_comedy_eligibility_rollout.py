"""Offline rollout controls exercise real policy SQL helper and atomic transactions."""

from contextlib import contextmanager
from copy import deepcopy
from types import SimpleNamespace
import json

import pytest

from scripts.core import rollout_comedy_eligibility as rollout


class Database:
    def __init__(self):
        self.sources = {
            sid: dict(
                id=sid,
                club_id=sid,
                enabled=True,
                scraper_key="seatengine",
                metadata={"keep": "configuration"},
                comedy_policy="unreviewed",
                comedy_gate_mode="off",
                comedy_policy_version=1,
                comedy_reviewed_by=None,
                comedy_reviewed_at=None,
                comedy_review_evidence={},
            )
            for sid in (1, 2)
        }
        self.results = []
        self.writes = 0
        self.missing = set()
        self.fail_metadata = False
        self.history = ["immutable event review"]

    @contextmanager
    def transaction(self):
        before = deepcopy(self.sources)
        try:
            yield self
        except Exception:
            self.sources = before
            raise

    @contextmanager
    def cursor(self):
        yield self

    def execute(self, sql, params):
        if sql.startswith("SELECT * FROM scraping_sources"):
            self.results = [deepcopy(self.sources[i]) for i in sorted(params[0]) if i in self.sources]
        elif "to_regclass" in sql:
            self.results = [{"name": n, "present": n not in self.missing} for n in params[0]]
        elif "SET comedy_policy" in sql:
            policy, mode, actor, evidence, sid, version = params
            row = self.sources[sid]
            if row["comedy_policy_version"] != version:
                self.results = []
                return
            row.update(
                comedy_policy=policy,
                comedy_gate_mode=mode,
                comedy_reviewed_by=actor,
                comedy_review_evidence=json.loads(evidence),
                comedy_policy_version=version + 1,
                comedy_reviewed_at="2026-10-11T00:00:00Z",
            )
            self.results = [deepcopy(row)]
            self.writes += 1
        elif "SET metadata" in sql:
            if self.fail_metadata:
                raise RuntimeError("history write failed")
            path, value, sid = params
            self.sources[sid]["metadata"][path[0]] = json.loads(value)
            self.writes += 1
        else:
            raise AssertionError(sql)

    def fetchall(self):
        return self.results

    def fetchone(self):
        return self.results[0] if self.results else None


def manifest(db):
    return dict(
        rollout_id="pilot-20261011",
        actor="operator",
        reason="reviewed mixed feeds",
        evidence={"artifact": "dated-pilot.json"},
        targets=[
            dict(
                source_id=sid,
                expected_version=1,
                config_fingerprint=rollout.source_fingerprint(row),
                policy="mixed",
                gate_mode="shadow",
            )
            for sid, row in db.sources.items()
        ],
    )


def test_plan_apply_retry_rollback_preserves_history():
    db = Database()
    plan = manifest(db)
    before = deepcopy(db.sources)
    rollout.run(plan, "plan", db.transaction)
    rollout.run(plan, "apply", db.transaction, dry_run=True)
    assert db.sources == before and db.writes == 0
    rollout.run(plan, "apply", db.transaction)
    assert all(r["comedy_gate_mode"] == "shadow" for r in db.sources.values())
    writes = db.writes
    rollout.run(plan, "apply", db.transaction)
    assert db.writes == writes
    rollout.run(plan, "rollback", db.transaction)
    assert all(r["comedy_gate_mode"] == "off" and r["comedy_policy_version"] == 3 for r in db.sources.values())
    writes = db.writes
    rollout.run(plan, "rollback", db.transaction)
    assert db.writes == writes
    assert db.history == ["immutable event review"]
    assert all(r["metadata"]["keep"] == "configuration" and r["enabled"] for r in db.sources.values())


@pytest.mark.parametrize("change", ["version", "config", "disabled", "missing_table", "missing_source"])
def test_entire_cohort_validated_before_any_write(change):
    db = Database()
    plan = manifest(db)
    if change == "version":
        db.sources[2]["comedy_policy_version"] += 1
    elif change == "config":
        db.sources[2]["metadata"]["keep"] = "changed"
    elif change == "disabled":
        db.sources[2]["enabled"] = False
    elif change == "missing_table":
        db.missing.add("comedy_event_observations")
    else:
        del db.sources[2]
    with pytest.raises(ValueError, match="Rollout refused"):
        rollout.run(plan, "apply", db.transaction)
    assert db.writes == 0


def test_history_failure_rolls_back_policy_and_stale_rollback_refuses():
    db = Database()
    plan = manifest(db)
    before = deepcopy(db.sources)
    db.fail_metadata = True
    with pytest.raises(RuntimeError):
        rollout.run(plan, "apply", db.transaction)
    assert db.sources == before
    db.fail_metadata = False
    rollout.run(plan, "apply", db.transaction)
    db.sources[2]["comedy_policy_version"] += 1
    writes = db.writes
    with pytest.raises(ValueError, match="rollback refused"):
        rollout.run(plan, "rollback", db.transaction)
    assert db.writes == writes


def test_enforcement_needs_explicit_go_and_duplicate_manifest_is_rejected():
    db = Database()
    plan = manifest(db)
    plan["targets"][0]["gate_mode"] = "enforce"
    with pytest.raises(ValueError, match="go decision"):
        rollout.run(plan, "apply", db.transaction)
    plan["evidence"]["go_no_go"] = "go"
    rollout.run(plan, "apply", db.transaction)
    altered = deepcopy(plan)
    altered["reason"] = "different request"
    with pytest.raises(ValueError, match="already used"):
        rollout.run(altered, "apply", db.transaction)


def test_seatengine_original_talents_survive_filtered_lineup():
    from laughtrack.core.comedy_eligibility_gate import capture_event_inputs

    show = SimpleNamespace(
        eligibility_performer_names=["Filtered survivor"],
        eligibility_raw_performers_preserved=False,
        eligibility_evidence=[],
        lineup=["Filtered survivor"],
    )
    capture_event_inputs(show, {"id": 3, "event": {"talents": [{"name": "Blocked band"}, {"name": "Show label"}]}})
    assert show.eligibility_performer_names == ["Blocked band", "Show label"]
    assert show.eligibility_raw_performers_preserved
    assert show.lineup == ["Filtered survivor"]
    for talents in (None, {}, [None], [{"name": "Valid"}, {"name": None}]):
        capture_event_inputs(show, {"id": 3, "event": {"talents": talents}})
        assert not show.eligibility_raw_performers_preserved
    assert show.eligibility_performer_names == ["Valid"]


def test_pipeline_uses_original_seatengine_event_after_transformer_filters(monkeypatch):
    from laughtrack.utilities.infrastructure.pipeline.pipeline import ShowTransformationPipeline

    original = {"id": 9, "event": {"talents": [{"name": "Removed label"}, {"name": "Survivor"}]}}
    show = SimpleNamespace(
        eligibility_performer_names=[],
        eligibility_raw_performers_preserved=False,
        eligibility_evidence=[],
        lineup=["Survivor"],
        source_performance_id=None,
    )
    pipeline = ShowTransformationPipeline(SimpleNamespace(name="Synthetic mixed venue"))
    pipeline.register_transformer(SimpleNamespace(can_transform=lambda raw: True, transform_to_show=lambda raw: show))
    monkeypatch.setattr(pipeline, "_warn_if_ticketless", lambda show: None)
    assert pipeline.transform(SimpleNamespace(event_list=[original])) == [show]
    assert show.eligibility_performer_names == ["Removed label", "Survivor"]
    assert show.eligibility_raw_performers_preserved
    assert show.lineup == ["Survivor"]
    assert show.source_performance_id is None

    missing = SimpleNamespace(
        eligibility_performer_names=[], eligibility_raw_performers_preserved=False, eligibility_evidence=[]
    )
    from laughtrack.core.comedy_eligibility_gate import capture_event_inputs

    capture_event_inputs(missing, {"id": 10, "event": {}})
    assert not missing.eligibility_raw_performers_preserved


def test_captured_blocked_alias_resolves_parent_without_becoming_comedy_proof():
    from laughtrack.core.comedy_eligibility import CanonicalPerson, PerformerObservation, classify_comedy_eligibility
    from laughtrack.core.comedy_eligibility_gate import capture_event_inputs
    from laughtrack.core.entities.club.comedy_policy import SourceComedyPolicy

    show = SimpleNamespace(
        eligibility_performer_names=[], eligibility_raw_performers_preserved=False, eligibility_evidence=[]
    )
    capture_event_inputs(show, {"event": {"talents": [{"name": "Blocked alias"}]}})
    result = classify_comedy_eligibility(
        source_id=1,
        policy=SourceComedyPolicy(),
        performers=[PerformerObservation(name) for name in show.eligibility_performer_names],
        people=[CanonicalPerson(1, "Blocked alias", False, 2, "duplicate"), CanonicalPerson(2, "Root", True)],
    )
    assert result.decision == "review" and result.blocked_count == 0
    assert "canonical_parent_resolved" in result.reason_codes
