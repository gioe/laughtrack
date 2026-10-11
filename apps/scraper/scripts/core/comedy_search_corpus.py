"""Validate and load frozen public-search evidence without running ingestion rules."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

BASELINE = _root / "docs/audits/comedy-search-rules/baseline-v1"
VERSION = "comedy-search-2026-10-11-v1"
FORMATS = {"mixed_live", "mixed_open_mic", "meet_and_greet", "promotion", "closure", "screening",
           "mixed_screening", "watch_party", "mixer", "social_activity", "tour", "training", "activity",
           "live_performance", "unknown"}


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def checked_bytes(root, entry):
    relative = Path(entry["file"])
    path = (root / relative).resolve()
    if relative.is_absolute() or not path.is_relative_to(root.resolve()):
        raise ValueError("Artifact path escapes corpus")
    try:
        raw = path.read_bytes()
    except FileNotFoundError as exc:
        raise ValueError(f"Missing artifact: {relative}") from exc
    if sha256(raw) != entry["sha256"]:
        raise ValueError(f"Artifact digest mismatch: {relative}")
    return raw


def load_snapshot(root=BASELINE):
    """Validate original bytes and observable capture consistency; no live fetch."""
    root = Path(root)
    manifest = json.loads((root / "manifest.json").read_bytes())
    if manifest.get("schema_version") != 1 or manifest.get("corpus_version") != VERSION:
        raise ValueError("Unsupported corpus version")
    if manifest.get("baseline_decision") != "observed_publication":
        raise ValueError("Baseline must describe observed publication")
    if manifest.get("counts") != {"shows": 2886, "venue_title_groups": 2175, "clubs": 702}:
        raise ValueError("Frozen capture counts changed")
    query = {"fromDate": "2026-10-11", "toDate": "2026-10-17", "size": 500, "sort": "date_asc"}
    if manifest.get("query") != query:
        raise ValueError("Frozen capture query changed")
    pages = manifest.get("pages", [])
    if len(pages) != 6 or [p.get("page") for p in pages] != list(range(6)):
        raise ValueError("Missing, repeated or reordered capture page")
    shows = []
    for index, entry in enumerate(pages):
        if entry["file"] != f"raw/page-{index}.json" or entry.get("params") != {**query, "page": index}:
            raise ValueError("Page identity/query mismatch")
        saved_at = datetime.fromisoformat(entry["saved_at_utc"])
        if saved_at.tzinfo is None:
            raise ValueError("Capture timestamp must have timezone")
        page = json.loads(checked_bytes(root, entry))
        expected_size = 500 if index < 5 else 386
        if page.get("total") != 2886 or entry.get("reported_total") != 2886:
            raise ValueError("Drifting page total")
        data = page.get("data")
        if not isinstance(data, list) or len(data) != expected_size or entry.get("returned") != expected_size:
            raise ValueError("Incomplete page")
        shows.extend(data)
    ids = [s["id"] for s in shows]
    if any(type(sid) is not int for sid in ids) or len(set(ids)) != 2886:
        raise ValueError("Duplicate or invalid public show identity")
    if len({s["clubId"] for s in shows}) != 702 or len({(s["clubName"], s["name"]) for s in shows}) != 2175:
        raise ValueError("Capture grouping counts changed")
    order = [(datetime.fromisoformat(s["date"].replace("Z", "+00:00")), s["id"]) for s in shows]
    if order != sorted(order):
        raise ValueError("Capture ordering drift")
    if any(not isinstance(s.get("lineup"), list) for s in shows):
        raise ValueError("Invalid public lineup evidence")
    triage = manifest.get("triage_artifacts", [])
    if {p["file"] for p in triage} != {
        "triage/audit.json", "triage/build_report.py", "triage/report.txt",
        "triage/groups.json", "triage/shows.json", "triage/titles.txt",
    } or len(triage) != 6:
        raise ValueError("Incomplete original triage archive")
    for entry in triage:
        checked_bytes(root, entry)
    return manifest, shows


def load_corpus(root=BASELINE):
    """Join frozen publication, reference labels and separately captured identities."""
    root = Path(root)
    manifest, shows = load_snapshot(root)
    artifacts = manifest.get("review_artifacts", [])
    if {a["file"] for a in artifacts} != {"labels.json", "mappings.json"} or len(artifacts) != 2:
        raise ValueError("Reference review is not frozen")
    documents = {a["file"]: json.loads(checked_bytes(root, a)) for a in artifacts}
    labels, mappings = documents["labels.json"], documents["mappings.json"]
    if any(d.get("schema_version") != 1 for d in (labels, mappings)):
        raise ValueError("Unsupported review schema")
    by_id = {show["id"]: show for show in shows}
    locations = {show["id"]: f"raw/page-{index // 500}.json#/data/{index % 500}"
                 for index, show in enumerate(shows)}
    provenance = mappings.get("provenance", {})
    if provenance.get("readonly") is not True or provenance.get("transaction_read_only") != "on":
        raise ValueError("Identity evidence lacks read-only capture provenance")
    captured_at = datetime.fromisoformat(provenance["captured_at"])
    if captured_at.tzinfo is None:
        raise ValueError("Identity capture timestamp must have timezone")
    checked_bytes(root, {"file": provenance["query_file"], "sha256": provenance["query_sha256"]})
    parameters = json.loads(checked_bytes(root, {
        "file": provenance["parameter_file"], "sha256": provenance["parameter_sha256"],
    }))
    if not isinstance(parameters, list) or len(parameters) != len(by_id) or set(parameters) != by_id.keys():
        raise ValueError("Identity query parameters differ from original public IDs")
    raw_mapping = json.loads(checked_bytes(root, {
        "file": provenance["raw_result_file"], "sha256": provenance["raw_result_sha256"],
    }))
    raw_by_id = {r["show_id"]: r for r in raw_mapping}
    if len(raw_by_id) != len(raw_mapping) or raw_by_id.keys() != by_id.keys():
        raise ValueError("Identity capture does not cover original public IDs")
    reviewed = {}
    review = labels.get("review", {})
    for row in labels["records"]:
        sid = row["show_id"]
        if sid not in by_id or sid in reviewed:
            raise ValueError("Unknown or duplicated reviewed show")
        if row.get("genre") not in {"comedy", "non_comedy", "unknown"}:
            raise ValueError("Invalid reference genre")
        if row.get("format") not in FORMATS or row.get("public_availability") not in {"public", "non_public", "unknown"}:
            raise ValueError("Invalid reference format/public availability")
        if not row.get("rationale") or not (row.get("reviewer") or review.get("reviewer")):
            raise ValueError("Reference label lacks rationale/reviewer")
        if not (row.get("reviewed_at") or review.get("reviewed_at")):
            raise ValueError("Reference label lacks review time")
        if row.get("selection") not in {"flagged", "control"}:
            raise ValueError("Reference label lacks review selection")
        evidence = row.get("evidence", [])
        if row["genre"] != "unknown" and not evidence:
            raise ValueError("Known genre requires event evidence")
        for item in evidence:
            if item.get("field") not in {"name", "description"}:
                raise ValueError("Genre reference must use event title/description, not branding/tags/lineup")
            text = by_id[sid].get(item["field"]) or ""
            if (not item.get("excerpt") or item["excerpt"] not in text
                    or item.get("reference") != f"{locations[sid]}/{item['field']}"):
                raise ValueError("Reference excerpt not present in event evidence")
        reviewed[sid] = row
    triage = json.loads((root / "triage/audit.json").read_bytes())
    flagged_ids = {sid for flag in triage["flags"] for sid in flag["ids"]}
    if not flagged_ids <= reviewed.keys():
        raise ValueError("Flagged occurrences missing reference review")
    if any(reviewed[sid]["selection"] != "flagged" for sid in flagged_ids):
        raise ValueError("Flagged review selection mismatch")
    if not any(r["selection"] == "control" and r["genre"] == "comedy" for r in reviewed.values()):
        raise ValueError("Missing comedy controls")
    mapped = {}
    for row in mappings["records"]:
        sid = row["show_id"]
        if sid not in by_id or sid in mapped:
            raise ValueError("Unknown or duplicated mapped show")
        if {key: value for key, value in row.items() if key != "status"} != raw_by_id[sid]:
            raise ValueError("Mapping differs from captured identity evidence")
        if row.get("present_in_database") and row.get("club_id") != by_id[sid]["clubId"]:
            raise ValueError("Mapped venue changed since public capture; explicit review required")
        if row.get("status") not in {"resolved", "unresolved", "ambiguous"}:
            raise ValueError("Missing explicit mapping status")
        candidates = row.get("publication_candidates", [])
        pairs = {(c["source_id"], c["event_key"]) for c in candidates}
        if row["status"] == "resolved" and len(pairs) != 1:
            raise ValueError("Resolved source requires actual publication linkage")
        if row["status"] == "unresolved" and candidates:
            raise ValueError("Unresolved mapping has candidate linkage")
        if row["status"] == "ambiguous" and len(pairs) < 2:
            raise ValueError("Ambiguous mapping lacks conflicting linkage")
        mapped[sid] = row
    if mapped.keys() != by_id.keys():
        raise ValueError("Public occurrences missing identity evidence/status")
    records = []
    for show in shows:
        sid = show["id"]
        records.append({
            "public_show_id": sid,
            "observed_publication": True,
            "event_evidence": {"title": show["name"], "description": show.get("description"),
                               "public_lineup": show["lineup"]},
            "context": {"club_id": show["clubId"], "club_name": show["clubName"],
                        "tags": show.get("tags", []), "date": show["date"], "tickets": show["tickets"]},
            "source_evidence": mapped[sid],
            "reference_label": reviewed.get(sid, {"show_id": sid, "genre": "unknown", "selection": "unreviewed",
                                                   "rationale": "Not reviewed; publication does not prove comedy."}),
        })
    return {"corpus_version": VERSION, "manifest_sha256": sha256((root / "manifest.json").read_bytes()),
            "baseline_decision": "observed_publication", "records": records}


def report(corpus):
    records = corpus["records"]
    return {"corpus_version": corpus["corpus_version"], "manifest_sha256": corpus["manifest_sha256"],
            "baseline_decision": corpus["baseline_decision"], "published_occurrences": len(records),
            "reference_genres": dict(sorted(Counter(r["reference_label"]["genre"] for r in records).items())),
            "review_selections": dict(sorted(Counter(r["reference_label"]["selection"] for r in records).items())),
            "source_mapping_status": dict(sorted(Counter(r["source_evidence"]["status"] for r in records).items())),
            "database_writes": 0, "network_calls": 0, "model_calls": 0, "classifier_calls": 0}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate and summarize the frozen public show-search corpus offline.")
    parser.add_argument("--corpus", type=Path, default=BASELINE, help="Frozen corpus directory")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(report(load_corpus(args.corpus)), indent=2, sort_keys=True))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
