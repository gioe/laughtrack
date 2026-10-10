"""Runtime contracts; executable PostgreSQL migration coverage lives in web/prisma."""

from dataclasses import replace
from unittest.mock import Mock

import pytest

from laughtrack.core.entities.club.comedy_policy import SourceComedyPolicy, save_source_comedy_policy
from laughtrack.core.entities.club.model import ScrapingSource
from sql.club_queries import ClubQueries


def test_contract_1():
    first = ScrapingSource.from_dict(
        {
            "id": 1,
            "club_id": 20,
            "platform": "custom",
            "comedy_policy": "mixed",
            "comedy_gate_mode": "shadow",
            "comedy_policy_version": 2,
            "comedy_reviewed_by": "reviewer",
            "comedy_review_evidence": {"url": "https://example.org"},
        }
    )
    sibling = ScrapingSource.from_dict(
        {"id": 2, "club_id": 20, "platform": "custom", "comedy_policy": "comedy_only", "comedy_gate_mode": "off"}
    )
    assert first.comedy_policy.policy == "mixed"
    assert sibling.comedy_policy.policy == "comedy_only"
    assert first.comedy_policy.gate_mode == "shadow"
    cursor = Mock()
    cursor.fetchone.return_value = ("mixed", "enforce", 3, "reviewer", "2026-10-10", {"url": "https://example.org"})
    saved = save_source_comedy_policy(cursor, first.id, replace(first.comedy_policy, gate_mode="enforce"))
    assert saved.version == 3
    sql, params = cursor.execute.call_args.args
    assert params[-2:] == (1, 2)
    assert "WHERE id = %s AND comedy_policy_version = %s" in sql
    assert saved.reviewed_at == "2026-10-10"
    for kwargs in (
        {"policy": "trusted"},
        {"gate_mode": "enabled"},
        {"version": 0},
        {"version": True},
        {"evidence": []},
    ):
        with pytest.raises(ValueError):
            SourceComedyPolicy(**kwargs)


def test_contract_2():
    legacy = ScrapingSource.from_dict(
        {"platform": "custom", "metadata": {"comedy_policy": "comedy_only", "comedy_gate_mode": "enforce"}}
    )
    assert legacy.comedy_policy == SourceComedyPolicy()
    assert ScrapingSource(platform="custom", scraper_key="test").comedy_policy == SourceComedyPolicy()
    # Both owner paths must load policy from the source itself, never merged metadata.
    for sql in (ClubQueries.GET_ALL_CLUBS, ClubQueries.GET_ALL_SOURCE_TARGETS):
        assert "to_jsonb(ss)->>'comedy_policy'" in sql
        assert "to_jsonb(ss)->>'comedy_gate_mode'" in sql
        assert "'unreviewed'" in sql and "'off'" in sql
        where = sql.split("WHERE")
        assert all("comedy_policy =" not in part and "comedy_gate_mode =" not in part for part in where)


def test_contract_3():
    old = SourceComedyPolicy(policy="mixed", gate_mode="enforce", version=4)
    assert old.accepts_decision(source_id=1, decision_source_id=1, decision_policy_version=4)
    assert not old.accepts_decision(source_id=2, decision_source_id=1, decision_policy_version=4)
    assert not old.accepts_decision(source_id=None, decision_source_id=1, decision_policy_version=4)
    rolled_back = replace(old, gate_mode="off", version=5)
    assert not rolled_back.accepts_decision(source_id=1, decision_source_id=1, decision_policy_version=4)
    cursor = Mock()
    cursor.fetchone.return_value = None
    with pytest.raises(ValueError, match="reload"):
        save_source_comedy_policy(cursor, 1, replace(old, reviewed_by="operator", evidence={"reason": "rollback"}))
    with pytest.raises(ValueError, match="reviewer"):
        save_source_comedy_policy(cursor, 1, old)
