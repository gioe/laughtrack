"""Versioned offline replay must not pretend public search is raw ingestion."""

import copy
import io
import json
from pathlib import Path
import subprocess
import sys
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
    return corpus, comparison.replay(corpus, ablations=True)


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
    with pytest.raises(subprocess.CalledProcessError):
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


@pytest.mark.parametrize("policy", [
    {"policy": "invalid"}, {"version": 0}, {"gate_mode": "publish"},
    {"policy": "comedy_only", "reviewed_by": None},
    {"policy": "comedy_only", "reviewed_by": "Reviewer", "reviewed_at": "not-a-date", "evidence": {"review": "snapshot"}},
])
def test_malformed_policy_fails_replay(policy):
    row = supported_row()
    row["ingestion_snapshot"]["policy"].update(policy)
    row["ingestion_snapshot"]["policy_sha256"] = comparison.digest(row["ingestion_snapshot"]["policy"])
    inputs, _ = comparison.prepare_inputs({"records": [row]})
    with pytest.raises(subprocess.CalledProcessError):
        comparison.run_revision(comparison.REVISIONS["candidate"], inputs)


def test_comparison_metrics(versioned):
    corpus, replayed = versioned
    # Reference labels remain independent from the classifier's determinations.
    corpus = copy.deepcopy(corpus)
    corpus["records"][0]["reference_label"]["genre"] = "unknown"
    corpus["records"][1]["reference_label"]["genre"] = "non_comedy"
    corpus["records"][2]["reference_label"]["genre"] = "comedy"
    result = comparison.comparison_metrics(corpus, replayed)
    assert result["evaluated_denominators"]["shows"] == 3
    assert result["evaluated_denominators"]["resolved_native_groups"] == 1
    assert result["versions"]["baseline"]["decisions"] == {"accept": 0, "review": 3, "reject": 0}
    assert result["versions"]["candidate"]["decisions"] == {"accept": 1, "review": 0, "reject": 2}
    assert result["versions"]["candidate"]["comedy_withheld"] == 1
    assert result["versions"]["candidate"]["non_comedy_accepted"] == 1
    assert result["versions"]["candidate"]["reference_genre_outcomes"]["unknown"]["reject"] == 1
    assert result["versions"]["candidate"]["audience_formats"]["instruction"] == 1
    assert result["reference_comedy_newly_withheld_ids"] == []  # Already held at baseline.
    assert result["combined_transitions"] == {"review->accept": 1, "review->reject": 2}
    assert result["proposed_exclusion_ids"] == [91, 93]
    assert result["overlap"]["unique_matched"]["shows"] == 3
    assert result["overlap"]["sum_of_rule_occurrence_matches"] > 3
    assert result["overlap"]["multiple_rule_occurrences"] >= 1
    assert result["rule_ablations"]["audience_format:instruction"]["combined_minus_this_rule_outcomes"] == {
        "accept": 2, "review": 0, "reject": 1}
    assert result["recall"] is None and result["population_false_positive_rate"] is None

    unsupported = {**replayed, "runs": {name: {**run, "rows": []} for name, run in replayed["runs"].items()},
                   "unsupported": [{"public_show_id": row["public_show_id"]} for row in corpus["records"]]}
    empty = comparison.comparison_metrics(corpus, unsupported)
    assert empty["evaluated_denominators"]["shows"] == 0
    assert empty["versions"]["candidate"]["decisions"] == {"accept": 0, "review": 0, "reject": 0}
    assert empty["unsupported_shows"] == 3


