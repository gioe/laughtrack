"""Source-quality aggregation and passive collection contracts, offline only."""

from dataclasses import asdict
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock

from laughtrack.core.comedy_eligibility_monitor import (
    MonitorConfig,
    evidence_digest,
    evaluate_source,
    observe_show,
    recommendation,
    summarize_samples,
)


def sample(index, verdict="reject", **changes):
    baseline = {
        "decision": verdict,
        "lineup_status": "missing",
        "performers": [],
        "reason_codes": ["explicit_non_comedy_event"] if verdict == "reject" else [],
        "raw_lineup_complete": False,
        "policy_version": 1,
        "policy": "unreviewed",
    }
    return {
        "source_id": 7,
        "event_key": f"event:{index}",
        "payload_fingerprint": f"payload:{index}",
        "identity_fingerprint": "identity",
        "baseline": baseline,
        "last_seen_at": datetime(2026, 10, 11, tzinfo=timezone.utc),
        **changes,
    }


def test_contract_1():
    rows = [sample(0), sample(1, "accept"), sample(2, "review")]
    duplicate = {**rows[0], "last_seen_at": rows[0]["last_seen_at"] + timedelta(minutes=1)}
    metrics = summarize_samples([*rows, duplicate])
    assert metrics["event_count"] == 3
    assert metrics["decisions"]["reject"] == {"count": 1, "denominator": 3, "fraction": 1 / 3}
    assert metrics["coverage"]["missing"]["count"] == 3
    assert metrics["blocked_appearances"]["fraction"] is None
    assert evidence_digest(rows) == evidence_digest([duplicate, *rows[1:]])
    version_changed = [{**r, "policy_version": 4, "baseline": {**r["baseline"], "policy_version": 4}} for r in rows]
    assert evidence_digest(rows) == evidence_digest(version_changed)
    assert evidence_digest(rows) != evidence_digest([*rows, sample(3)])
    assert "no_observations_telemetry_gap" in recommendation(summarize_samples([]), MonitorConfig())["reasons"]
    people = [
        {"state": "unblocked", "canonical_id": 11, "diagnostics": ["canonical_parent_resolved"]},
        {"state": "unknown", "canonical_id": None},
    ]
    metrics = summarize_samples(
        [sample(0, "review", baseline={"decision": "review", "lineup_status": "partial", "performers": people})]
    )
    assert metrics["blocked_appearances"]["count"] == 0
    assert metrics["unresolved_appearances"] == {"count": 1, "denominator": 2, "fraction": 0.5}


def test_contract_2(monkeypatch):
    from laughtrack.core import comedy_eligibility_gate as gate
    from laughtrack.core import comedy_eligibility_monitor_store as storage
    from tests.integration.test_comedy_eligibility_gate import _gate_environment, _gate_show, _writer_handler

    config = MonitorConfig()
    assert config.auto_downgrade is False
    assert not recommendation(summarize_samples([sample(i) for i in range(19)]), config)["downgrade"]
    assert not recommendation(summarize_samples([sample(i, "review") for i in range(30)]), config)["downgrade"]
    assert recommendation(summarize_samples([sample(i, "reject" if i < 5 else "accept") for i in range(20)]), config)[
        "downgrade"
    ]
    state = _gate_environment(monkeypatch, "off")
    state.source["comedy_policy"] = "comedy_only"
    state.source["comedy_reviewed_by"] = "operator"
    state.source["comedy_reviewed_at"] = datetime.now(timezone.utc)
    state.source["comedy_review_evidence"] = {"review": "Source checked"}
    handler = _writer_handler(monkeypatch, state)
    monkeypatch.setattr(gate, "observe_show", observe_show)
    recorded = []
    monkeypatch.setattr(storage, "record_sample", lambda cursor, **row: recorded.append(row))
    shows = [_gate_show(name="Live music", source_performance_id=f"event:{i}", room=f"Room {i}") for i in range(3)]
    result = handler._process_single_batch(shows)
    assert result.eligibility_withheld == 0 and len(recorded) == 3
    assert all(row["baseline"]["decision"] == "reject" for row in recorded)
    assert not state.staged  # Monitor samples do not turn off mode into admission.
    handler._process_single_batch([_gate_show(name="Unknown evening", source_performance_id="unknown")])
    assert recorded[-1]["baseline"]["decision"] == "review"  # Trust does not count as affirmative evidence.
    monkeypatch.setattr(storage, "record_sample", Mock(side_effect=RuntimeError("monitor tables unavailable")))
    result = handler._process_single_batch([_gate_show()])
    assert result.eligibility_withheld == 0
    assert any("ROLLBACK TO SAVEPOINT" in sql for sql, _ in state.calls)


