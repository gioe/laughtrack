"""The ingestion boundary only resolves identities explicitly validated by review."""
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from laughtrack.core.entities.comedian.handler import ComedianHandler
from laughtrack.core.entities.comedian.model import Comedian

@contextmanager
def transaction():
    yield object()

def handler():
    h = ComedianHandler.__new__(ComedianHandler)
    h.transaction = transaction
    h.execute_batch_operation = MagicMock()
    h.execute_with_cursor = MagicMock(return_value=[])
    return h

@pytest.mark.parametrize("name", ["A BOOMER CHRISTMAS CAROL", "A Charlie Brown Christmas", "A Dreadful...", "a first-generation Pakistani-Chilean", "A Magical Cirque Christmas (Touring)", "Robin Tran", "Blue Man Group"])
def test_extraction_never_inserts_an_unvalidated_identity(name):
    h = handler()
    c = Comedian(name=name, uuid="candidate")
    show = SimpleNamespace(id=1, name=name, description="Source context", show_page_url="https://example.com/event", last_scraped_by="test", lineup=[c])
    assert h.stage_identity_candidates([c], shows=[show]) == {}
    queries = [call.args[0] for call in h.execute_batch_operation.call_args_list]
    assert len(queries) == 4
    assert all("INSERT INTO comedians " not in q for q in queries)
    assert "ON CONFLICT(uuid) DO NOTHING" in queries[1]
    assert h.execute_batch_operation.call_args.args[1][0][-1] == f"Event: {name}\nSource context"

def test_reviewed_alias_resolves_to_canonical_uuid():
    h=handler()
    h.execute_with_cursor.return_value=[{"candidate_uuid":"candidate","uuid":"canonical","name":"Steve Marshall"}]
    result=h.stage_identity_candidates([Comedian(name="Steve Marshall Comedy",uuid="candidate")])
    assert result["candidate"].uuid == "canonical"
    assert "candidate.status='accepted'" in h.execute_with_cursor.call_args.args[0]
    assert "identity_validated_at IS NOT NULL" in h.execute_with_cursor.call_args.args[0]

def test_pre_filtered_does_not_bypass_human_validation():
    h=handler()
    h._filter_false_positive_comedians=lambda items:items
    h.stage_identity_candidates=MagicMock(return_value={})
    assert h.insert_comedians([Comedian(name="Unreviewed Person",uuid="candidate")],pre_filtered=True)==[]
    h.execute_batch_operation.assert_not_called()

def test_joint_billing_resolves_members_and_preserves_source_credit_in_batch():
    h = handler()
    h.execute_with_cursor.side_effect = [
        [{"credit_id": "joint", "show_id": 5, "uuid": "josh", "name": "Josh Martier"},
         {"credit_id": "joint", "show_id": 5, "uuid": "ben", "name": "Ben Staab"}], None]
    show = SimpleNamespace(id=5, club_id=42, last_scraped_by="venue", lineup=[Comedian(name="Josh Martier & Ben Staab", uuid="billing")])
    result = h.resolve_joint_billings([show])
    assert [c.name for c in result[5]] == ["Josh Martier", "Ben Staab"]
    assert show.lineup[0].name == "Josh Martier & Ben Staab"
    assert h.execute_with_cursor.call_args_list[0].args[1] == ([5], ["venue"], ["Josh Martier & Ben Staab"], [42])
    assert h.execute_batch_operation.call_args.args[1] == [("joint", 5)]


def test_unmatched_billing_returns_to_review_without_inventing_members():
    h = handler()
    show = SimpleNamespace(id=5, club_id=42, last_scraped_by="different-source", lineup=[Comedian(name="Josh Martier & Ben Staab",uuid="billing")])
    assert h.resolve_joint_billings([show]) == {}
    h.execute_batch_operation.assert_not_called()
    assert "status='pending'" in h.execute_with_cursor.call_args.args[0]
    assert h.execute_with_cursor.call_args.args[1] == (["billing"], ["different-source"], ["Josh Martier & Ben Staab"], [42])
