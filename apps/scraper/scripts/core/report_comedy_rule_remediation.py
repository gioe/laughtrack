"""Compare a corrected rule revision with the frozen TASK-4166 candidate offline.

This remains exposed development evidence. Historical post-outcome judgments
describe the archived event, not independent validation of corrected decisions.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

# Direct script execution imports sibling offline tools, without the scripts
# package's database-adapter composition side effects.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import comedy_search_corpus as corpus_tools
    import compare_comedy_event_rules as comparison
else:
    from scripts.core import comedy_search_corpus as corpus_tools
    from scripts.core import compare_comedy_event_rules as comparison

PREVIOUS_CANDIDATE = "346cac72604a6338673fff90f5e3d6781de49b13"
ORIGINAL_DIRECTORY = comparison.SCRAPER / "docs/audits/comedy-rule-comparison"
ORIGINAL_REPORT_SHA256 = "f4e46e376c31936410a6d8361bc12b5f1603ec9d16a1047b9f608576284b8b5d"
ORIGINAL_ADJUDICATION_SHA256 = "ee674e0cd6d7cf48ba5f3d6577dedd1adc41cbd67cf192d28a811bb7833374fc"
CORPUS_MANIFEST_SHA256 = "f6e6e5f11c069e81cb4331cb3884df3b9ceb47ce275db23722c92365a4936c28"


def frozen_json(path, expected_digest):
    raw = Path(path).read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected_digest:
        raise ValueError(f"Frozen artifact digest mismatch: {path}")
    return json.loads(raw)


def load_original_inputs(corpus_root=corpus_tools.BASELINE, original_directory=ORIGINAL_DIRECTORY):
    corpus = corpus_tools.load_corpus(corpus_root)
    if corpus["manifest_sha256"] != CORPUS_MANIFEST_SHA256:
        raise ValueError("Remediation requires the unchanged original corpus manifest")
    original_directory = Path(original_directory)
    original = frozen_json(original_directory / "comparison.json", ORIGINAL_REPORT_SHA256)
    judgments = frozen_json(original_directory / "adjudications.json", ORIGINAL_ADJUDICATION_SHA256)
    previous = original["diagnostic_replay"]
    if (previous["runs"]["candidate"]["git_revision"] != PREVIOUS_CANDIDATE
            or previous["manifest_sha256"] != corpus["manifest_sha256"]
            or previous["corpus_records_sha256"] != comparison.digest(corpus["records"])):
        raise ValueError("Original comparison identity does not match the frozen corpus/candidate")
    # Validate these judgments only against the decisions they actually reviewed.
    comparison.validate_adjudications(corpus, previous, judgments)
    return corpus, original, judgments


def decisions_by_id(replayed, stage):
    return {row["public_show_id"]: row["decision"] for row in replayed["runs"][stage]["rows"]}


def historical_cohort_outcomes(corpus, replayed, judgments):
    """Carry labels forward as exposed development cohorts, never new approvals."""
    before, after = decisions_by_id(replayed, "baseline"), decisions_by_id(replayed, "candidate")
    records = {row["public_show_id"]: row for row in corpus["records"]}
    original_labels = {row["public_show_id"]: row for row in judgments["records"]}
    if len(original_labels) != len(judgments["records"]) or not original_labels.keys() <= before.keys() or set(before) != set(after):
        raise ValueError("Historical cohort or replay identities are missing/duplicated")
    cohorts = {}
    for judgment in sorted({row["judgment"] for row in original_labels.values()}):
        ids = sorted(sid for sid, row in original_labels.items() if row["judgment"] == judgment)
        cohorts[judgment] = {
            "denominators": comparison.row_denominators([records[sid] for sid in ids]),
            "public_show_ids": ids,
            "previous": comparison.outcome_counts([before[sid] for sid in ids]),
            "corrected": comparison.outcome_counts([after[sid] for sid in ids]),
            "transitions": comparison.transitions({sid: before[sid] for sid in ids}, {sid: after[sid] for sid in ids}),
            "corrected_accepted_ids": [sid for sid in ids if after[sid]["decision"] == "accept"],
            "corrected_review_ids": [sid for sid in ids if after[sid]["decision"] == "review"],
            "corrected_rejected_ids": [sid for sid in ids if after[sid]["decision"] == "reject"],
        }
    changed_ids = {sid for sid in before if before[sid]["decision"] != after[sid]["decision"]}
    corrected_proposals = comparison.proposed_ids(before, after)
    return {
        "label_status": "Historical TASK-4166 post-outcome development labels; not fresh, blind or corrected-outcome adjudication.",
        "reviewer": judgments["reviewer"], "reviewed_at": judgments["reviewed_at"],
        "judged_candidate_revision": judgments["candidate_revision"],
        "historical_adjudication_sha256": ORIGINAL_ADJUDICATION_SHA256,
        "cohorts": cohorts,
        "newly_accepted_ids": sorted(sid for sid in changed_ids if after[sid]["decision"] == "accept"),
        "newly_withheld_from_accept_ids": sorted(sid for sid in changed_ids if before[sid]["decision"] == "accept"),
        "newly_rejected_ids": sorted(sid for sid in changed_ids if after[sid]["decision"] == "reject"),
        "changed_ids_without_historical_judgment": sorted(changed_ids - original_labels.keys()),
        "proposed_ids_without_historical_judgment": sorted(corrected_proposals - original_labels.keys()),
        "changed_decisions_requiring_review_ids": sorted(changed_ids),
        "historical_label_genres": dict(sorted(Counter(row["genre"] for row in original_labels.values()).items())),
    }


def build_remediation_report(candidate, *, corpus_root=corpus_tools.BASELINE, original_directory=ORIGINAL_DIRECTORY):
    if not re.fullmatch(r"[0-9a-f]{40}", candidate):
        raise ValueError("Candidate must be a complete immutable git commit SHA")
    corpus, original, judgments = load_original_inputs(corpus_root, original_directory)
    revisions = {"baseline": PREVIOUS_CANDIDATE, "candidate": candidate}
    strict = comparison.replay(corpus, revisions=revisions)
    diagnostic = comparison.replay(corpus, revisions=revisions, diagnostic=True)
    before = decisions_by_id(diagnostic, "baseline")
    original_candidate = decisions_by_id(original["diagnostic_replay"], "candidate")
    if before != original_candidate:
        raise ValueError("Previous candidate no longer reproduces the original TASK-4166 decisions")
    changes = comparison.changed_outcomes(corpus, diagnostic)
    judgments_by_id = {row["public_show_id"]: row for row in judgments["records"]}
    for change in changes:
        change["corrected_outcome_review_status"] = "pending"
        # The original fields explicitly retain their original review timestamp
        # and candidate; this is not a rewritten judgment for the corrected run.
        change["historical_posthoc_judgment"] = judgments_by_id.get(change["public_show_id"])
    return {
        "schema_version": 1, "purpose": "TASK-4160 development rule remediation; not rollout validation",
        "previous_candidate_revision": PREVIOUS_CANDIDATE, "corrected_candidate_revision": candidate,
        "original_comparison_sha256": ORIGINAL_REPORT_SHA256,
        "original_adjudication_sha256": ORIGINAL_ADJUDICATION_SHA256,
        "corpus_version": corpus["corpus_version"], "manifest_sha256": corpus["manifest_sha256"],
        "strict": comparison.comparison_metrics(corpus, strict),
        "title_only_diagnostic": comparison.comparison_metrics(corpus, diagnostic),
        "historical_development_cohorts": historical_cohort_outcomes(corpus, diagnostic, judgments),
        "strict_replay": strict, "diagnostic_replay": diagnostic, "changed_outcomes": changes,
        "limits": [
            "The original public-search corpus, labels, comparison and adjudications are unchanged.",
            "All archived occurrences lack complete source-owned prefilter ingestion snapshots; unsupported rows are not successful removals.",
            "The title-only diagnostic uses unreviewed/off policy and missing performers; public descriptions are not invented collector evidence.",
            "The historical 60 post-outcome judgments are exposed labels, not independent validation or approval of corrected outcomes.",
            "Every changed decision requires separate outcome review; newly proposed exclusions are not automatically adjudicated.",
            "No corpus recall, fresh-event qualification, production enforcement, rollback result or stored-inventory cleanup is inferred.",
        ],
        "database_writes": 0, "network_calls": 0, "model_calls": 0,
    }


def write_report(path, report, *, corpus_root=corpus_tools.BASELINE, original_directory=ORIGINAL_DIRECTORY):
    output = Path(path).resolve()
    for frozen in (Path(corpus_root).resolve(), Path(original_directory).resolve()):
        if output == frozen or output.is_relative_to(frozen):
            raise ValueError("Remediation output must be separate from immutable original artifacts")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x") as handle:
        json.dump(report, handle, sort_keys=True, separators=(",", ":"))
        handle.write("\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Report corrected comedy rules against the immutable TASK-4166 candidate offline.")
    parser.add_argument("--candidate", required=True, help="Full corrected git commit SHA")
    parser.add_argument("--output", required=True, type=Path, help="New JSON file outside the frozen original artifacts")
    args = parser.parse_args(argv)
    report = build_remediation_report(args.candidate)
    write_report(args.output, report)
    print(json.dumps({key: report[key] for key in (
        "previous_candidate_revision", "corrected_candidate_revision", "strict", "title_only_diagnostic",
        "historical_development_cohorts", "database_writes", "network_calls", "model_calls",
    )}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