def test_contract_3(monkeypatch, capsys):
    import json
    import pytest
    from contextlib import contextmanager
    from scripts.core.monitor_comedy_eligibility import main
    from laughtrack.core import comedy_eligibility_monitor_store as storage

    samples = [sample(i) for i in range(20)]
    store = Mock()
    store.load_snapshot.return_value = {"source": {"comedy_policy_version": 1}, "samples": samples}
    store.record_report.return_value = {"report_id": 1, "new_report": False, "transition": None}
    evaluate_source(store, 7)
    assert store.record_report.call_args.kwargs["apply"] is False
    assert store.record_report.call_args.kwargs["recommendation"]["downgrade"] is True
    store.sources.return_value = []
    main(["report"], store=store)
    assert json.loads(capsys.readouterr().out)["status"] == "no_monitored_sources"
    store.rollback.return_value = {"reason": "rolled_back"}
    main(
        [
            "rollback",
            "--transition-id",
            "1",
            "--expected-version",
            "2",
            "--actor",
            "operator",
            "--reason",
            "Pilot evidence reviewed",
        ],
        store=store,
    )
    store.rollback.assert_called_once_with(1, expected_version=2, actor="operator", reason="Pilot evidence reviewed")
    # The actual store revalidates samples under the source lock before any report or transition.
    cursor = Mock()
    cursor.__enter__ = Mock(return_value=cursor)
    cursor.__exit__ = Mock(return_value=False)
    connection = Mock()
    connection.cursor.return_value = cursor

    @contextmanager
    def transaction():
        yield connection

    rows = iter([{"comedy_policy_version": 1}, {"as_of": datetime.now(timezone.utc)}])
    monkeypatch.setattr(storage, "_row", lambda cur: next(rows))
    monkeypatch.setattr(storage, "_rows", lambda cur: [sample(0)])
    with pytest.raises(ValueError, match="changed"):
        storage.MonitorStore(transaction).record_report(
            7,
            evidence_digest=evidence_digest(samples),
            config=asdict(MonitorConfig()),
            metrics=summarize_samples(samples),
            recommendation=recommendation(summarize_samples(samples), MonitorConfig()),
            expected_version=1,
            apply=True,
        )
    assert not any(
        "INSERT" in call.args[0] or "UPDATE scraping_sources" in call.args[0] for call in cursor.execute.call_args_list
    )
    _exercise_transition_lifecycle(monkeypatch)


def test_source_evaluation_after_publication_and_empty_run(monkeypatch):
    from types import SimpleNamespace
    from laughtrack.core.models.results import ClubScrapingResult
    from laughtrack.foundation.models.operation_result import DatabaseOperationResult
    from laughtrack.utilities.domain.scraper.result import ScrapingResultProcessor
    from laughtrack.core import comedy_eligibility_monitor as monitor

    order = []
    handler = SimpleNamespace(transaction=Mock())
    processor = ScrapingResultProcessor.__new__(ScrapingResultProcessor)
    processor.show_service = SimpleNamespace(
        show_handler=handler, insert_shows=lambda *a, **kw: (order.append("published"), DatabaseOperationResult())[1]
    )
    processor._reconcile_stale_future_shows = lambda *args: order.append("reconciled")
    monkeypatch.setattr(monitor, "evaluate_completed_source", lambda tx, sid: order.append(("evaluated", sid)))
    result = ClubScrapingResult("Feed", [object()], 1.0, eligibility_source_id=7)
    processor.insert_club_result(result)
    assert order == ["published", "reconciled", ("evaluated", 7)]
    order.clear()
    processor.insert_club_result(ClubScrapingResult("National feed", [], 1.0, eligibility_source_id=9))
    assert order == ["reconciled", ("evaluated", 9)]


