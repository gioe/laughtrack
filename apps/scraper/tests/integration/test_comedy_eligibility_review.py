"""Human review command and gate contracts; no production access."""

import json
from unittest.mock import Mock


def test_contract_1(capsys):
    from scripts.core.review_comedy_eligibility import main

    store = Mock()
    item = {
        "candidate_id": 7,
        "current": {
            "payload": {"name": "Blues Night"},
            "evidence": {
                "lineup_status": "partial",
                "performers": [
                    {
                        "canonical_id": 11,
                        "block_reasons": ["non_comedian_musician"],
                        "diagnostics": ["canonical_parent_resolved"],
                    }
                ],
            },
        },
        "source": {"id": 3, "comedy_policy": "mixed"},
        "history": [{"decision": "review"}],
    }
    store.list_queue.return_value = {"items": [item], "next_after_id": 7, "ceiling_id": 100}
    assert (
        main(
            [
                "list",
                "--source-id",
                "3",
                "--decision",
                "review",
                "--coverage",
                "partial",
                "--after-id",
                "6",
                "--ceiling-id",
                "100",
                "--limit",
                "10",
            ],
            store=store,
        )
        == 0
    )
    page = json.loads(capsys.readouterr().out)
    assert page["items"] == [item]
    store.list_queue.assert_called_once_with(
        filters={"source_id": 3, "decision": "review", "coverage": "partial"}, after_id=6, ceiling_id=100, limit=10
    )
    store.detail.return_value = item
    main(["inspect", "7"], store=store)
    assert json.loads(capsys.readouterr().out) == item
    store.detail.assert_called_once_with(7)
    store.apply.assert_not_called()


def _review_environment(monkeypatch, mode="enforce", action="approve"):
    from tests.integration.test_comedy_eligibility_gate import _gate_environment, _writer_handler
    from laughtrack.core import comedy_eligibility_gate as gate

    state = _gate_environment(monkeypatch, mode)
    state.review_version = 1
    state.action = action
    state.stale_review = False

    def review(*args):
        return {
            "review_version": state.review_version,
            "stale": state.stale_review,
            "review": (
                None
                if state.stale_review
                else {"id": 1, "action": state.action, "actor": "operator", "reason": "Event evidence checked"}
            ),
        }

    monkeypatch.setattr(gate, "load_review", review)
    return state, _writer_handler(monkeypatch, state)


def test_contract_2(monkeypatch, capsys):
    import pytest
    from scripts.core.review_comedy_eligibility import main
    from laughtrack.core.comedy_eligibility_review_store import ReviewStore
    from tests.integration.test_comedy_eligibility_gate import _gate_show

    transaction = Mock()
    store = ReviewStore(transaction)
    for actor, reason in [("", "Evidence checked"), ("operator", " ")]:
        with pytest.raises(ValueError):
            store.preview([7], "approve", reason, actor)
    transaction.assert_not_called()
    cli_store = Mock()
    cli_store.preview.return_value = {"preview_id": "p1", "token_digest": "digest", "items": [{"candidate_id": 7}]}
    main(
        [
            "preview",
            "--candidate-id",
            "7",
            "--action",
            "approve",
            "--actor",
            "operator",
            "--reason",
            "Event evidence checked",
        ],
        store=cli_store,
    )
    assert json.loads(capsys.readouterr().out)["operation"] == "PLAN"
    cli_store.apply.assert_not_called()
    cli_store.apply.return_value = {"actions": [{"candidate_id": 7, "action": "approve"}]}
    main(
        [
            "apply",
            "--preview-id",
            "p1",
            "--token-digest",
            "digest",
            "--actor",
            "operator",
            "--idempotency-key",
            "operation-1",
        ],
        store=cli_store,
    )
    cli_store.apply.assert_called_once_with("p1", "operator", "operation-1", "digest")
    state, handler = _review_environment(monkeypatch)
    for _ in range(2):
        result = handler._process_single_batch([_gate_show(name="Saturday at Eight")])
        assert result.eligibility_withheld == 0
    assert len(state.public) == 1  # Existing public writer upsert identity, no replay shortcut.
    assert state.staged[-1]["decision"].reason_codes[-1] != "validated_model_evidence"
    for mode in ("shadow", "enforce"):
        for action in ("reject", "defer"):
            state, handler = _review_environment(monkeypatch, mode, action)
            result = handler._process_single_batch([_gate_show()])
            assert result.eligibility_withheld == 1
            assert not state.public
            assert state.source["comedy_policy"] == "unreviewed"


def test_contract_3(monkeypatch):
    from laughtrack.core import comedy_eligibility_model as model
    from laughtrack.core import comedy_eligibility_gate as gate
    from laughtrack.core.comedy_eligibility_review_store import load_review
    from tests.integration.test_comedy_eligibility_gate import _gate_show, _gate_environment, _writer_handler

    # Real scope matcher: payload, identity and policy changes each invalidate review.
    row = {
        "review_version": 1,
        "id": 1,
        "action": "approve",
        "reason": "Reviewed",
        "actor": "operator",
        "payload_fingerprint": "payload",
        "identity_fingerprint": "identity",
        "policy_version": 1,
    }
    cursor = Mock()
    cursor.fetchone.return_value = row
    for payload, identity, version in [
        ("changed", "identity", 1),
        ("payload", "changed", 1),
        ("payload", "identity", 2),
    ]:
        result = load_review(cursor, 7, "event", payload, identity, version)
        assert result["stale"] is True and result["review"] is None
    assert load_review(cursor, 7, "event", "payload", "identity", 1)["review"]["action"] == "approve"
    model_calls = Mock()
    monkeypatch.setattr(model, "cached_decision", model_calls)
    state, handler = _review_environment(monkeypatch, "shadow", "approve")
    state.stale_review = True
    assert handler._process_single_batch([_gate_show()]).eligibility_withheld == 1
    assert "stale_human_review" in state.staged[-1]["decision"].reason_codes
    model_calls.assert_not_called()
    assert not state.public
    # A review arriving after staging invalidates the pending publication fence.
    state, handler = _review_environment(monkeypatch)
    state.after_stage = lambda: setattr(state, "review_version", 2)
    assert handler._process_single_batch([_gate_show()]).eligibility_withheld == 1
    assert not state.public
    # A failed shadow staging operation cannot bypass a late human review.
    state = _gate_environment(monkeypatch, "shadow")
    handler = _writer_handler(monkeypatch, state)
    state.fail_stage = True
    reads = []

    def late_review(*args):
        reads.append(True)
        return {"review_version": 0 if len(reads) == 1 else 1, "review": None, "stale": len(reads) > 1}

    monkeypatch.setattr(gate, "load_review", late_review)
    model_calls.return_value = gate.classify_comedy_eligibility(
        source_id=7, policy=gate.SourceComedyPolicy(), evidence=[], performers=[], people=[], denied=[]
    )
    result = handler._process_single_batch([_gate_show(name="Saturday at Eight")])
    assert result.eligibility_withheld == 1 and not state.public
    assert any("FOR UPDATE" in sql and "scraping_sources" in sql for sql, _ in state.calls)
    # Unknown review authority also fails closed in shadow, without provider work.
    state = _gate_environment(monkeypatch, "shadow")
    handler = _writer_handler(monkeypatch, state)
    monkeypatch.setattr(gate, "load_review", Mock(side_effect=RuntimeError("review unavailable")))
    result = handler._process_single_batch([_gate_show()])
    assert result.eligibility_withheld == 1 and not state.public
