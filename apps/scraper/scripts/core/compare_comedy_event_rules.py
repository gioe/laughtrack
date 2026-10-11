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


def run_revision(revision, inputs, *, repo=REPO):
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
                                input=json.dumps(inputs), text=True, capture_output=True,
                                cwd=runtime, env=environment, check=True, timeout=120)
    value = json.loads(result.stdout)
    return {"git_revision": revision, "source_archive_sha256": hashlib.sha256(archive).hexdigest(),
            "input_sha256": digest(inputs), **value}


def worker(runtime, inputs):
    """Call the same pure capture/classification functions used by the write gate.

    Publication staging, human-review overrides and optional model caches are
    deliberately outside this deterministic rule comparison.
    """
    import socket
    import sqlite3
    import psycopg2
    from types import SimpleNamespace

    def forbidden(*args, **kwargs):
        raise RuntimeError("Offline replay forbids network and database connections")

    socket.socket.connect = forbidden
    socket.socket.connect_ex = forbidden
    socket.create_connection = forbidden
    socket.getaddrinfo = forbidden
    psycopg2.connect = forbidden
    sqlite3.connect = forbidden
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
        decision = classifier.classify_comedy_eligibility(
            source_id=snapshot["source_id"], policy=policy, evidence=evidence,
            performers=[classifier.PerformerObservation(name) for name in snapshot["performers"]],
            people=[classifier.CanonicalPerson(**person) for person in snapshot["people"]],
            denied=[classifier.DeniedName(**person) for person in snapshot["denied"]],
        ).to_dict()
        rows.append({"public_show_id": entry["public_show_id"], "policy_sha256": digest(snapshot["policy"]),
                     "decision": decision})
    imported = {}
    for name, module in sorted(sys.modules.items()):
        if name.startswith(("laughtrack.", "sql.")) and getattr(module, "__file__", None):
            path = Path(module.__file__).resolve()
            if not path.is_relative_to(runtime):
                raise ValueError("Replay imported code outside frozen revision: " + name)
            imported[str(path.relative_to(runtime))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"classifier_version": classifier.CLASSIFIER_VERSION, "imported_source_sha256": imported,
            "rows": rows, "io_contract": {"database_writes": 0, "network_calls": 0, "model_calls": 0}}


def replay(corpus, *, revisions=REVISIONS, diagnostic=False):
    inputs, unsupported = prepare_inputs(corpus, diagnostic=diagnostic)
    runs = {name: run_revision(revision, inputs) for name, revision in revisions.items()}
    if len({run["input_sha256"] for run in runs.values()}) != 1:
        raise ValueError("Revision inputs differ")
    return {"mode": "title_only_diagnostic" if diagnostic else "strict_ingestion_replay",
            "corpus_version": corpus["corpus_version"], "manifest_sha256": corpus["manifest_sha256"],
            "corpus_records_sha256": digest(corpus["records"]), "input_sha256": digest(inputs),
            "input_count": len(inputs), "unsupported": unsupported,
            "unsupported_reasons": dict(Counter(reason for row in unsupported for reason in row["reasons"])),
            "runs": runs}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compare frozen ingestion rule revisions offline.")
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.worker:
        print(json.dumps(worker(args.worker, json.load(sys.stdin)), sort_keys=True))
    else:
        parser.error("Report command is not yet configured")


if __name__ == "__main__":
    main()