def _exercise_transition_lifecycle(monkeypatch):
    """Execute real store control flow with an isolated SQL-dispatch transaction.

    Postgres constraints/rollback are additionally covered by the PGlite suite.
    This fixture checks Python policy branches and rerun semantics end to end.
    """
    import json
    import pytest
    from contextlib import contextmanager
    from dataclasses import replace
    from laughtrack.core import comedy_eligibility_monitor_store as storage

    class Database:
        def __init__(self):
            self.source = {
                "id": 7,
                "enabled": True,
                "comedy_policy": "comedy_only",
                "comedy_gate_mode": "off",
                "comedy_policy_version": 1,
                "comedy_reviewed_by": "operator",
                "comedy_reviewed_at": None,
                "comedy_review_evidence": {"initial": True},
            }
            self.samples = [sample(i) for i in range(20)]
            self.reports = []
            self.transitions = []
            self.writes = []
            self.result = []

        def execute(self, sql, params=()):
            self.result = []
            if sql.startswith(storage.LOAD_SOURCE_SQL):
                self.result = [dict(self.source)]
            elif sql == "SELECT clock_timestamp() AS as_of":
                self.result = [{"as_of": datetime.now(timezone.utc)}]
            elif sql == storage.SAMPLES_AT_SQL:
                self.result = self.samples
            elif sql == storage.INSERT_REPORT_SQL:
                if not any(r["report_digest"] == params[1] for r in self.reports):
                    row = {"id": len(self.reports) + 1, "report_digest": params[1], "evidence_digest": params[2]}
                    self.reports.append(row)
                    self.result = [row]
            elif sql == storage.FIND_REPORT_SQL:
                self.result = [r for r in self.reports if r["report_digest"] == params[1]]
            elif sql == storage.SUPPRESSED_SQL:
                self.result = [
                    {
                        "suppressed": any(
                            t["kind"] == "rollback"
                            and any(
                                r["id"] == t["report_id"] and r["evidence_digest"] == params[1] for r in self.reports
                            )
                            for t in self.transitions
                        )
                    }
                ]
            elif sql == storage.EXISTING_TRANSITION_SQL:
                self.result = [t for t in self.transitions if t["report_id"] == params[0] and t["kind"] == "downgrade"]
            elif sql == storage.INSERT_TRANSITION_SQL:
                row = dict(
                    zip(
                        (
                            "source_id",
                            "report_id",
                            "kind",
                            "rollback_of",
                            "actor",
                            "reason",
                            "before_state",
                            "after_state",
                        ),
                        params,
                    )
                )
                row.update(
                    id=len(self.transitions) + 1,
                    before_state=json.loads(row["before_state"]),
                    after_state=json.loads(row["after_state"]),
                )
                self.transitions.append(row)
                self.result = [row]
            elif sql == storage.LOAD_TRANSITION_SQL:
                self.result = [t for t in self.transitions if t["id"] == params[0]]
            elif sql == storage.ROLLBACK_EXISTING_SQL:
                self.result = [t for t in self.transitions if t["rollback_of"] == params[0]]
            else:
                raise AssertionError(f"Unexpected monitor SQL: {sql}")

        def save(self, cursor, source_id, policy):
            assert source_id == self.source["id"] and policy.version == self.source["comedy_policy_version"]
            self.writes.append(policy)
            self.source.update(
                comedy_policy=policy.policy,
                comedy_gate_mode=policy.gate_mode,
                comedy_policy_version=policy.version + 1,
                comedy_reviewed_by=policy.reviewed_by,
                comedy_review_evidence=policy.evidence,
            )
            return replace(policy, version=policy.version + 1)

        def cursor(self):
            return self

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    db = Database()

    @contextmanager
    def transaction():
        yield db

    monkeypatch.setattr(storage, "_row", lambda cur: cur.result[0] if cur.result else None)
    monkeypatch.setattr(storage, "_rows", lambda cur: list(cur.result))
    monkeypatch.setattr(storage, "save_source_comedy_policy", db.save)
    store = storage.MonitorStore(transaction)
    report = evaluate_source(store, 7, apply=False)
    assert report["new_report"] and not db.writes
    repeat = evaluate_source(store, 7, apply=False)
    assert not repeat["new_report"] and repeat["report_id"] == report["report_id"]
    downgraded = evaluate_source(store, 7, apply=True)
    assert downgraded["reason"] == "downgraded"
    assert (db.source["comedy_policy"], db.source["comedy_gate_mode"], db.source["comedy_policy_version"]) == (
        "mixed",
        "enforce",
        2,
    )
    assert db.source["id"] == 7 and db.source["enabled"] is True
    assert len(db.writes) == 1 and len(db.transitions) == 1
    evaluate_source(store, 7, apply=True)
    assert len(db.writes) == 1  # Never upgrade a mixed source or repeat the downgrade.
    with pytest.raises(ValueError, match="changed"):
        store.rollback(1, expected_version=1, actor="operator", reason="Review correction")
    store.rollback(1, expected_version=2, actor="operator", reason="Review correction")
    assert (db.source["comedy_policy"], db.source["comedy_gate_mode"], db.source["comedy_policy_version"]) == (
        "comedy_only",
        "off",
        3,
    )
    assert db.transitions[-1]["actor"] == "operator"
    suppressed = evaluate_source(store, 7, apply=True)
    assert suppressed["reason"] == "rollback_suppressed_same_evidence" and len(db.writes) == 2
    with pytest.raises(ValueError, match="already"):
        store.rollback(1, expected_version=3, actor="operator", reason="Repeat")
    # New evidence may create a new report; unreviewed sources still cannot upgrade.
    db.samples.append(sample(21))
    db.source["comedy_policy"] = "unreviewed"
    assert evaluate_source(store, 7, apply=True)["reason"] == "source_not_enabled_comedy_only"
    assert len(db.writes) == 2
