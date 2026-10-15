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

    def execute(self, sql, params=()):
        self.statements.append(sql)
        assert sql.startswith("SELECT"), "Default pilot must not write"
        if sql == "SELECT curation_lock_intake()":
            self.rows = []
        elif "scraping_sources" in sql:
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
