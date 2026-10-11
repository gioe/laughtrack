"""Actual monitor-store orchestration over a rollback-capable SQL boundary fake.

PostgreSQL constraints/SQL semantics are separately exercised by PGlite.
"""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
import json

import pytest

from laughtrack.core import comedy_eligibility_monitor_store as store
from laughtrack.core.comedy_eligibility_monitor import MonitorConfig, evidence_digest, recommendation, summarize_samples
from laughtrack.core.entities.club.comedy_policy import UPDATE_POLICY_SQL


class Database:
    def __init__(self, policy="comedy_only"):
        self.source = dict(id=1, enabled=True, comedy_policy=policy, comedy_gate_mode="off",
                           comedy_policy_version=1, comedy_reviewed_by="operator",
                           comedy_reviewed_at=None, comedy_review_evidence={"reason": "reviewed"})
        self.samples = [dict(source_id=1, event_key=str(i), payload_fingerprint=f"payload-{i}",
                             identity_fingerprint="identity", policy_version=1,
                             baseline={"decision": "reject", "reason_codes": ["explicit_non_comedy_event"],
                                       "lineup_status": "missing", "performers": []}) for i in range(20)]
        self.reports = []
        self.transitions = []
        self.fail_transition = False
        self.calls = []

    @contextmanager
    def transaction(self):
        saved = deepcopy((self.source, self.samples, self.reports, self.transitions))
        try:
            yield self
        except BaseException:
            self.source, self.samples, self.reports, self.transitions = saved
            raise

    @contextmanager
    def cursor(self):
        yield Cursor(self)


class Cursor:
    def __init__(self, db):
        self.db = db
        self.rows = []
        self.description = []

    def execute(self, sql, params=()):
        d = self.db
        d.calls.append((sql, params))
        rows = []
        if sql.startswith(store.LOAD_SOURCE_SQL):
            rows = [d.source]
        elif sql == "SELECT clock_timestamp() AS as_of":
            rows = [{"as_of": datetime(2026, 10, 11, tzinfo=timezone.utc)}]
        elif sql == store.SAMPLES_AT_SQL:
            rows = d.samples
        elif sql == store.INSERT_REPORT_SQL:
            sid, digest, evidence, config, metrics, advised, source = params
            if not any(r["source_id"] == sid and r["report_digest"] == digest for r in d.reports):
                row = dict(id=len(d.reports)+1, source_id=sid, report_digest=digest, evidence_digest=evidence,
                           config=json.loads(config), metrics=json.loads(metrics), recommendation=json.loads(advised),
                           source_snapshot=json.loads(source))
                d.reports.append(row)
                rows = [{"id": row["id"]}]
        elif sql == store.FIND_REPORT_SQL:
            rows = [r for r in d.reports if (r["source_id"], r["report_digest"]) == params]
        elif sql == store.SUPPRESSED_SQL:
            undone = {t["rollback_of"] for t in d.transitions if t["kind"] == "rollback" and t["source_id"] == params[0]}
            report_ids = {t["report_id"] for t in d.transitions if t["id"] in undone}
            rows = [{"suppressed": any(r["id"] in report_ids and r["evidence_digest"] == params[1] for r in d.reports)}]
        elif sql == store.EXISTING_TRANSITION_SQL:
            rows = [t for t in d.transitions if t["report_id"] == params[0] and t["kind"] == "downgrade"]
        elif sql == UPDATE_POLICY_SQL:
            policy, mode, actor, evidence, sid, expected = params
            if sid == d.source["id"] and expected == d.source["comedy_policy_version"]:
                d.source.update(comedy_policy=policy, comedy_gate_mode=mode, comedy_reviewed_by=actor,
                                comedy_review_evidence=json.loads(evidence), comedy_policy_version=expected+1)
                rows = [d.source]
        elif sql == store.INSERT_TRANSITION_SQL:
            if d.fail_transition:
                raise RuntimeError("history storage failed")
            sid, report, kind, original, actor, reason, before, after = params
            row = dict(id=len(d.transitions)+1, source_id=sid, report_id=report, kind=kind, rollback_of=original,
                       actor=actor, reason=reason, before_state=json.loads(before), after_state=json.loads(after))
            d.transitions.append(row)
            rows = [row]
        elif sql == store.LOAD_TRANSITION_SQL:
            rows = [t for t in d.transitions if t["id"] == params[0]]
        elif sql == store.ROLLBACK_EXISTING_SQL:
            rows = [t for t in d.transitions if t["rollback_of"] == params[0]]
        else:
            raise AssertionError(f"Unexpected SQL: {sql}")
        self.rows = deepcopy(rows)
        self.description = [(key,) for key in (rows[0] if rows else {})]

    def fetchone(self):
        return self.rows.pop(0) if self.rows else None

    def fetchall(self):
        rows, self.rows = self.rows, []
        return rows


