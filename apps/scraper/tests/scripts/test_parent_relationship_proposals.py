"""Maintenance scripts must not bypass durable parent review."""
from unittest.mock import Mock
import pytest
from scripts.core import link_comedian_aliases, reconcile_deny_list


def test_alias_normalization_only_proposes_pairs():
    cur = Mock(rowcount=1)
    links = [{"child_id": 1, "parent_id": 2}]
    assert link_comedian_aliases._apply_links(cur, links) == 1
    sql, args = cur.execute.call_args.args
    assert "curation_propose_parent" in sql
    assert "automatic-alias-suggestion" in sql
    assert args == (1, 2)
    assert "UPDATE comedians" not in sql


def test_denied_title_cannot_be_resurrected_as_alias():
    cur = Mock()
    with pytest.raises(ValueError, match="Automatic resurrection"):
        reconcile_deny_list._apply_aliases(cur, [{"name": "Real Person Comedy", "parent_id": 2}])
    cur.execute.assert_not_called()
    assert reconcile_deny_list._apply_aliases(cur, []) == (0, 0)
