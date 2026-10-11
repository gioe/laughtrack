"""Saved pilot replay uses actual transformers with no network/public writers."""

from contextlib import contextmanager
from copy import deepcopy

import pytest
from scripts.core import pilot_comedy_eligibility as pilot


class ReadDatabase:
    def __init__(self):
        self.source = dict(
            id=1,
            club_id=2,
            platform="seatengine",
            scraper_key="seatengine",
            seatengine_id=3,
            source_url="https://example.com",
            metadata={},
            enabled=True,
            comedy_policy="mixed",
            comedy_gate_mode="shadow",
            comedy_policy_version=2,
        )
        self.rows = []
        self.statements = []

    @contextmanager
    def transaction(self):
        yield self

    @contextmanager
    def cursor(self):
        yield self

    def execute(self, sql, params):
        self.statements.append(sql)
        assert sql.startswith("SELECT"), "Default pilot must not write"
        if "scraping_sources" in sql:
            self.rows = [deepcopy(self.source)]
        elif "FROM clubs" in sql:
            self.rows = [dict(id=2, name="Synthetic venue", website="https://example.com", timezone="America/New_York")]
        else:
            raise AssertionError(sql)

    def fetchall(self):
        return self.rows


def saved():
    event = dict(
        id=44,
        start_date_time="2027-01-01T20:00:00Z",
        sold_out=False,
        event=dict(id=5, name="Stand-up comedy night", talents=[dict(name="An alias")]),
        inventories=[dict(price=2500, title="General admission", active=True)],
    )
    return dict(
        fetched_at="2026-10-11", sources=[dict(source_id=1, club_id=2, venue_id="3", events=[event, deepcopy(event)])]
    )


def setup(monkeypatch):
    monkeypatch.setattr(pilot, "load_review", lambda *args: {"review_version": 0, "review": None, "stale": False})
    monkeypatch.setenv("COMEDY_MODEL_ENABLED", "0")
    monkeypatch.setenv("COMEDY_MODEL_CACHE_ENABLED", "0")
    monkeypatch.setattr(pilot, "_identity_snapshot", lambda cursor, names: ([], []))
    # Construction has no requests; fail hard if the saved replay attempts a fetch.
    from laughtrack.core.clients.seatengine.client import SeatEngineClient

    monkeypatch.setattr(SeatEngineClient, "fetch_events", lambda *args: pytest.fail("No provider fetch during replay"))


def test_readonly_actual_transform_preserves_counts_evidence_and_duplicate_keys(monkeypatch):
    setup(monkeypatch)
    db = ReadDatabase()
    result = pilot.run(saved(), [1], db.transaction)
    source = result["sources"][0]
    assert source["provider_occurrences"] == source["post_filter_occurrences"] == source["transformed_occurrences"] == 2
    assert source["unique_event_keys"] == 1
    assert source["baseline_decisions"] == {"accept": 2}
    assert source["decisions"][0]["payload"]["performers"] == ["An alias"]
    assert source["shadow"] is None and result["model_requests"] == 0
    assert all(sql.startswith("SELECT") for sql in db.statements)


def test_shadow_requires_exact_mode_and_no_model(monkeypatch):
    setup(monkeypatch)
    db = ReadDatabase()
    db.source["comedy_gate_mode"] = "enforce"
    with pytest.raises(ValueError, match="mixed/shadow"):
        pilot.run(saved(), [1], db.transaction, stage_shadow=True)
    monkeypatch.setenv("COMEDY_MODEL_CACHE_ENABLED", "1")
    with pytest.raises(ValueError, match="COMEDY_MODEL"):
        pilot.run(saved(), [1], db.transaction)


def test_mismatched_account_rejected_before_transform(monkeypatch):
    setup(monkeypatch)
    db = ReadDatabase()
    raw = saved()
    raw["sources"][0]["venue_id"] = "another-account"
    monkeypatch.setattr(pilot, "transform_saved", lambda *args: pytest.fail("Invalid source transformed"))
    with pytest.raises(ValueError, match="provider account"):
        pilot.run(raw, [1], db.transaction)


def test_shadow_uses_real_gate_and_never_records_publication(monkeypatch):
    setup(monkeypatch)
    from laughtrack.core import comedy_eligibility_gate as gate
    from laughtrack.core.comedy_eligibility_store import StagedCandidate

    db = ReadDatabase()
    staged = []
    monkeypatch.setattr(gate, "load_source", lambda *args, **kwargs: deepcopy(db.source))
    monkeypatch.setattr(gate, "_identity_snapshot", lambda *args: ([], []))
    monkeypatch.setattr(gate, "observe_show", lambda *args: True)
    monkeypatch.setattr(gate, "load_review", lambda *args: {"review_version": 0, "review": None, "stale": False})

    def stage(cursor, **kwargs):
        staged.append(kwargs)
        return StagedCandidate(1, 1, 1, kwargs["event_key"], 2, "shadow")

    monkeypatch.setattr(gate, "stage_candidate", stage)
    monkeypatch.setattr(gate, "verify_publication", lambda *args: True)
    monkeypatch.setattr(gate, "link_published", lambda *args: pytest.fail("Pilot cannot publish"))
    result = pilot.run(saved(), [1], db.transaction, stage_shadow=True)
    assert len(staged) == 2
    assert result["sources"][0]["shadow"]["public_writes"] == 0
    assert result["sources"][0]["shadow"]["admitted"] == 2


