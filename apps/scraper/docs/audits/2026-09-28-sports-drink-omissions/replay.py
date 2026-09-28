"""Replay TASK-4064's saved Sports Drink evidence without network or DB access.

From apps/scraper:
    PYTHONPATH=src:. .venv/bin/python3 docs/audits/2026-09-28-sports-drink-omissions/replay.py

Reconciliation behavior is separately tested by:
    PYTHONPATH=src:. .venv/bin/python3 -m pytest -q \
        tests/utilities/domain/scraper/test_result_processor.py \
        tests/core/entities/show/test_handler_stale_reconciliation.py

This checks a fixed historical snapshot; it never deletes data or changes caps.
"""

import ast
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from laughtrack.core.entities.event.sports_drink import _parse_opendate_datetime
from laughtrack.scrapers.implementations.venues.sports_drink.extractor import SportsDrinkExtractor

EVIDENCE_DIR = Path(__file__).resolve().parent
HISTORICAL_CUTOFF = datetime.fromisoformat("2026-09-24T15:49:37+00:00")
SNAPSHOT_CUTOFF = datetime.fromisoformat("2026-09-28T12:00:00+00:00")


def utc(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
    assert parsed is not None and parsed.tzinfo is not None, value
    return parsed.astimezone(timezone.utc)


def rows(filename):
    return [json.loads(line) for line in (EVIDENCE_DIR / filename).read_text().splitlines() if line.strip()]


def identity(row):
    return row["show_page_url"], utc(row["date"])


def main():
    manifest = json.loads((EVIDENCE_DIR / "manifest.json").read_text())
    assert utc(manifest["snapshot_cutoff_utc"]) == SNAPSHOT_CUTOFF
    assert utc(manifest["historical_cutoff_utc"]) == HISTORICAL_CUTOFF
    required_files = {"stored.jsonl", "listing.jsonl", "candidates.jsonl", "listing-cards.html", "pagination.json"}
    assert required_files <= manifest["files"].keys()
    for filename, expected_hash in manifest["files"].items():
        assert hashlib.sha256((EVIDENCE_DIR / filename).read_bytes()).hexdigest() == expected_hash, filename

    stored = rows("stored.jsonl")
    listing = rows("listing.jsonl")
    candidates = rows("candidates.jsonl")
    assert len(stored) == len({row["id"] for row in stored}) == 220
    assert all(utc(row["date"]) > HISTORICAL_CUTOFF for row in stored)
    assert all(row["last_scraped_by"] == "sports_drink" and row["room"] == "" for row in stored)
    legacy = [row for row in stored if urlsplit(row["show_page_url"]).hostname == "app.opendate.io"]
    refreshed = [row for row in stored if urlsplit(row["show_page_url"]).hostname == "event.tixologi.com"]
    assert len(legacy) == 85 and len(refreshed) == 135
    assert all(utc(row["last_scraped_date"]) < HISTORICAL_CUTOFF for row in legacy)
    assert all(utc(row["last_scraped_date"]) > HISTORICAL_CUTOFF for row in refreshed)
    assert sum(utc(row["date"]) > SNAPSHOT_CUTOFF for row in legacy) == 84

    extracted = SportsDrinkExtractor.extract_events((EVIDENCE_DIR / "listing-cards.html").read_text())
    assert len(extracted) == len(listing) == 130
    actual = [(event.title, event.date_str, event.time_str, event.event_url,
               utc(_parse_opendate_datetime(event.date_str, event.time_str, "America/Chicago")))
              for event in extracted]
    expected = [(row["title"], row["date_str"], row["time_str"], row["event_url"], utc(row["utc"]))
                for row in listing]
    assert actual == expected
    listing_identities = {(row["event_url"], utc(row["utc"])) for row in listing}
    assert len(listing_identities) == 130
    matched = [row for row in refreshed if identity(row) in listing_identities]
    past = [row for row in refreshed if identity(row) not in listing_identities]
    assert len(matched) == 129 and len(past) == 6
    assert all(utc(row["date"]) > SNAPSHOT_CUTOFF for row in matched)
    assert all(utc(row["date"]) < SNAPSHOT_CUTOFF for row in past)
    assert not any(identity(row) in listing_identities for row in legacy)
    unmatched_listing = listing_identities - {identity(row) for row in stored}
    assert len(unmatched_listing) == 1
    placeholder = next(row for row in listing if (row["event_url"], utc(row["utc"])) in unmatched_listing)
    assert placeholder["title"] == "Thank You For Your Purchase!!!"
    assert utc(placeholder["utc"]).year == 2099

    assert len(candidates) == len({row["id"] for row in candidates}) == 85
    assert {row["id"] for row in candidates} == {row["id"] for row in legacy}
    stored_by_id = {row["id"]: row for row in stored}
    for row in candidates:
        assert all(row[key] == value for key, value in stored_by_id[row["id"]].items()), row["id"]
        assert row["stored_id"] == row["id"] and row["requested_url"] == row["show_page_url"]
        assert row["classification"] and row["evidence"], row["id"]
    assert dict(Counter(row["classification"] for row in candidates)) == manifest["classification_counts"]
    assert manifest["classification_counts"] == {
        "canceled": 56, "redirected_rescheduled": 28, "unresolved_404": 1,
    }
    canceled = [row for row in candidates if row["explicitly_canceled"]]
    assert len(canceled) == 56
    for row in canceled:
        assert row["fetch_nonempty"] and row["html_sha256"], row["id"]
        assert "THIS EVENT HAS BEEN CANCELED" in row["primary_ticket_ctas"], row["id"]
        assert any(event.get("eventStatus") == "https://schema.org/EventScheduled"
                   for event in row["jsonld_events"]), row["id"]

    redirected = [row for row in candidates if row["classification"] == "redirected_rescheduled"]
    assert len(redirected) == 28
    for row in redirected:
        redirect = row["redirect"]
        replacement = row["replacement"]
        assert redirect["http_status"] == 200, row["id"]
        assert redirect["final_url"] == replacement["event_url"], row["id"]
        replacement_identity = (replacement["event_url"], utc(replacement["utc"]))
        assert replacement_identity in listing_identities, row["id"]
        assert utc(row["date"]) != replacement_identity[1], row["id"]
        stored_matches = sorted(item["id"] for item in stored if identity(item) == replacement_identity)
        assert stored_matches and stored_matches == sorted(row["replacement_stored_ids"]), row["id"]
    unresolved = [row for row in candidates if row["classification"] == "unresolved_404"]
    assert len(unresolved) == 1 and unresolved[0]["id"] == 506917
    assert unresolved[0]["redirect"]["http_status"] == 404

    pagination = json.loads((EVIDENCE_DIR / "pagination.json").read_text())
    variants = {}
    for variant in pagination:
        query = parse_qs(urlsplit(variant["url"]).query)
        key = (int(query["per_page"][0]), int(query.get("page", ["1"])[0]))
        assert key not in variants, key
        variant_identities = [(url, utc(timestamp)) for url, timestamp in variant["identities"]]
        assert len(variant_identities) == variant["extracted_count"]
        variants[key] = variant_identities
    assert set(variants[(500, 1)]) == set(variants[(1000, 1)]) == listing_identities
    assert len(variants[(500, 1)]) == len(variants[(1000, 1)]) == 130
    assert variants[(500, 2)] == []
    assert len(variants[(20, 1)]) == 20
    assert variants[(20, 1)] == [(row["event_url"], utc(row["utc"])) for row in listing[:20]]

    # Read the default constant without constructing persistence services.
    processor_path = EVIDENCE_DIR.parents[2] / "src/laughtrack/utilities/domain/scraper/result.py"
    tree = ast.parse(processor_path.read_text())
    caps = [ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "_DEFAULT_RECONCILE_DELETE_CAP"
                    for target in node.targets)]
    assert caps == [10]
    assert len(legacy) > caps[0]
    print(json.dumps({"stored": 220, "legacy_candidates": 85, "still_future_legacy": 84,
                      "refreshed": 135, "current_matches": 129, "past_refreshed": 6,
                      "listing_cards": 130, "future_placeholder": 1,
                      "explicit_cancellations_with_conflicting_jsonld": 56,
                      "classification_counts": manifest["classification_counts"],
                      "default_reconciliation_cap": caps[0]}, indent=2))


if __name__ == "__main__":
    main()
