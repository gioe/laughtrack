"""Bounded collector activation changes metadata only, with atomic cohort guards."""

from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import json

import pytest
from scripts.archive import enable_pilot_event_details_2026_10_11 as activation


class Database:
    def __init__(self):
        self.data = [
            dict(
                id=sid,
                club_id=club,
                seatengine_id=venue,
                scraper_key="seatengine",
                platform="seatengine",
                enabled=True,
                comedy_policy="unreviewed",
                comedy_gate_mode="off",
                comedy_policy_version=3,
                source_target_id=None,
                updated_at=datetime(2026, 10, 10, tzinfo=timezone.utc),
                metadata={"keep": "unrelated", "task_4158_rollout": {"history": "preserved"}},
            )
            for sid, (club, venue, _) in activation.EXPECTED.items()
        ]
        self.result = []
        self.rowcount = 0
        self.writes = 0
        self.fail_id = None
        self.transaction_time = datetime(2026, 10, 11, tzinfo=timezone.utc)
        self.illegal_mutation = False

    @contextmanager
    def transaction(self):
        before = deepcopy(self.data)
        try:
            yield self
        except Exception:
            self.data = before
            raise

    @contextmanager
    def cursor(self):
        yield self

    def execute(self, sql, params):
        if sql == "SELECT transaction_timestamp()":
            self.result = [(self.transaction_time,)]
        elif sql.startswith("SELECT"):
            self.description = [(key,) for key in self.data[0]]
            self.result = [tuple(row.values()) for row in self.data]
        elif sql.startswith("UPDATE"):
            metadata, sid, old = params
            if sid == self.fail_id:
                raise RuntimeError("injected failure")
            row = next(row for row in self.data if row["id"] == sid)
            assert row["metadata"] == json.loads(old)
            row["metadata"] = json.loads(metadata)
            row["updated_at"] = self.transaction_time
            if self.illegal_mutation:
                row["enabled"] = False
            self.result = [(sid,)]
            self.rowcount = 1
            self.writes += 1
        else:
            raise AssertionError(sql)

    def fetchall(self):
        return self.result


@pytest.fixture
def db(monkeypatch):
    value = Database()
    monkeypatch.setattr(
        activation,
        "EXPECTED",
        {row["id"]: (row["club_id"], row["seatengine_id"], activation.fingerprint(row)) for row in value.data},
    )
    return value


def test_dry_run_activation_retry_preserve_gate_and_unrelated_fields(db):
    before = deepcopy(db.data)
    assert activation.run(db.transaction)["changed_rows"] == 0
    assert db.data == before
    assert activation.run(db.transaction, apply=True)["changed_rows"] == 3
    for original, current in zip(before, db.data):
        expected = deepcopy(original)
        expected["metadata"].update(seatengine_event_details=True)
        expected["metadata"][activation.ANNOTATION_KEY] = activation.ANNOTATION
        expected["updated_at"] = db.transaction_time
        assert current == expected
    after_first = deepcopy(db.data)
    db.transaction_time = datetime(2026, 10, 12, tzinfo=timezone.utc)
    assert activation.run(db.transaction, apply=True)["changed_rows"] == 0
    assert db.data == after_first  # Idempotent rows retain their exact timestamp.
    assert db.writes == 3


def test_unrelated_trigger_mutation_rolls_back_despite_valid_timestamp(db):
    before = deepcopy(db.data)
    db.illegal_mutation = True
    with pytest.raises(ValueError, match="Post-state mismatch"):
        activation.run(db.transaction, apply=True)
    assert db.data == before


@pytest.mark.parametrize("change", ["version", "mode", "config", "disabled", "audit"])
def test_entire_cohort_validates_before_any_write(db, change):
    row = db.data[-1]
    if change == "version":
        row["comedy_policy_version"] = 4
    elif change == "mode":
        row["comedy_gate_mode"] = "enforce"
    elif change == "disabled":
        row["enabled"] = False
    elif change == "audit":
        row["metadata"][activation.ANNOTATION_KEY] = {"task": "different"}
    else:
        row["metadata"]["keep"] = "changed"
    with pytest.raises(ValueError, match="Refusing entire activation"):
        activation.run(db.transaction, apply=True)
    assert db.writes == 0


def test_late_write_failure_rolls_back_all_sources(db):
    before = deepcopy(db.data)
    db.fail_id = db.data[-1]["id"]
    with pytest.raises(RuntimeError, match="injected failure"):
        activation.run(db.transaction, apply=True)
    assert db.data == before