def test_trust_keeps_baseline_separate_and_cannot_rescue_blocked_people(monkeypatch):
    setup(monkeypatch)
    from laughtrack.core.comedy_eligibility import DeniedName

    db = ReadDatabase()
    db.source.update(
        comedy_policy="comedy_only",
        comedy_reviewed_by="reviewer",
        comedy_reviewed_at="2026-10-11T00:00:00Z",
        comedy_review_evidence={"programming": "reviewed"},
    )
    raw = saved()
    for event in raw["sources"][0]["events"]:
        event["event"]["name"] = "Performer evening"
    result = pilot.run(raw, [1], db.transaction)["sources"][0]
    assert result["baseline_decisions"] == {"review": 2}
    assert result["effective_decisions"] == {"accept": 2}
    monkeypatch.setattr(
        pilot, "_identity_snapshot", lambda *args: ([], [DeniedName("An alias", "non_comedian_musician")])
    )
    result = pilot.run(raw, [1], db.transaction)["sources"][0]
    assert result["effective_decisions"] == {"reject": 2}


def test_prospective_policy_uses_new_version_and_stale_actual_review_holds(monkeypatch):
    setup(monkeypatch)
    db = ReadDatabase()
    calls = []

    def review(*args):
        calls.append(args[-1])
        return {"review_version": 1, "review": None, "stale": True}

    monkeypatch.setattr(pilot, "load_review", review)
    plan = dict(
        rollout_id="future",
        actor="reviewer",
        reason="review programming",
        evidence={"artifact": "review.json"},
        targets=[
            dict(
                source_id=1,
                expected_version=2,
                config_fingerprint=pilot.source_fingerprint(db.source),
                policy="comedy_only",
                gate_mode="shadow",
                source_trust_evidence={
                    "programming_url": "https://example.com/calendar",
                    "reviewed_at": "2026-10-11T00:00:00Z",
                    "reason": "documented programming",
                },
            )
        ],
    )
    result = pilot.run(saved(), [1], db.transaction, prospective_manifest=plan)["sources"][0]
    assert calls == [3, 3]
    assert result["evaluation_kind"] == "prospective"
    assert result["baseline_decisions"] == {"accept": 2}
    assert result["effective_decisions"] == {"review": 2}
    assert all(row["review"]["stale"] for row in result["decisions"])
    with pytest.raises(ValueError, match="cannot stage"):
        pilot.run(saved(), [1], db.transaction, prospective_manifest=plan, stage_shadow=True)


def test_review_identity_scope_stable_when_batch_gets_unrelated_performer(monkeypatch):
    setup(monkeypatch)
    from laughtrack.core.comedy_eligibility import CanonicalPerson

    db = ReadDatabase()
    scopes = []

    def identities(cursor, names):
        return ([CanonicalPerson(1 if name == "an alias" else 2, name, True) for name in names], [])

    def review(*args):
        scopes.append(args[1:])
        return {"review_version": 0, "review": None, "stale": False}

    monkeypatch.setattr(pilot, "_identity_snapshot", identities)
    monkeypatch.setattr(pilot, "load_review", review)
    raw = saved()
    pilot.run(raw, [1], db.transaction)
    first = scopes[0]
    other = deepcopy(raw["sources"][0]["events"][0])
    other["id"] = 99
    other["event"]["talents"] = [{"name": "Other person"}]
    raw["sources"][0]["events"].append(other)
    scopes.clear()
    result = pilot.run(raw, [1], db.transaction)
    assert scopes[0] == first
    assert result["sources"][0]["transformation_losses"] == {"upstream_filtered": 0, "conversion_lost": 0}


def test_transformation_losses_keep_dropped_occurrences_in_denominator(monkeypatch):
    setup(monkeypatch)
    db = ReadDatabase()
    raw = saved()
    lost = deepcopy(raw["sources"][0]["events"][0])
    lost["id"] = 77
    lost["inventories"] = [{"price": 999999999999, "active": True}]
    raw["sources"][0]["events"].append(lost)
    result = pilot.run(raw, [1], db.transaction)["sources"][0]
    assert result["provider_occurrences"] == result["post_filter_occurrences"] == 3
    assert result["transformed_occurrences"] == 2
    assert result["transformation_losses"] == {"upstream_filtered": 0, "conversion_lost": 1}
    assert result["transformation_loss_identifiers"] == {
        "upstream_filtered": [],
        "conversion_lost": [{"source_id": 1, "event_id": 5, "occurrence_id": 77}],
    }


def test_real_review_application_approves_exact_scope_without_changing_baseline(monkeypatch):
    setup(monkeypatch)
    db = ReadDatabase()
    raw = saved()
    for event in raw["sources"][0]["events"]:
        event["event"]["name"] = "Performer evening"
    monkeypatch.setattr(
        pilot,
        "load_review",
        lambda *args: {"review_version": 1, "stale": False, "review": {"id": 41, "action": "approve"}},
    )
    result = pilot.run(raw, [1], db.transaction)["sources"][0]
    assert result["baseline_decisions"] == {"review": 2}
    assert result["effective_decisions"] == {"accept": 2}
    for decision in result["decisions"]:
        assert decision["review"]["action_id"] == 41
        assert "human_approve" in decision["effective"]["reason_codes"]
        assert decision["effective"]["classifier_version"].endswith(":human:41")


def test_partial_raw_lineup_reason_matches_gate_for_both_outputs(monkeypatch):
    setup(monkeypatch)
    db = ReadDatabase()
    raw = saved()
    for event in raw["sources"][0]["events"]:
        event["event"]["talents"].append({"name": None})
    result = pilot.run(raw, [1], db.transaction)["sources"][0]
    for decision in result["decisions"]:
        for kind in ("baseline", "effective"):
            assert decision[kind]["lineup_status"] == "partial"
            assert "raw_lineup_partial" in decision[kind]["reason_codes"]
