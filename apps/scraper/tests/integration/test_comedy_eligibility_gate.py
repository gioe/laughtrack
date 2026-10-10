"""Eligibility staging and public write boundary contracts."""


def test_contract_1(monkeypatch):
    from laughtrack.core import comedy_eligibility_store as store

    source = {"comedy_policy": "unreviewed", "id": 7, "enabled": True, "comedy_policy_version": 2, "comedy_gate_mode": "enforce"}
    monkeypatch.setattr(store, "load_source", lambda *args, **kwargs: source)
    rows = iter([{"id": 10, "observation_generation": 1}, {"id": 20},
                 {"id": 10, "observation_generation": 2}, None, {"id": 20}])
    monkeypatch.setattr(store, "_row", lambda cursor: next(rows))

    class Cursor:
        def __init__(self):
            self.calls = []

        def execute(self, sql, params):
            self.calls.append((sql, params))

    cursor = Cursor()
    kwargs = dict(source_id=7, event_key="native:event-1", club_id=42,
                  payload={"title": "Stand-up comedy", "performers": ["Raw Name"]},
                  decision={"policy": "unreviewed", "source_id": 7, "policy_version": 2, "classifier_version": "v1",
                            "decision": "review", "performers": [], "reason_codes": ["unknown"]},
                  gate_mode="enforce")
    first = store.stage_candidate(cursor, **kwargs)
    retry = store.stage_candidate(cursor, **kwargs)
    assert first.id == retry.id and first.decision_id == retry.decision_id
    assert first.observation_generation == 1 and retry.observation_generation == 2
    assert first.id == 10 and first.decision_id == 20 and first.source_id == 7
    assert first.policy_version == 2
    insert_calls = [params for sql, params in cursor.calls if sql == store.INSERT_DECISION_SQL]
    assert insert_calls[0] == insert_calls[1]
    assert "Raw Name" in insert_calls[0][-2] and "unknown" in insert_calls[0][-1]
    assert store.fingerprint({"a": 1, "b": 2}) == store.fingerprint({"b": 2, "a": 1})
    assert store.fingerprint({"a": 1}) != store.fingerprint({"a": 2})
