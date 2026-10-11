"""Frozen search evidence integrity and offline review boundaries."""

import builtins
import copy
import json
import shutil

import pytest

from scripts.core import comedy_search_corpus as corpus


@pytest.fixture
def archived(tmp_path):
    root = tmp_path / "baseline"
    shutil.copytree(corpus.BASELINE, root)
    return root


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def replace_artifact(root, filename, value, section):
    """Update declared digest so tests also exercise semantic consistency checks."""
    write_json(root / filename, value)
    manifest = json.loads((root / "manifest.json").read_text())
    next(e for e in manifest[section] if e["file"] == filename)["sha256"] = corpus.sha256((root / filename).read_bytes())
    write_json(root / "manifest.json", manifest)


def test_snapshot_integrity():
    manifest, shows = corpus.load_snapshot()
    assert len(shows) == len({s["id"] for s in shows}) == 2886
    assert len({s["clubId"] for s in shows}) == 702
    assert len({(s["clubName"], s["name"]) for s in shows}) == 2175
    assert [p["returned"] for p in manifest["pages"]] == [500] * 5 + [386]
    original_audit = json.loads((corpus.BASELINE / "triage/audit.json").read_text())
    assert [p["sha256"] for p in manifest["pages"]] == [p["sha256"] for p in original_audit["scope"]["pagination"]]
    assert [p["saved_at_utc"] for p in manifest["pages"]] == [p["saved_at_utc"] for p in original_audit["scope"]["pagination"]]


@pytest.mark.parametrize("mutation", ["missing", "tampered", "swapped", "total", "duplicate", "short", "order"])
def test_incomplete_or_drifting_snapshot_rejected(archived, mutation):
    path = archived / "raw/page-0.json"
    if mutation == "missing":
        path.unlink()
    elif mutation == "tampered":
        path.write_bytes(path.read_bytes() + b" ")
    elif mutation == "swapped":
        manifest = json.loads((archived / "manifest.json").read_text())
        manifest["pages"][0], manifest["pages"][1] = manifest["pages"][1], manifest["pages"][0]
        write_json(archived / "manifest.json", manifest)
    else:
        page = json.loads(path.read_text())
        if mutation == "total":
            page["total"] += 1
        elif mutation == "duplicate":
            page["data"][0] = copy.deepcopy(page["data"][1])
        elif mutation == "short":
            page["data"].pop()
        elif mutation == "order":
            page["data"][0], page["data"][1] = page["data"][1], page["data"][0]
        replace_artifact(archived, "raw/page-0.json", page, "pages")
    with pytest.raises(ValueError):
        corpus.load_snapshot(archived)


def test_evidence_contract(monkeypatch):
    real_import = builtins.__import__

    def local_import(name, *args, **kwargs):
        if name.startswith(("laughtrack", "openai", "psycopg", "requests", "httpx", "urllib", "socket")):
            raise AssertionError(f"Offline loader tried importing {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", local_import)
    first = corpus.load_corpus()
    second = corpus.load_corpus()
    assert first == second
    assert corpus.report(first) == corpus.report(second)
    original = {s["id"]: s for s in corpus.load_snapshot()[1]}
    for row in first["records"]:
        raw = original[row["public_show_id"]]
        assert row["observed_publication"] is True
        assert row["event_evidence"] == {
            "title": raw["name"], "description": raw["description"], "public_lineup": raw["lineup"],
        }
        assert "club_name" not in row["event_evidence"] and "tags" not in row["event_evidence"]
        assert "blocked" not in row["event_evidence"] and "parents" not in row["event_evidence"]
        if row["reference_label"]["selection"] == "unreviewed":
            assert row["reference_label"]["genre"] == "unknown"
        if row["source_evidence"]["status"] == "unresolved":
            assert row["source_evidence"]["publication_candidates"] == []
    summary = corpus.report(first)
    assert summary["published_occurrences"] == 2886
    assert summary["review_selections"]["flagged"] == 212
    assert summary["review_selections"]["control"] > 5
    assert all(summary[key] == 0 for key in ("database_writes", "network_calls", "model_calls", "classifier_calls"))


@pytest.mark.parametrize("mutation", ["unsupported", "branding", "missing", "reviewer", "no_evidence", "wrong_event", "format"])
def test_reference_labels_require_explicit_event_review(archived, mutation):
    labels = json.loads((archived / "labels.json").read_text())
    target = next(r for r in labels["records"] if r["genre"] == "comedy")
    if mutation == "unsupported":
        target["evidence"][0]["excerpt"] = "This text does not occur in the frozen event."
    elif mutation == "branding":
        target["evidence"][0]["field"] = "clubName"
    elif mutation == "missing":
        labels["records"] = [r for r in labels["records"] if r["selection"] != "flagged"]
    elif mutation == "reviewer":
        labels.get("review", {}).pop("reviewer", None)
        for row in labels["records"]:
            row.pop("reviewer", None)
    elif mutation == "no_evidence":
        target["evidence"] = []
    elif mutation == "wrong_event":
        target["evidence"][0]["reference"] = "raw/page-5.json#/data/999/name"
    elif mutation == "format":
        target["format"] = "comedy"
    replace_artifact(archived, "labels.json", labels, "review_artifacts")
    with pytest.raises(ValueError):
        corpus.load_corpus(archived)


def test_public_ids_cannot_be_invented_as_native_identity(archived):
    mappings = json.loads((archived / "mappings.json").read_text())
    row = mappings["records"][0]
    row["source_performance_id"] = str(row["show_id"])
    row["publication_candidates"] = [{"source_id": 1, "event_key": str(row["show_id"])}]
    row["status"] = "resolved"
    replace_artifact(archived, "mappings.json", mappings, "review_artifacts")
    with pytest.raises(ValueError, match="captured identity"):
        corpus.load_corpus(archived)


def test_unfrozen_review_rejected(archived):
    manifest = json.loads((archived / "manifest.json").read_text())
    manifest["review_artifacts"] = []
    write_json(archived / "manifest.json", manifest)
    with pytest.raises(ValueError, match="not frozen"):
        corpus.load_corpus(archived)


def test_mapping_parameters_cannot_omit_public_occurrences(archived):
    path = archived / "mapping-query-ids.json"
    parameters = json.loads(path.read_text())
    write_json(path, parameters[:-1])
    mappings = json.loads((archived / "mappings.json").read_text())
    mappings["provenance"]["parameter_sha256"] = corpus.sha256(path.read_bytes())
    replace_artifact(archived, "mappings.json", mappings, "review_artifacts")
    with pytest.raises(ValueError, match="query parameters"):
        corpus.load_corpus(archived)
