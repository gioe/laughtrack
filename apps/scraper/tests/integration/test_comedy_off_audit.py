"""Off-mode audit records never grant public-write authority."""

from contextlib import contextmanager
from unittest.mock import Mock

import pytest
from laughtrack.core import comedy_eligibility_store as staging
from laughtrack.core import comedy_eligibility_review_store as reviews


def test_off_token_never_verifies_or_links_publication():
    cursor = Mock()
    token = staging.StagedCandidate(1, 2, 3, "event", 3, "off")
    assert not staging.verify_publication(cursor, token)
    with pytest.raises(ValueError, match="ineligible"):
        staging.link_published(cursor, token, 99)
    cursor.execute.assert_not_called()


def test_off_staging_is_explicit_and_preserves_policy_checks(monkeypatch):
    source = dict(id=3, enabled=True, comedy_policy="unreviewed", comedy_policy_version=3, comedy_gate_mode="off")
    monkeypatch.setattr(staging, "load_source", lambda *args, **kwargs: source)
    kwargs = dict(
        source_id=3,
        event_key="event",
        club_id=10,
        payload={},
        gate_mode="off",
        decision=dict(source_id=3, policy="unreviewed", policy_version=3, classifier_version="v3", decision="accept"),
    )
    cursor = Mock()
    with pytest.raises(ValueError):
        staging.stage_candidate(cursor, **kwargs)
    cursor.execute.assert_not_called()
    rows = iter([dict(id=1, observation_generation=1, review_version=0), dict(id=2)])
    monkeypatch.setattr(staging, "_row", lambda cur: next(rows))
    assert staging.stage_candidate(cursor, **kwargs, allow_off_audit=True).gate_mode == "off"
    source["comedy_policy_version"] = 4
    with pytest.raises(ValueError):
        staging.stage_candidate(cursor, **kwargs, allow_off_audit=True)


def test_off_review_requires_optin_and_rechecks_source_and_identity(monkeypatch):
    row = dict(
        candidate_id=1,
        source_id=3,
        observation_generation=1,
        review_version=0,
        decision_id=2,
        payload_fingerprint="p",
        identity_fingerprint="i",
        policy_version=3,
        current_policy_version=3,
        gate_mode="off",
        enabled=True,
        decision="review",
    )
    source = dict(enabled=True, comedy_policy_version=3, comedy_gate_mode="off")
    cursor = Mock()

    @contextmanager
    def transaction():
        yield Mock(cursor=lambda: cursor)

    cursor.__enter__ = Mock(return_value=cursor)
    cursor.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(reviews, "_row", lambda c: row)
    monkeypatch.setattr(reviews, "load_source", lambda *args, **kwargs: source)
    validator = lambda c, r: "i"
    with pytest.raises(ValueError, match="current enabled"):
        reviews.ReviewStore(transaction, validator).preview([1], "approve", "specific event evidence", "Codex agent")
    allowed = reviews.ReviewStore(transaction, validator, allow_off_audit=True)
    preview = allowed.preview([1], "approve", "specific event evidence", "Codex agent")
    stored = {**preview, "fresh": True}

    def apply(store):
        results = iter([stored, None, row, {"id": 1}])
        monkeypatch.setattr(reviews, "_row", lambda c: next(results))
        return store.apply(preview["preview_id"], "Codex agent", "audit-1", preview["token_digest"])

    with pytest.raises(ValueError, match="Source policy"):
        apply(reviews.ReviewStore(transaction, validator))
    assert apply(allowed)["actions"][0]["action"] == "approve"
    source["comedy_policy_version"] = 4
    with pytest.raises(ValueError, match="Source policy"):
        apply(allowed)
    source["comedy_policy_version"] = 3
    allowed.snapshot_validator = lambda *args: "changed"
    with pytest.raises(ValueError, match="identity evidence"):
        apply(allowed)
