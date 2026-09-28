"""Replay TASK-4063's saved iO feed comparison without network or database access.

From apps/scraper:
    PYTHONPATH=src:. .venv/bin/python3 docs/audits/2026-09-28-io-stale-reconciliation/replay.py

The separate production safety-cap regression is:
    PYTHONPATH=src:. .venv/bin/python3 -m pytest -q \
        tests/utilities/domain/scraper/test_result_processor.py::TestStaleFutureShowReconciliation::test_cap_exceeded_skips_delete

This evidence replay never performs cleanup or changes the reconciliation cap.
"""

import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from laughtrack.scrapers.implementations.api.crowdwork.utils import (
    RAILS_TO_IANA,
    extract_performances,
)
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


SNAPSHOT_CUTOFF = datetime.fromisoformat("2026-09-28T00:44:50.541695+00:00")
EVIDENCE_DIR = Path(__file__).resolve().parent


def read_rows(filename):
    return [json.loads(line) for line in (EVIDENCE_DIR / filename).read_text().splitlines() if line.strip()]


def utc(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
    # The scraper's datetime helper can return UTC-naive domain timestamps.
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def main():
    manifest = json.loads((EVIDENCE_DIR / "manifest.json").read_text())
    assert utc(manifest["snapshot_cutoff_utc"]) == SNAPSHOT_CUTOFF
    for filename, expected_hash in manifest["files"].items():
        assert hashlib.sha256((EVIDENCE_DIR / filename).read_bytes()).hexdigest() == expected_hash, filename
    feed = read_rows("feed.jsonl")
    stored = read_rows("stored.jsonl")
    candidates = read_rows("candidates.jsonl")
    extracted = []
    for event in feed:
        raw_dates = event.get("dates") or ([event["next_date"]] if event.get("next_date") else [])
        expected_dates = [str(value) for value in raw_dates if value]
        performances = extract_performances(event, rails_to_iana=RAILS_TO_IANA)
        assert [performance.date_str for performance in performances] == expected_dates, event["id"]
        for performance in performances:
            timestamp = utc(ShowFactoryUtils.parse_datetime_with_timezone_fallback(
                performance.date_str, performance.timezone
            ))
            extracted.append((performance.url, timestamp))

    assert len(extracted) == 1519, len(extracted)
    future = [(url, timestamp) for url, timestamp in extracted if timestamp > SNAPSHOT_CUTOFF]
    assert len(future) == 1255, len(future)
    identities = set(future)
    slots = defaultdict(set)
    for url, timestamp in future:
        slots[timestamp].add(url)
    collisions = {timestamp: urls for timestamp, urls in slots.items() if len(urls) > 1}
    assert len(collisions) == 282, len(collisions)

    assert len(stored) == 946, len(stored)
    assert len({row["id"] for row in stored}) == len(stored)
    assert all(row["room"] == "" for row in stored)
    assert all(utc(row["date"]) > SNAPSHOT_CUTOFF for row in stored)
    matched = [row for row in stored if (row["show_page_url"], utc(row["date"])) in identities]
    unmatched = [row for row in stored if (row["show_page_url"], utc(row["date"])) not in identities]
    assert len(matched) == 904, len(matched)
    assert len(unmatched) == 42, len(unmatched)
    assert all(utc(row["date"]) not in slots for row in unmatched)
    assert all(row["last_scraped_by"] == "crowdwork" for row in unmatched)
    assert len(candidates) == 42
    assert len({row["id"] for row in candidates}) == len(candidates)
    assert {row["id"] for row in candidates} == {row["id"] for row in unmatched}
    expected = {row["id"]: (row["show_page_url"], utc(row["date"])) for row in unmatched}
    pages = {row["url"]: row for row in read_rows("pages.jsonl")}
    assert dict(Counter(row["classification"] for row in candidates)) == manifest["counts"]
    replacement_count = 0
    replacements_stored = 0
    for row in candidates:
        assert expected[row["id"]] == (row["show_page_url"], utc(row["date"]))
        assert row["classification"] and row["evidence"], row["id"]
        assert row["evidence_page_url"] in pages, row["id"]
        if row.get("replacement_utc"):
            replacement_count += 1
            replacement_time = utc(row["replacement_utc"])
            assert (row["show_page_url"], replacement_time) in identities, row["id"]
            matching_ids = sorted(stored_row["id"] for stored_row in stored
                                  if stored_row["show_page_url"] == row["show_page_url"]
                                  and utc(stored_row["date"]) == replacement_time)
            assert matching_ids == sorted(row["replacement_stored_ids"]), row["id"]
            replacements_stored += bool(matching_ids)
            occupants = [{key: stored_row[key] for key in ("id", "name", "show_page_url")}
                         for stored_row in stored if utc(stored_row["date"]) == replacement_time]
            assert sorted(occupants, key=lambda item: item["id"]) == sorted(
                row["replacement_slot_occupants"], key=lambda item: item["id"]
            ), row["id"]
    assert replacement_count == 11
    assert replacements_stored == 10
    assert len(unmatched) > 10  # Exceeds the unchanged default reconciliation safety cap.

    print(json.dumps({
        "snapshot_cutoff": SNAPSHOT_CUTOFF.isoformat(),
        "raw_performances_preserved": len(extracted),
        "future_performances": len(future),
        "future_collision_slots": len(collisions),
        "stored_future_rows": len(stored),
        "exact_url_timestamp_matches": len(matched),
        "candidate_rows_absent_from_all_feed_slots": len(unmatched),
        "candidate_ids_verified": True,
        "evidence_hashes_verified": len(manifest["files"]),
        "replacements_in_feed": replacement_count,
        "replacements_in_stored_rows": replacements_stored,
        "default_safety_cap": 10,
        "cleanup_performed": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
