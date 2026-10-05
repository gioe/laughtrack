"""Offline verification of the exact freshly reviewed Sports Drink cohort."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from laughtrack.scrapers.implementations.venues.sports_drink.extractor import SportsDrinkExtractor
from laughtrack.core.entities.event.sports_drink import _parse_opendate_datetime

ROOT = Path(__file__).resolve().parent


def utc(value):
    result = datetime.fromisoformat(value) if isinstance(value, str) else value
    assert result.tzinfo is not None
    return result.astimezone(timezone.utc)


def verify():
    manifest = json.loads((ROOT / "manifest.json").read_text())
    for name, digest in manifest["files"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    old = {
        r["id"]: r
        for r in (
            json.loads(s)
            for s in (ROOT.parent / "2026-09-28-sports-drink-omissions/candidates.jsonl").read_text().splitlines()
        )
    }
    decisions = json.loads((ROOT / "decisions.json").read_text())
    stored = {r["id"]: r for r in json.loads((ROOT / "before.json").read_text())["shows"]}
    pages = {r["url"]: r for r in json.loads((ROOT / "pages.json").read_text())}
    events = SportsDrinkExtractor.extract_events((ROOT / "listing-cards.html").read_text())
    listing = {(e.event_url, utc(_parse_opendate_datetime(e.date_str, e.time_str, "America/Chicago"))) for e in events}
    assert len(decisions) == len(old) == 85 and {r["id"] for r in decisions} == set(old)
    chosen = [r for r in decisions if r["decision"] == "retire"]
    assert sorted(r["id"] for r in chosen) == manifest["retire_ids"]
    assert len(chosen) == manifest["expected_count"] == 77
    assert sorted(r["id"] for r in decisions if r["decision"] == "hold") == sorted(manifest["hold_ids"])
    assert 506917 in manifest["hold_ids"]
    assert not set(manifest["retire_ids"]) & set(manifest["replacement_ids"])
    for item in decisions:
        ident = item["id"]
        prior = old[ident]
        row = stored[ident]
        page = pages[prior["show_page_url"]]
        if item["decision"] == "hold":
            assert ident == 506917 or utc(row["date"]) <= utc(manifest["cutoff"])
            continue
        assert row["club_id"] == 653 and row["last_scraped_by"] == "sports_drink"
        assert utc(row["date"]) > utc(manifest["cutoff"])
        for key in ("name", "show_page_url", "room", "last_scraped_by"):
            assert row[key] == prior[key], (ident, key)
        for key in ("date", "last_scraped_date"):
            assert utc(row[key]) == utc(prior[key]), (ident, key)
        assert (row["show_page_url"], utc(row["date"])) not in listing
        if item["classification"] == "canceled":
            assert page["response"] == [row["show_page_url"], 200]
            assert page["primary_ticket_ctas"] == ["THIS EVENT HAS BEEN CANCELED"]
            assert 'data-primary-tickets-cta="true"' in page["primary_cta_html"][0]
        else:
            assert item["classification"] == "redirected_rescheduled"
            rep = prior["replacement"]
            assert page["response"] == [rep["event_url"], 200]
            assert (rep["event_url"], utc(rep["utc"])) in listing
            assert item["replacement_ids"] == prior["replacement_stored_ids"]
            for replacement_id in item["replacement_ids"]:
                replacement = stored[replacement_id]
                assert replacement["club_id"] == 653 and replacement["room"] == ""
                assert replacement["show_page_url"] == rep["event_url"] and utc(replacement["date"]) == utc(rep["utc"])
    return chosen


if __name__ == "__main__":
    print(json.dumps({"verified_retire": len(verify()), "held": 8, "cap_unchanged": 10}))