def test_read_only_evidence_report(versioned):
    corpus, replayed = versioned
    changed = comparison.changed_outcomes(corpus, replayed)
    assert len(changed) == 3
    for row in changed:
        assert row["source_id"] == 8 and row["event_key"] == "native:provider-123"
        assert row["public_show_id"] in {91, 92, 93}
        assert row["title"] and row["venue"]
        assert row["baseline_revision"] == comparison.REVISIONS["baseline"]
        assert row["candidate_revision"] == comparison.REVISIONS["candidate"]
        assert row["old"]["reason_codes"] and row["new"]["reason_codes"]
        assert all(item["detail"] == row["title"] and item["rule_version"] for item in row["new"]["evidence"])
    assert all(run["io_contract"] == {"database_writes": 0, "network_calls": 0, "model_calls": 0}
               for run in replayed["runs"].values())
    assert not any("comedy_eligibility_model.py" in path for run in replayed["runs"].values()
                   for path in run["imported_source_sha256"])


def test_native_group_denominators_do_not_promote_fallback_keys():
    native = supported_row()
    repeated_native = copy.deepcopy(native)
    repeated_native["public_show_id"] = 92
    fallback = copy.deepcopy(native)
    fallback["public_show_id"] = 93
    fallback["source_evidence"]["publication_candidates"][0]["event_key"] = "fallback:hash"
    unresolved = copy.deepcopy(native)
    unresolved["public_show_id"] = 94
    unresolved["source_evidence"] = {"status": "unresolved", "publication_candidates": [],
                                      "source_performance_id": "known-provider-id-without-owner"}
    result = comparison.row_denominators([native, repeated_native, fallback, unresolved])
    assert result["shows"] == 4
    assert result["resolved_source_event_groups"] == 2
    assert result["resolved_native_groups"] == 1
    assert result["unresolved_native_group_occurrences"] == 2
    assert result["native_identifier_occurrences"] == 1


@pytest.mark.parametrize("attempt,message", [
    ("import socket; socket.create_connection(('example.com', 443))", "forbids network"),
    ("import psycopg2; psycopg2.connect('dbname=should_never_connect')", "forbids network"),
    ("import sqlite3; sqlite3.connect(':memory:')", "forbids network"),
    ("import openai", "forbids model"),
])
def test_worker_blocks_connection_and_model_import_side_effects(tmp_path, attempt, message):
    archive = subprocess.run(["git", "-C", str(comparison.REPO), "archive", comparison.REVISIONS["candidate"],
                              *comparison.SOURCE_PATHS], check=True, capture_output=True).stdout
    comparison.extract_source(archive, tmp_path)
    runtime = tmp_path / "apps/scraper"
    gate = runtime / "src/laughtrack/core/comedy_eligibility_gate.py"
    gate.write_text(gate.read_text() + "\n" + attempt + "\n")
    result = subprocess.run([sys.executable, str(comparison.SCRIPT), "--worker", str(runtime)],
                            input=json.dumps({"inputs": [], "ablations": False}), capture_output=True, text=True)
    assert result.returncode != 0 and message in result.stderr


def test_committed_adjudications_cover_proposed_exclusions():
    corpus = comedy_search_corpus.load_corpus()
    replayed = comparison.replay(corpus, revisions={key: comparison.REVISIONS[key] for key in ("baseline", "candidate")},
                                 diagnostic=True)
    path = Path(comparison.SCRAPER / "docs/audits/comedy-rule-comparison/adjudications.json")
    document = json.loads(path.read_bytes())
    summary = comparison.validate_adjudications(corpus, replayed, document)
    expected = comparison.comparison_metrics(corpus, replayed)["proposed_exclusion_ids"]
    assert summary["occurrences"] == len(expected)
    assert sum(summary["judgments"].values()) == len(expected)
    missing = copy.deepcopy(document)
    missing["records"].pop()
    with pytest.raises(ValueError, match="every proposed exclusion"):
        comparison.validate_adjudications(corpus, replayed, missing)
    altered = copy.deepcopy(document)
    altered["records"][0]["evidence"][0]["excerpt"] = "A fabricated excerpt"
    with pytest.raises(ValueError, match="not in the frozen event"):
        comparison.validate_adjudications(corpus, replayed, altered)
