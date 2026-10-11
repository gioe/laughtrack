"""Development remediation preserves history and makes every changed result reviewable."""

import copy
import hashlib
import json
import socket

import psycopg2
import pytest

from scripts.core import report_comedy_rule_remediation as remediation


def test_same_corpus_remediation_report(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Remediation must not connect to a database or the network")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(psycopg2, "connect", forbidden)
    # Even hostile inherited model flags cannot turn offline replay into a call.
    monkeypatch.setenv("COMEDY_MODEL_ENABLED", "1")
    monkeypatch.setenv("COMEDY_MODEL_CACHE_ENABLED", "1")
    paths = [remediation.ORIGINAL_DIRECTORY / name for name in ("comparison.json", "adjudications.json")]
    before_hashes = [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths]
    report = remediation.build_remediation_report(remediation.PREVIOUS_CANDIDATE)
    assert report["strict"]["evaluated_denominators"]["shows"] == 0
    assert report["strict"]["unsupported_shows"] == 2886
    assert report["title_only_diagnostic"]["evaluated_denominators"]["shows"] == 2886
    assert report["changed_outcomes"] == []
    assert report["diagnostic_replay"]["runs"]["baseline"]["input_sha256"] == report["diagnostic_replay"]["runs"]["candidate"]["input_sha256"]
    cohorts = report["historical_development_cohorts"]
    assert cohorts["cohorts"]["supported_non_comedy"]["corrected"] == {"accept": 0, "review": 0, "reject": 6}
    assert cohorts["cohorts"]["live_comedy_withheld"]["corrected"] == {"accept": 0, "review": 12, "reject": 2}
    assert cohorts["judged_candidate_revision"] == remediation.PREVIOUS_CANDIDATE
    assert cohorts["changed_decisions_requiring_review_ids"] == []
    assert "not fresh" in cohorts["label_status"]
    assert all(report[key] == 0 for key in ("database_writes", "network_calls", "model_calls"))
    assert [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths] == before_hashes


def cohort_fixture():
    records = [{"public_show_id": sid, "context": {"club_id": sid, "club_name": "Venue"},
                "event_evidence": {"title": f"Event {sid}"},
                "source_evidence": {"status": "unresolved", "publication_candidates": []}}
               for sid in range(1, 5)]
    judgments = {"reviewer": "historical-agent", "reviewed_at": "2026-10-11T00:00:00Z",
                 "candidate_revision": remediation.PREVIOUS_CANDIDATE, "records": [
                     {"public_show_id": 1, "judgment": "supported_non_comedy", "genre": "non_comedy"},
                     {"public_show_id": 2, "judgment": "live_comedy_withheld", "genre": "comedy"},
                     {"public_show_id": 3, "judgment": "live_comedy_withheld", "genre": "comedy"},
                 ]}
    before = [(1, "reject"), (2, "review"), (3, "reject"), (4, "accept")]
    after = [(1, "reject"), (2, "accept"), (3, "review"), (4, "reject")]
    replayed = {"runs": {name: {"rows": [{"public_show_id": sid, "decision": {"decision": decision}}
                                         for sid, decision in pairs]}
                          for name, pairs in (("baseline", before), ("candidate", after))}}
    return {"records": records}, replayed, judgments


def test_remediation_reports_retention_losses_and_unreviewed_changes():
    corpus, replayed, judgments = cohort_fixture()
    saved = copy.deepcopy(judgments)
    report = remediation.historical_cohort_outcomes(corpus, replayed, judgments)
    assert report["cohorts"]["supported_non_comedy"]["corrected"]["reject"] == 1
    assert report["cohorts"]["live_comedy_withheld"]["corrected"] == {"accept": 1, "review": 1, "reject": 0}
    assert report["newly_accepted_ids"] == [2]
    assert report["newly_withheld_from_accept_ids"] == [4]
    assert report["newly_rejected_ids"] == [4]
    assert report["changed_ids_without_historical_judgment"] == [4]
    assert report["proposed_ids_without_historical_judgment"] == [4]
    assert report["changed_decisions_requiring_review_ids"] == [2, 3, 4]
    assert judgments == saved
    # A regression that starts accepting labeled non-comedy must be visible.
    replayed["runs"]["candidate"]["rows"][0]["decision"]["decision"] = "accept"
    changed = remediation.historical_cohort_outcomes(corpus, replayed, judgments)
    assert changed["cohorts"]["supported_non_comedy"]["corrected"]["accept"] == 1
    assert changed["newly_accepted_ids"] == [1, 2]


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "missing_candidate"])
def test_historical_cohorts_require_complete_identity_coverage(mutation):
    corpus, replayed, judgments = cohort_fixture()
    if mutation == "missing":
        judgments["records"][0]["public_show_id"] = 999
    elif mutation == "duplicate":
        judgments["records"].append(copy.deepcopy(judgments["records"][0]))
    else:
        replayed["runs"]["candidate"]["rows"].pop()
    with pytest.raises(ValueError, match="identities"):
        remediation.historical_cohort_outcomes(corpus, replayed, judgments)


def test_history_digest_tampering_is_rejected(tmp_path):
    path = tmp_path / "original.json"
    path.write_text('{"review": "changed"}')
    with pytest.raises(ValueError, match="digest mismatch"):
        remediation.frozen_json(path, remediation.ORIGINAL_ADJUDICATION_SHA256)
    for name in ("HEAD", "main", "346cac726", "--candidate=anything"):
        with pytest.raises(ValueError, match="complete immutable"):
            remediation.build_remediation_report(name)


def test_report_output_cannot_modify_original_artifacts(tmp_path):
    corpus = tmp_path / "baseline"
    original = tmp_path / "comparison"
    for path in (corpus / "manifest.json", original / "adjudications.json", original / "new.json"):
        with pytest.raises(ValueError, match="separate"):
            remediation.write_report(path, {}, corpus_root=corpus, original_directory=original)
        assert not path.exists()
    output = tmp_path / "remediation.json"
    remediation.write_report(output, {"development_only": True}, corpus_root=corpus, original_directory=original)
    assert json.loads(output.read_text()) == {"development_only": True}
    with pytest.raises(FileExistsError):
        remediation.write_report(output, {}, corpus_root=corpus, original_directory=original)
