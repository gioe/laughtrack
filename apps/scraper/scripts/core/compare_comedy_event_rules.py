"""Offline versioned decision replay and explicitly incomplete title diagnostics.

The immutable search archive is not an ingestion snapshot. Strict replay never
substitutes its public lineup, venue branding, or descriptions for missing raw
performers, reviewed source policy, and collector-validated event evidence.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile

REVISIONS = {
    "baseline": "a0f28e84f32edca40e8f3e09d6158e4545a2489b",
    "after_4163": "4988d1e4a90abeb2ff13a215b787fc9ab76c605c",
    "after_4164": "df90d01eeec5d8b67ae214c02adfc69692c6d3fb",
    "candidate": "346cac72604a6338673fff90f5e3d6781de49b13",
}
SCRIPT = Path(__file__).resolve()
SCRAPER = SCRIPT.parents[2]
REPO = SCRAPER.parents[1]
SOURCE_PATHS = ("apps/scraper/src", "apps/scraper/sql", "apps/scraper/pyproject.toml")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def identity_digest(snapshot):
    return digest({key: snapshot.get(key) for key in (
        "performers", "people", "denied", "raw_performers_preserved", "identity_snapshot_complete",
    )})


def replay_gaps(row):
    """Require captured ownership and complete pre-filter inputs, never infer them."""
    gaps = []
    source = row.get("source_evidence", {})
    candidates = source.get("publication_candidates", [])
    if source.get("status") != "resolved" or len(candidates) != 1:
        gaps.append("unresolved_source_ownership")
    snapshot = row.get("ingestion_snapshot")
    if not isinstance(snapshot, dict):
        return gaps + ["missing_prefilter_performers", "missing_identity_snapshot",
                       "missing_source_policy_snapshot", "missing_raw_event_snapshot"]
    if (snapshot.get("raw_performers_preserved") is not True
            or not isinstance(snapshot.get("performers"), list)
            or not all(isinstance(name, str) and name.strip() for name in snapshot["performers"])):
        gaps.append("missing_prefilter_performers")
    if (snapshot.get("identity_snapshot_complete") is not True
            or not isinstance(snapshot.get("people"), list) or not isinstance(snapshot.get("denied"), list)
            or snapshot.get("identity_sha256") != identity_digest(snapshot)):
        gaps.append("missing_identity_snapshot")
    policy = snapshot.get("policy")
    if (not isinstance(policy, dict) or not {"policy", "gate_mode", "version", "reviewed_by", "reviewed_at", "evidence"} <= policy.keys()
            or snapshot.get("policy_sha256") != digest(policy)):
        gaps.append("missing_source_policy_snapshot")
    if (not isinstance(snapshot.get("raw_event"), dict)
            or not isinstance(snapshot.get("adapter_evidence"), list)
            or snapshot.get("raw_event_sha256") != digest(snapshot["raw_event"])):
        gaps.append("missing_raw_event_snapshot")
    if candidates and (snapshot.get("source_id"), snapshot.get("event_key")) != (
            candidates[0].get("source_id"), candidates[0].get("event_key")):
        gaps.append("snapshot_source_mismatch")
    if type(snapshot.get("source_id")) is not int or snapshot["source_id"] <= 0 or not snapshot.get("event_key"):
        gaps.append("invalid_source_identity")
    if snapshot.get("club_id") != row.get("context", {}).get("club_id"):
        gaps.append("snapshot_venue_mismatch")
    return gaps


def source_identity(row):
    source = row.get("source_evidence", {})
    candidates = source.get("publication_candidates", [])
    return {"source_mapping_status": source.get("status", "unresolved"),
            "publication_candidates": candidates,
            "source_id": candidates[0].get("source_id") if source.get("status") == "resolved" and len(candidates) == 1 else None,
            "event_key": candidates[0].get("event_key") if source.get("status") == "resolved" and len(candidates) == 1 else None,
            "source_performance_id": source.get("source_performance_id"),
            "last_scraped_by": source.get("last_scraped_by")}


def prepare_inputs(corpus, *, diagnostic=False):
    """Use exactly the same input bytes for every revision; unsupported rows stay out."""
    inputs, unsupported = [], []
    for row in corpus["records"]:
        gaps = replay_gaps(row)
        if gaps:
            unsupported.append({"public_show_id": row["public_show_id"], **source_identity(row), "reasons": gaps})
        if gaps and not diagnostic:
            continue
        if diagnostic:
            snapshot = {"source_id": None, "event_key": None,
                        "policy": {"policy": "unreviewed", "gate_mode": "off", "version": 1,
                                   "reviewed_by": None, "reviewed_at": None, "evidence": {}},
                        "performers": [], "people": [], "denied": [], "adapter_evidence": [],
                        "raw_event": {}, "raw_performers_preserved": False}
        else:
            snapshot = row["ingestion_snapshot"]
        inputs.append({"public_show_id": row["public_show_id"], "title": row["event_evidence"]["title"],
                       "snapshot": snapshot})
    return inputs, unsupported


def extract_source(archive, destination):
    """Extract regular source files only; reject traversal and all link types."""
    root = Path(destination).resolve()
    with tarfile.open(fileobj=io.BytesIO(archive)) as saved:
        members = saved.getmembers()
        for member in members:
            path = (root / member.name).resolve()
            if Path(member.name).is_absolute() or not path.is_relative_to(root) or not (member.isdir() or member.isfile()):
                raise ValueError("Unsafe revision archive path or file type")
        for member in members:
            path = root / member.name
            if member.isdir():
                path.mkdir(parents=True, exist_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(saved.extractfile(member).read())


def run_revision(revision, inputs, *, repo=REPO, ablations=False):
    """Execute committed source in a fresh interpreter, isolated from editable installs."""
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Replay requires a complete immutable git commit SHA")
    resolved = subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify", revision + "^{commit}"],
                              check=True, capture_output=True, text=True).stdout.strip()
    if resolved != revision:
        raise ValueError("Revision is not a commit")
    archive = subprocess.run(["git", "-C", str(repo), "archive", revision, *SOURCE_PATHS],
                             check=True, capture_output=True).stdout
    with tempfile.TemporaryDirectory(prefix="comedy-replay-") as folder:
        extract_source(archive, folder)
        runtime = Path(folder) / "apps/scraper"
        environment = {**os.environ, "PYTHONPATH": str(runtime / "src") + os.pathsep + str(runtime),
                       "PYTHONDONTWRITEBYTECODE": "1", "COMEDY_MODEL_ENABLED": "0",
                       "COMEDY_MODEL_CACHE_ENABLED": "0"}
        result = subprocess.run([sys.executable, str(SCRIPT), "--worker", str(runtime)],
                                input=json.dumps({"inputs": inputs, "ablations": ablations}), text=True, capture_output=True,
                                cwd=runtime, env=environment, check=True, timeout=120)
    value = json.loads(result.stdout)
    return {"git_revision": revision, "source_archive_sha256": hashlib.sha256(archive).hexdigest(),
            "input_sha256": digest(inputs), **value}


def worker(runtime, inputs, *, ablations=False):
    """Call the same pure capture/classification functions used by the write gate.

    Publication staging, human-review overrides and optional model caches are
    deliberately outside this deterministic rule comparison.
    """
    import socket
    import sqlite3
    import psycopg2
    import importlib.abc
    from types import SimpleNamespace

    def forbidden(*args, **kwargs):
        raise RuntimeError("Offline replay forbids network and database connections")

    socket.socket.connect = forbidden
    socket.socket.connect_ex = forbidden
    socket.create_connection = forbidden
    socket.getaddrinfo = forbidden
    psycopg2.connect = forbidden
    psycopg2._psycopg.connect = forbidden
    sqlite3.connect = forbidden
    class NoModelImports(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path, target=None):
            if fullname.split(".")[0] in {"openai", "anthropic"} or fullname == "laughtrack.core.comedy_eligibility_model":
                raise RuntimeError("Offline replay forbids model imports")
            return None
    sys.meta_path.insert(0, NoModelImports())
    # Audit hooks also catch direct low-level socket/sqlite calls.
    def audit(event, args):
        if event in {"socket.connect", "socket.getaddrinfo", "sqlite3.connect"}:
            forbidden()
    sys.addaudithook(audit)
    runtime = Path(runtime).resolve()
    sys.path[:0] = [str(runtime / "src"), str(runtime)]
    from laughtrack.core import comedy_eligibility as classifier
    from laughtrack.core.comedy_eligibility_gate import capture_event_inputs, event_evidence
    from laughtrack.core.entities.club.comedy_policy import SourceComedyPolicy

    rows = []
    for entry in inputs:
        snapshot = entry["snapshot"]
        show = SimpleNamespace(name=entry["title"], eligibility_evidence=list(snapshot["adapter_evidence"]),
                               eligibility_performer_names=[], eligibility_raw_performers_preserved=False)
        capture_event_inputs(show, snapshot["raw_event"])
        # An explicit raw snapshot must agree with what the shared capture sees.
        if snapshot["raw_performers_preserved"] and (
                not show.eligibility_raw_performers_preserved
                or show.eligibility_performer_names != snapshot["performers"]):
            raise ValueError("Raw performer snapshot differs from captured event")
        evidence = event_evidence(show)
        policy = SourceComedyPolicy(**snapshot["policy"])
        if policy.policy == "comedy_only":
            if not policy.reviewed_by or not policy.reviewed_by.strip() or not policy.evidence or not policy.reviewed_at:
                raise ValueError("Reviewed comedy-only source snapshot lacks review evidence")
            reviewed_at = datetime.fromisoformat(str(policy.reviewed_at).replace("Z", "+00:00"))
            if reviewed_at.tzinfo is None:
                raise ValueError("Reviewed source timestamp must have timezone")
        arguments = dict(source_id=snapshot["source_id"], policy=policy,
            performers=[classifier.PerformerObservation(name) for name in snapshot["performers"]],
            people=[classifier.CanonicalPerson(**person) for person in snapshot["people"]],
            denied=[classifier.DeniedName(**person) for person in snapshot["denied"]],
        )
        def classify(items):
            return classifier.classify_comedy_eligibility(evidence=items, **arguments).to_dict()
        decision = classify(evidence)
        row = {"public_show_id": entry["public_show_id"], "policy_sha256": digest(snapshot["policy"]),
               "decision": decision}
        if ablations:
            def key(item):
                return f"{item.rule_family}:{item.rule_reason}" if item.rule_family else None
            def compact(value):
                return {field: value[field] for field in ("decision", "content_status", "audience_format", "format_disposition")}
            hits = sorted({key(item) for item in evidence if key(item) is not None})
            base = [item for item in evidence if key(item) is None]
            row["ablations"] = {"without_typed_rules": compact(classify(base)), "rules": {
                rule: {"standalone": compact(classify(base + [item for item in evidence if key(item) == rule])),
                       "without_rule": compact(classify([item for item in evidence if key(item) != rule]))}
                for rule in hits}}
        rows.append(row)
    imported = {}
    for name, module in sorted(sys.modules.items()):
        if name.startswith(("laughtrack.", "sql.")) and getattr(module, "__file__", None):
            path = Path(module.__file__).resolve()
            if not path.is_relative_to(runtime):
                raise ValueError("Replay imported code outside frozen revision: " + name)
            imported[str(path.relative_to(runtime))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"classifier_version": classifier.CLASSIFIER_VERSION, "imported_source_sha256": imported,
            "rows": rows, "io_contract": {"database_writes": 0, "network_calls": 0, "model_calls": 0}}


def replay(corpus, *, revisions=REVISIONS, diagnostic=False, ablations=False):
    inputs, unsupported = prepare_inputs(corpus, diagnostic=diagnostic)
    runs = {name: run_revision(revision, inputs, ablations=ablations and name == "candidate")
            for name, revision in revisions.items()}
    if len({run["input_sha256"] for run in runs.values()}) != 1:
        raise ValueError("Revision inputs differ")
    return {"mode": "title_only_diagnostic" if diagnostic else "strict_ingestion_replay",
            "corpus_version": corpus["corpus_version"], "manifest_sha256": corpus["manifest_sha256"],
            "corpus_records_sha256": digest(corpus["records"]), "input_sha256": digest(inputs),
            "input_count": len(inputs), "unsupported": unsupported,
            "unsupported_reasons": dict(Counter(reason for row in unsupported for reason in row["reasons"])),
            "runs": runs}


def row_denominators(records):
    identities = [source_identity(row) for row in records]
    resolved = {(identity["source_id"], identity["event_key"]) for identity in identities
                if identity["source_id"] is not None and identity["event_key"]}
    native = {(source, key) for source, key in resolved if key.startswith("native:")}
    return {"shows": len(records),
            "venue_title_groups": len({(row["context"]["club_id"], row["event_evidence"]["title"]) for row in records}),
            "resolved_source_event_groups": len(resolved),
            "resolved_native_groups": len(native),
            "unresolved_native_group_occurrences": sum(identity["source_id"] is None
                                                        or not (identity["event_key"] or "").startswith("native:")
                                                        for identity in identities),
            "native_identifier_occurrences": sum(bool(source_identity(row)["source_performance_id"]) for row in records)}


def outcome_counts(rows):
    return {key: sum(row["decision"] == key for row in rows) for key in ("accept", "review", "reject")}


def transitions(before, after):
    return dict(sorted(Counter(f"{before[sid]['decision']}->{after[sid]['decision']}" for sid in before).items()))


def outcome_summary(records, decisions):
    selected = [row for row in records if row["public_show_id"] in decisions]
    values = list(decisions.values())
    labels = {}
    for genre in ("comedy", "non_comedy", "unknown"):
        ids = [row["public_show_id"] for row in selected if row["reference_label"]["genre"] == genre]
        labels[genre] = {"shows": len(ids), **outcome_counts([decisions[sid] for sid in ids])}
    formats = Counter(value.get("audience_format", "not_supported_by_revision") for value in values)
    return {"denominators": row_denominators(selected), "decisions": outcome_counts(values),
            "audience_formats": dict(sorted(formats.items())),
            "format_dispositions": dict(sorted(Counter(value.get("format_disposition", "not_supported_by_revision")
                                                       for value in values).items())),
            "reference_genre_outcomes": labels,
            "reference_selection_outcomes": {selection: outcome_counts([
                decisions[row["public_show_id"]] for row in selected if row["reference_label"]["selection"] == selection])
                for selection in ("flagged", "control", "unreviewed")},
            "comedy_retained": labels["comedy"]["accept"],
            "comedy_withheld": labels["comedy"]["review"] + labels["comedy"]["reject"],
            "non_comedy_accepted": labels["non_comedy"]["accept"]}


def proposed_ids(before, after):
    return {sid for sid in before if after[sid]["decision"] == "reject"
            or (before[sid]["decision"] == "accept" and after[sid]["decision"] != "accept")}


def comparison_metrics(corpus, replayed):
    """Paired denominators, sequential effects and candidate evidence ablations."""
    records = corpus["records"]
    decisions = {name: {row["public_show_id"]: row["decision"] for row in run["rows"]}
                 for name, run in replayed["runs"].items()}
    ids = set(decisions["baseline"])
    if any(set(rows) != ids for rows in decisions.values()):
        raise ValueError("Revision row identities differ")
    before, after = decisions["baseline"], decisions["candidate"]
    stages = list(decisions)
    incremental = {f"{left}->{right}": transitions(decisions[left], decisions[right])
                   for left, right in zip(stages, stages[1:])}
    by_id = {row["public_show_id"]: row for row in records}
    proposed = proposed_ids(before, after)
    by_proxy = {}
    for proxy in sorted({source_identity(by_id[sid])["last_scraped_by"] or "unknown" for sid in ids}):
        members = [by_id[sid] for sid in ids if (source_identity(by_id[sid])["last_scraped_by"] or "unknown") == proxy]
        by_proxy[proxy] = {"denominators": row_denominators(members),
                          "before": outcome_counts([before[row["public_show_id"]] for row in members]),
                          "after": outcome_counts([after[row["public_show_id"]] for row in members])}
    by_source = {}
    for source in sorted({source_identity(by_id[sid])["source_id"] for sid in ids
                          if source_identity(by_id[sid])["source_id"] is not None}):
        members = [by_id[sid] for sid in ids if source_identity(by_id[sid])["source_id"] == source]
        by_source[str(source)] = {"denominators": row_denominators(members),
                                  "before": outcome_counts([before[row["public_show_id"]] for row in members]),
                                  "after": outcome_counts([after[row["public_show_id"]] for row in members])}
    candidate_rows = replayed["runs"]["candidate"]["rows"]
    variants = {row["public_show_id"]: row["ablations"] for row in candidate_rows if "ablations" in row}
    rule_effects, overlap = {}, {}
    if variants:
        if set(variants) != ids:
            raise ValueError("Partial ablation coverage")
        untyped = {sid: row["without_typed_rules"] for sid, row in variants.items()}
        keys = sorted({key for row in variants.values() for key in row["rules"]})
        for key in keys:
            hit_ids = {sid for sid, row in variants.items() if key in row["rules"]}
            alone = {sid: row["rules"][key]["standalone"] if sid in hit_ids else untyped[sid]
                     for sid, row in variants.items()}
            without = {sid: row["rules"][key]["without_rule"] if sid in hit_ids else after[sid]
                       for sid, row in variants.items()}
            rule_effects[key] = {"matched": row_denominators([by_id[sid] for sid in hit_ids]),
                                 "matched_public_show_ids": sorted(hit_ids),
                                 "standalone_outcomes": outcome_counts(list(alone.values())),
                                 "standalone_transitions_from_untyped": transitions(untyped, alone),
                                 "combined_minus_this_rule_outcomes": outcome_counts(list(without.values())),
                                 "incremental_transitions_into_combined": transitions(without, after)}
        hit_sets = {sid: set(row["rules"]) for sid, row in variants.items()}
        touched = {sid for sid, hits in hit_sets.items() if hits}
        overlap = {"unique_matched": row_denominators([by_id[sid] for sid in touched]),
                   "sum_of_rule_occurrence_matches": sum(len(hits) for hits in hit_sets.values()),
                   "multiple_rule_occurrences": sum(len(hits) > 1 for hits in hit_sets.values()),
                   "exact_rule_combinations": dict(sorted(Counter(" + ".join(sorted(hits)) for hits in hit_sets.values() if hits).items())),
                   "without_typed_rules_outcomes": outcome_counts(list(untyped.values()))}
    return {"mode": replayed["mode"], "corpus_denominators": row_denominators(records),
            "evaluated_denominators": row_denominators([by_id[sid] for sid in ids]),
            "unsupported_shows": len(replayed["unsupported"]),
            "versions": {name: outcome_summary(records, rows) for name, rows in decisions.items()},
            "sequential_incremental_transitions": incremental, "combined_transitions": transitions(before, after),
            "proposed_exclusion_denominators": row_denominators([by_id[sid] for sid in proposed]),
            "proposed_exclusion_ids": sorted(proposed),
            "reference_comedy_newly_withheld_ids": sorted(sid for sid in ids if by_id[sid]["reference_label"]["genre"] == "comedy"
                                                        and before[sid]["decision"] == "accept" and after[sid]["decision"] != "accept"),
            "resolved_source_outcomes": by_source,
            "last_scraped_by_proxy_outcomes_not_source_ownership": by_proxy,
            "rule_ablations": rule_effects, "overlap": overlap,
            "ablation_caveat": "Candidate classifier with typed evidence selected/removed; legacy untyped evidence retained. These are not historical revision baselines.",
            "recall": None, "population_false_positive_rate": None}


def changed_outcomes(corpus, replayed):
    before = {row["public_show_id"]: row["decision"] for row in replayed["runs"]["baseline"]["rows"]}
    after = {row["public_show_id"]: row["decision"] for row in replayed["runs"]["candidate"]["rows"]}
    rows = []
    for row in corpus["records"]:
        sid = row["public_show_id"]
        if sid not in before:
            continue
        previous, current = before[sid], after[sid]
        if previous["decision"] == current["decision"]:
            continue
        rows.append({"public_show_id": sid, **source_identity(row), "title": row["event_evidence"]["title"],
                     "venue": row["context"]["club_name"], "club_id": row["context"]["club_id"],
                     "mode": replayed["mode"], "original_reference_label": row["reference_label"],
                     "baseline_revision": replayed["runs"]["baseline"]["git_revision"],
                     "candidate_revision": replayed["runs"]["candidate"]["git_revision"],
                     "old": previous, "new": current})
    return rows


def validate_adjudications(corpus, replayed, document):
    """Check post-outcome review coverage; never feed these judgments into replay."""
    if (document.get("schema_version") != 1 or not document.get("reviewer") or not document.get("review_type")
            or not document.get("reviewed_at")
            or document.get("candidate_revision") != replayed["runs"]["candidate"]["git_revision"]
            or document.get("manifest_sha256") != corpus["manifest_sha256"]
            or document.get("corpus_version") != corpus["corpus_version"]):
        raise ValueError("Adjudication version or review provenance mismatch")
    before = {row["public_show_id"]: row["decision"] for row in replayed["runs"]["baseline"]["rows"]}
    after = {row["public_show_id"]: row["decision"] for row in replayed["runs"]["candidate"]["rows"]}
    expected = proposed_ids(before, after)
    rows = document.get("records", [])
    if len(rows) != len(expected) or {row["public_show_id"] for row in rows} != expected:
        raise ValueError("Adjudication must cover every proposed exclusion exactly once")
    originals = {row["public_show_id"]: (index, row) for index, row in enumerate(corpus["records"])}
    for row in rows:
        sid = row["public_show_id"]
        index, original = originals[sid]
        if (row.get("title") != original["event_evidence"]["title"] or row.get("venue") != original["context"]["club_name"]
                or row.get("original_reference_label") != original["reference_label"]
                or row.get("source_evidence") != original["source_evidence"]
                or row.get("baseline_decision") != before[sid]["decision"]
                or row.get("candidate_decision") != after[sid]["decision"]
                or row.get("candidate_reason_codes") != after[sid]["reason_codes"]
                or row.get("genre") not in {"comedy", "non_comedy", "unknown"}
                or not row.get("judgment") or not row.get("rationale") or not row.get("evidence")):
            raise ValueError("Adjudication identity, evidence or outcome mismatch")
        for evidence in row["evidence"]:
            field = {"name": "title", "description": "description"}.get(evidence.get("field"))
            if (field is None or not evidence.get("excerpt")
                    or evidence["excerpt"] not in (original["event_evidence"].get(field) or "")
                    or evidence.get("reference") != f"raw/page-{index // 500}.json#/data/{index % 500}/{evidence['field']}"):
                raise ValueError("Adjudication excerpt is not in the frozen event")
    return {"sha256": digest(document), "review_type": document["review_type"], "reviewer": document["reviewer"],
            "occurrences": len(rows), "judgments": dict(sorted(Counter(row["judgment"] for row in rows).items())),
            "genres": dict(sorted(Counter(row["genre"] for row in rows).items()))}


def build_report(corpus, *, adjudications=None):
    strict = replay(corpus)
    diagnostic = replay(corpus, diagnostic=True, ablations=True)
    report = {"schema_version": 1, "strict": comparison_metrics(corpus, strict),
              "title_only_diagnostic": comparison_metrics(corpus, diagnostic),
              "strict_replay": strict, "diagnostic_replay": diagnostic,
              "changed_outcomes": changed_outcomes(corpus, diagnostic),
              "limits": ["Search publication is not a baseline ingestion acceptance decision.",
                         "No source ownership, pre-filter performer or source policy reconstruction from public data.",
                         "Public descriptions are reserved for manual adjudication, not invented collector evidence.",
                         "Development comparison only: no blind validation, recall, rollout or inventory suppression."],
              "database_writes": 0, "network_calls": 0, "model_calls": 0}
    if adjudications is not None:
        report["supplemental_adjudication"] = validate_adjudications(corpus, diagnostic, adjudications)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compare frozen ingestion rule revisions offline.")
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--corpus", type=Path, default=SCRAPER / "docs/audits/comedy-search-rules/baseline-v1")
    parser.add_argument("--output", type=Path, help="New local report JSON file; refuses overwriting")
    parser.add_argument("--adjudications", type=Path, help="Optional post-outcome development review to validate")
    args = parser.parse_args(argv)
    if args.worker:
        request = json.load(sys.stdin)
        print(json.dumps(worker(args.worker, request["inputs"], ablations=request["ablations"]), sort_keys=True))
    else:
        sys.path.insert(0, str(SCRIPT.parent))
        from comedy_search_corpus import load_corpus
        corpus = load_corpus(args.corpus)
        report = build_report(corpus, adjudications=json.loads(args.adjudications.read_bytes()) if args.adjudications else None)
        if args.output:
            output = args.output.resolve()
            frozen = args.corpus.resolve()
            if output == frozen or output.is_relative_to(frozen):
                parser.error("Output cannot modify the frozen corpus")
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("x") as handle:
                json.dump(report, handle, sort_keys=True, separators=(",", ":"))
                handle.write("\n")
        print(json.dumps({key: value for key, value in report.items()
                          if key not in {"strict_replay", "diagnostic_replay", "changed_outcomes"}}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
