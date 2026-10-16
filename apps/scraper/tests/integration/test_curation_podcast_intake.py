"""PostgreSQL contract shared by Python writers and the admin service."""
from pathlib import Path
import subprocess
from unittest.mock import MagicMock
import pytest
from laughtrack.core.podcast_curation import resolve_candidate


def test_podcast_intake_database_contract():
    web = Path(__file__).resolve().parents[3] / "web"
    result = subprocess.run(["npm", "test", "--", "lib/admin/curation/podcastIntake.test.ts"], cwd=web, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("row", [None, ("blocked", "id", 1), ("ambiguous", None, None)])
def test_discovery_holds_unresolved_policy(row):
    cur = MagicMock(); cur.fetchone.return_value = row
    candidate = MagicMock(source="itunes", source_podcast_id="1", feed_url="https://example.com/feed", title="Title")
    with pytest.raises(ValueError): resolve_candidate(cur, candidate)
    assert cur.execute.call_args_list[0].args[0] == "SELECT curation_lock_intake()"


def test_discovery_propagates_policy_failure():
    cur=MagicMock(); cur.execute.side_effect=RuntimeError("unavailable")
    candidate=MagicMock(source="itunes",source_podcast_id="1",feed_url=None,title="Title")
    with pytest.raises(RuntimeError): resolve_candidate(cur,candidate)
