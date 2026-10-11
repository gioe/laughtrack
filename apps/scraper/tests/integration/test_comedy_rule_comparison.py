"""Versioned offline replay must not pretend public search is raw ingestion."""

import copy
import io
import tarfile

import pytest

from scripts.core import comedy_search_corpus
from scripts.core import compare_comedy_event_rules as comparison


def supported_row(title="Book Your Holiday Party!"):
    policy = {"policy": "unreviewed", "gate_mode": "off", "version": 7,
              "reviewed_by": None, "reviewed_at": None, "evidence": {}}
    raw = {"performers": [], "classifications": []}
    row = {
        "public_show_id": 91, "event_evidence": {"title": title, "description": "Comedy Show",
                                                  "public_lineup": [{"name": "Public only"}]},
        "context": {"club_id": 5, "club_name": "Comedy Club"},
        "source_evidence": {"status": "resolved", "publication_candidates": [
            {"source_id": 8, "event_key": "native:provider-123"}]},
        "reference_label": {"genre": "unknown", "selection": "flagged"},
        "ingestion_snapshot": {
            "source_id": 8, "event_key": "native:provider-123", "club_id": 5, "policy": policy,
            "policy_sha256": comparison.digest(policy), "performers": [],
            "raw_performers_preserved": True, "identity_snapshot_complete": True,
            "people": [], "denied": [], "adapter_evidence": [],
            "raw_event": raw, "raw_event_sha256": comparison.digest(raw),
        },
    }
    row["ingestion_snapshot"]["identity_sha256"] = comparison.identity_digest(row["ingestion_snapshot"])
    return row


@pytest.fixture(scope="module")
def versioned():
    rows = [supported_row(), supported_row("R&B Karaoke and Comedy"), supported_row("Comedy Class")]
    rows[1]["public_show_id"] = 92
    rows[2]["public_show_id"] = 93
    corpus = {"corpus_version": "synthetic-v1", "manifest_sha256": "f" * 64, "records": rows}
    return corpus, comparison.replay(corpus)


def test_versioned_same_corpus_replay(versioned):
    corpus, result = versioned
    assert result["input_count"] == 3 and result["unsupported"] == []
    assert result["corpus_records_sha256"] == comparison.digest(corpus["records"])
    runs = result["runs"]
    assert {run["input_sha256"] for run in runs.values()} == {result["input_sha256"]}
    assert {run["git_revision"] for run in runs.values()} == set(comparison.REVISIONS.values())
    assert [row["decision"]["decision"] for row in runs["baseline"]["rows"]] == ["review", "review", "review"]
    assert [row["decision"]["decision"] for row in runs["candidate"]["rows"]] == ["reject", "accept", "reject"]
    assert runs["baseline"]["classifier_version"] == "comedy-eligibility-v2"
    assert runs["candidate"]["classifier_version"] == "comedy-eligibility-v2-rules-v3"
    assert all(run["imported_source_sha256"] for run in runs.values())
    assert all(row["policy_sha256"] == comparison.digest(corpus["records"][0]["ingestion_snapshot"]["policy"])
               for run in runs.values() for row in run["rows"])

    original = comedy_search_corpus.load_corpus()
    inputs, unsupported = comparison.prepare_inputs(original)
    assert inputs == [] and len(unsupported) == 2886
    assert all("unresolved_source_ownership" in row["reasons"] for row in unsupported)
    assert all("missing_prefilter_performers" in row["reasons"] for row in unsupported)
    diagnostic, _ = comparison.prepare_inputs(original, diagnostic=True)
    assert len(diagnostic) == 2886
    assert all(row["snapshot"]["source_id"] is None and row["snapshot"]["raw_event"] == {}
               and row["snapshot"]["performers"] == [] for row in diagnostic)


@pytest.mark.parametrize("mutation,reason", [
    ("ownership", "snapshot_source_mismatch"), ("raw_performers", "missing_prefilter_performers"),
    ("people", "missing_identity_snapshot"), ("policy", "missing_source_policy_snapshot"),
    ("event", "missing_raw_event_snapshot"),
])
def test_missing_or_changed_snapshots_are_unsupported(mutation, reason):
    row = supported_row()
    snapshot = row["ingestion_snapshot"]
    if mutation == "ownership":
        snapshot["source_id"] = 42
    elif mutation == "raw_performers":
        snapshot["raw_performers_preserved"] = False
    elif mutation == "people":
        snapshot["identity_snapshot_complete"] = False
    elif mutation == "policy":
        snapshot["policy"]["version"] = 8
    else:
        snapshot["raw_event"]["performers"] = ["Changed"]
    assert reason in comparison.replay_gaps(row)
    assert comparison.prepare_inputs({"records": [row]})[0] == []


def test_raw_capture_and_identity_are_actually_used():
    row = supported_row("Saturday")
    snapshot = row["ingestion_snapshot"]
    snapshot["performers"] = ["Blocked musician"]
    snapshot["raw_event"] = {"performers": ["Blocked musician"]}
    snapshot["raw_event_sha256"] = comparison.digest(snapshot["raw_event"])
    snapshot["people"] = [{"id": 4, "name": "Blocked musician", "visible": False,
                            "block_reason": "non_comedian_musician"}]
    snapshot["identity_sha256"] = comparison.identity_digest(snapshot)
    inputs, _ = comparison.prepare_inputs({"records": [row]})
    result = comparison.run_revision(comparison.REVISIONS["candidate"], inputs)
    assert result["rows"][0]["decision"]["decision"] == "reject"
    assert "blocked_only_lineup" in result["rows"][0]["decision"]["reason_codes"]
    mismatch = copy.deepcopy(inputs)
    mismatch[0]["snapshot"]["raw_event"]["performers"] = ["Different"]
    with pytest.raises(Exception, match="returned non-zero"):
        comparison.run_revision(comparison.REVISIONS["candidate"], mismatch)


@pytest.mark.parametrize("name,link", [("../escape.py", False), ("/absolute.py", False), ("link.py", True)])
def test_revision_archive_rejects_unsafe_paths(tmp_path, name, link):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        item = tarfile.TarInfo(name)
        if link:
            item.type = tarfile.SYMTYPE
            item.linkname = "../escape"
        archive.addfile(item)
    with pytest.raises(ValueError, match="Unsafe revision archive"):
        comparison.extract_source(buffer.getvalue(), tmp_path)


def test_revision_must_be_immutable():
    for revision in ("HEAD", "main", "--output=bad", "346cac726"):
        with pytest.raises(ValueError, match="immutable"):
            comparison.run_revision(revision, [])
