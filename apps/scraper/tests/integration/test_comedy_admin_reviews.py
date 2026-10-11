"""Admin worker transaction ownership and reuse of the live CLI review guard."""
from contextlib import contextmanager
from unittest.mock import MagicMock, Mock
import pytest
from laughtrack.core.comedy_admin_reviews import process_one, process_requests
from laughtrack.core.comedy_eligibility_review import current_identity_fingerprint


def environment():
    scope = dict(candidate_id=1, source_id=2, observation_generation="3", review_version=0,
                 decision_id=4, payload_fingerprint="p", identity_fingerprint="i", policy_version=1, gate_mode="shadow")
    row = {**scope, "observation_generation": 3}
    request = dict(id="request", candidate_id=1, actor="admin", action="reject", reason="Music only", snapshot=scope)
    cur = MagicMock()
    cur.fetchone.side_effect = [request, {"role": "admin"}, row]
    cur.__enter__.return_value = cur
    conn = MagicMock()
    conn.cursor.return_value = cur
    outcomes = []

    @contextmanager
    def transaction():
        try:
            yield conn
        except Exception:
            outcomes.append("rollback")
            raise
        else:
            outcomes.append("commit")

    store = Mock()
    store.preview.return_value = {"preview_id": "preview", "token_digest": "token", "items": [row.copy()]}
    store.apply.return_value = {"actions": [{"candidate_id": 1, "action": "reject"}]}
    factory = Mock(return_value=store)
    return request, row, cur, conn, transaction, store, factory, outcomes


def test_apply_uses_live_guard_same_transaction_and_exact_scope():
    request, row, cur, conn, transaction, store, factory, outcomes = environment()
    assert process_one(transaction, store_factory=factory) == {"id": "request", "status": "applied"}
    assert factory.call_args.kwargs == {"snapshot_validator": current_identity_fingerprint}
    with factory.call_args.args[0]() as reused:
        assert reused is conn
    store.preview.assert_called_once_with([1], "reject", "Music only", "admin")
    store.apply.assert_called_once_with("preview", "admin", "admin:request", "token")
    assert outcomes == ["commit"]
    sql = [call.args[0] for call in cur.execute.call_args_list]
    assert "FOR UPDATE SKIP LOCKED" in sql[0]
    assert "status='applied'" in sql[-1]
    assert not any("UPDATE shows" in s or "UPDATE scraping_sources" in s for s in sql)


@pytest.mark.parametrize("field,value", [("observation_generation",4),("review_version",1),("decision_id",5),
    ("payload_fingerprint","new"),("identity_fingerprint","new"),("policy_version",2),("gate_mode","off")])
def test_changed_snapshots_are_stale_before_preview(field, value):
    request, row, cur, conn, transaction, store, factory, outcomes = environment()
    row[field] = value
    assert process_one(transaction, store_factory=factory)["status"] == "stale"
    store.preview.assert_not_called()
    assert "ROLLBACK TO SAVEPOINT" in cur.execute.call_args_list[-2].args[0]
    assert outcomes == ["commit"]


def test_preview_race_cannot_replace_what_operator_reviewed():
    request, row, cur, conn, transaction, store, factory, outcomes = environment()
    store.preview.return_value["items"][0]["review_version"] = 7
    assert process_one(transaction, store_factory=factory)["status"] == "stale"
    store.apply.assert_not_called()


@pytest.mark.parametrize("method", ["preview", "apply"])
def test_review_store_live_identity_and_policy_rejection_is_visible(method):
    request, row, cur, conn, transaction, store, factory, outcomes = environment()
    getattr(store, method).side_effect = ValueError("Live identity changed")
    assert process_one(transaction, store_factory=factory)["status"] == "stale"
    assert "Live identity changed" in cur.execute.call_args.args[1]


def test_transient_failure_rolls_back_for_retry_instead_of_marking_applied():
    request, row, cur, conn, transaction, store, factory, outcomes = environment()
    store.apply.side_effect = RuntimeError("database disconnected")
    with pytest.raises(RuntimeError):
        process_one(transaction, store_factory=factory)
    assert outcomes == ["rollback"]
    assert not any("status='applied'" in c.args[0] for c in cur.execute.call_args_list)


def test_revoked_admin_request_is_not_applied():
    request, row, cur, conn, transaction, store, factory, outcomes = environment()
    cur.fetchone.side_effect = [request, {"role": "user"}]
    assert process_one(transaction, store_factory=factory)["status"] == "stale"
    factory.assert_not_called()


def test_empty_queue_and_limit_validation():
    request, row, cur, conn, transaction, store, factory, outcomes = environment()
    cur.fetchone.side_effect = [None]
    assert process_one(transaction, store_factory=factory) is None
    factory.assert_not_called()
    for invalid in [0,501,True]:
        with pytest.raises(ValueError):
            process_requests(transaction, invalid)


@pytest.mark.parametrize("change", ["identity", "policy", "off", "disabled"])
def test_real_review_store_refuses_changed_live_state(monkeypatch, change):
    import laughtrack.core.comedy_admin_reviews as worker
    request, row, cur, conn, transaction, store, factory, outcomes = environment()
    live = {**row, "enabled": True, "current_policy_version": 1}
    if change == "policy":
        live["current_policy_version"] = 2
    if change == "off":
        live["gate_mode"] = "off"
    if change == "disabled":
        live["enabled"] = False
    monkeypatch.setattr(worker, "current_identity_fingerprint", lambda cursor, current: "changed" if change == "identity" else "i")
    cur.fetchone.side_effect = [request, {"role": "admin"}, row, live]
    assert process_one(transaction)["status"] == "stale"
    assert not any("INSERT INTO comedy_event_reviews" in c.args[0] for c in cur.execute.call_args_list)