def report(db, config=None):
    config = config or MonitorConfig()
    metrics = summarize_samples(db.samples)
    return dict(evidence_digest=evidence_digest(db.samples), config=asdict(config), metrics=metrics,
                recommendation=recommendation(metrics, config), expected_version=db.source["comedy_policy_version"])


def test_monitor_store_downgrade_dedup_and_explicit_rollback_suppression():
    db = Database()
    api = store.MonitorStore(db.transaction)
    first = api.record_report(1, **report(db), apply=True)
    assert first["reason"] == "downgraded"
    assert (db.source["comedy_policy"], db.source["comedy_gate_mode"], db.source["comedy_policy_version"]) == ("mixed", "enforce", 2)
    repeated = api.record_report(1, **report(db), apply=True)
    assert not repeated["new_report"] and len(db.transitions) == 1
    rolled_back = api.rollback(first["transition"]["id"], expected_version=2, actor="reviewer", reason="Observed false alarm")
    assert rolled_back["kind"] == "rollback" and rolled_back["actor"] == "reviewer"
    assert (db.source["comedy_policy"], db.source["comedy_gate_mode"], db.source["comedy_policy_version"]) == ("comedy_only", "off", 3)
    for sample in db.samples:
        sample["policy_version"] = 3
    result = api.record_report(1, **report(db, MonitorConfig(rejection_fraction=.4)), apply=True)
    assert result["reason"] == "rollback_suppressed_same_evidence" and len(db.transitions) == 2
    assert db.source["enabled"] is True


@pytest.mark.parametrize("policy", ["unreviewed", "mixed"])
def test_monitor_store_never_automatically_upgrades(policy):
    db = Database(policy)
    result = store.MonitorStore(db.transaction).record_report(1, **report(db), apply=True)
    assert result["reason"] == "source_not_enabled_comedy_only"
    assert db.source["comedy_policy"] == policy and db.source["comedy_policy_version"] == 1
    assert not db.transitions


def test_monitor_store_refuses_stale_rollback_and_stale_collected_samples():
    db = Database()
    api = store.MonitorStore(db.transaction)
    collected = report(db)
    db.samples[0]["payload_fingerprint"] = "changed-after-collection"
    with pytest.raises(ValueError, match="evidence changed"):
        api.record_report(1, **collected, apply=True)
    assert not db.reports and not db.transitions and db.source["comedy_policy_version"] == 1
    first = api.record_report(1, **report(db), apply=True)
    db.source["comedy_policy_version"] = 3
    with pytest.raises(ValueError, match="Policy changed"):
        api.rollback(first["transition"]["id"], expected_version=3, actor="operator", reason="Restore")
    assert db.source["comedy_policy"] == "mixed" and len(db.transitions) == 1


def test_monitor_store_history_failure_rolls_back_policy_and_report():
    db = Database()
    db.fail_transition = True
    with pytest.raises(RuntimeError, match="history storage failed"):
        store.MonitorStore(db.transaction).record_report(1, **report(db), apply=True)
    assert db.source["comedy_policy"] == "comedy_only" and db.source["comedy_policy_version"] == 1
    assert not db.reports and not db.transitions
