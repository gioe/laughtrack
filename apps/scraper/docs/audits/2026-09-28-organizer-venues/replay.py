#!/usr/bin/env python3
"""Validate the frozen organizer audit using local artifacts only (Python stdlib).

Run: python3 replay.py
The manifest must pin every input JSON file with SHA-256. This checks
snapshot integrity and evidence joins, not the continuing truth of public sites.
"""
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
CUTOFF = "2026-09-28T13:45:00Z"
ORGANIZERS = {327, 412, 447, 469, 573, 613, 8701}
CLASSES = {"correct", "confirmed_mismatch", "unknown", "non_performance"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def timestamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(result.tzinfo is not None, f"Timestamp lacks timezone: {value}")
    return result


def url(value):
    parts = urlsplit(value)
    require(parts.scheme in {"http", "https"} and parts.netloc, f"Invalid source URL: {value}")
    return parts


def index(items, key, label):
    result = {}
    for item in items:
        value = item[key]
        require(value not in result, f"Duplicate {label}: {value}")
        result[value] = item
    return result


def main():
    manifest = json.loads((ROOT / "manifest.json").read_text())
    require(manifest["cutoff_utc"] == CUTOFF, "Manifest cutoff changed")
    hashes = manifest["files"]
    if isinstance(hashes, list):
        hashes = {item["path"]: item["sha256"] for item in hashes}
    require(bool(hashes), "Empty file manifest")
    for relative, expected_hash in hashes.items():
        path = (ROOT / relative).resolve()
        require(path.is_relative_to(ROOT), f"Manifest path escapes audit root: {relative}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        require(actual == expected_hash, f"SHA-256 mismatch: {relative}")

    def read(relative):
        require(relative in hashes, f"Input not pinned by manifest: {relative}")
        return json.loads((ROOT / relative).read_text())

    assigned = read("assigned-shows.json")
    organizers = index(read("organizers.json"), "id", "organizer ID")
    require(set(organizers) == ORGANIZERS, "Expected exactly seven scoped organizers")
    direct = index(assigned, "id", "assigned show ID")
    require(len(direct) == 95, "Expected 95 directly assigned shows")
    require(all(s["club_id"] in ORGANIZERS for s in assigned), "Unexpected base club")
    cutoff = timestamp(CUTOFF)
    require(all(timestamp(s["date"]) > cutoff for s in assigned), "Non-upcoming snapshot row")
    require(not any(s["club_id"] in {327, 8701} for s in assigned), "Shoppe/Pagliacci direct counts changed")

    ac_doc = read("ac-pag/per-show.json")
    yard_doc = read("yardbird-alameda/per-show.json")
    lets_doc = read("lets-shoppe/per-show.json")
    big = read("big-pine/shows.json")
    for document in (ac_doc, yard_doc, lets_doc):
        require(document.get("cutoff", document.get("cutoff_utc")) == CUTOFF, "Classification cutoff differs")
    ac, yard, lets = ac_doc["shows"], yard_doc["shows"], lets_doc["shows"]
    classified = index(ac + yard + lets + big, "id", "classified show ID")
    require(set(direct) <= set(classified), f"Missing classifications: {sorted(set(direct) - set(classified))}")
    for show_id, snapshot in direct.items():
        entry = classified[show_id]
        for field in ("club_id", "show_page_url", "name"):
            require(entry[field] == snapshot[field], f"Snapshot {field} mismatch for show {show_id}")
        require(timestamp(entry["date"]) == timestamp(snapshot["date"]), f"Snapshot date mismatch: {show_id}")
    extras = [s for i, s in classified.items() if i not in direct]
    for entry in classified.values():
        require(entry["classification"] in CLASSES, f"Invalid classification: {entry['id']}")
        require(timestamp(entry["date"]) > cutoff, f"Non-upcoming classified row: {entry['id']}")
        url(entry["show_page_url"])
    require(all(s["club_id"] not in ORGANIZERS for s in extras), "Unaccounted direct row presented as extra")

    # Wix event UUID, slug, UTC start and full location must join one-to-one.
    wix = read("ac-pag/ac-wix-source.json")
    wix_by_id = index(wix["events"], "id", "Wix UUID")
    require(len(ac) == len(wix_by_id) == wix["pagination"]["total"] == 44, "Wix coverage changed")
    require(wix["pagination"]["hasMore"] is False, "Wix source is paginated/incomplete")
    require({s["source_event_id"] for s in ac} == set(wix_by_id), "Wix UUID coverage mismatch")
    url(wix["url"])
    timestamp(wix["retrieved_at"])
    for entry in ac:
        event = wix_by_id[entry["source_event_id"]]
        require(entry["source_url"] == wix["url"], "Wix evidence URL mismatch")
        require(url(entry["show_page_url"]).path.rsplit("/", 1)[-1] == event["slug"], "Wix slug mismatch")
        require(timestamp(entry["date"]) == timestamp(event["scheduling"]["config"]["startDate"]), "Wix start mismatch")
        require(timestamp(entry["source_event_date"]) == timestamp(entry["date"]), "Wix recorded source date mismatch")
        require(entry["source_location"] == event["location"], "Wix location changed")
        expected = "correct" if event["location"]["address"] == organizers[412]["address"] else "confirmed_mismatch"
        require(entry["classification"] == expected, "Wix classification contradicts address")
    require(Counter(s["classification"] for s in ac) == {"correct": 40, "confirmed_mismatch": 4}, "Wix result totals changed")

    # SeatEngine descriptions override organizer-wide generic JSON-LD locations.
    public_yard = index(read("yardbird-alameda/public-source-projections.json"), "source_url", "SeatEngine evidence URL")
    for entry in yard:
        evidence = public_yard[entry["evidence_url"]]
        url(evidence["source_url"])
        timestamp(evidence["retrieved_at"])
        event = evidence["event"]
        require(timestamp(entry["date"]) == timestamp(event["startDate"]), "SeatEngine evidence date mismatch")
        require(url(entry["show_page_url"]).path.rsplit("/", 1)[-1] == entry["platform_show_id"], "SeatEngine stored show ID mismatch")
        require(url(evidence["source_url"]).path.rsplit("/", 1)[-1] == entry["platform_show_id"], "SeatEngine evidence show ID mismatch")
        require(entry["evidence_quote"] == evidence["venue_excerpt"], "SeatEngine venue quote mismatch")
        require(bool(entry["reason"]), "SeatEngine classification needs rationale")

    public_lets = read("lets-shoppe/public-source-projection.json")
    lets_events = index(public_lets["lets_comedy"]["events"], "source_show_id", "Let's Comedy event ID")
    for entry in lets:
        event = lets_events[entry["source_show_id"]]
        evidence = entry["evidence"]
        require(evidence["url"] == event["url"], "Let's Comedy evidence URL mismatch")
        require(url(entry["show_page_url"]).path.rsplit("/", 1)[-1] == entry["source_show_id"], "Let's Comedy stored show ID mismatch")
        require(timestamp(entry["date"]) == timestamp(event["startDate"]), "Let's Comedy evidence date mismatch")
        require(evidence["location_description_excerpts"] == event["location_description_excerpts"], "Let's Comedy quote mismatch")
        timestamp(evidence["retrieved_at"])

    # Big Pine is non-performance inventory, not inferred physical misrouting.
    require(len(big) == 19, "Expected 19 Big Pine rows")
    for entry in big:
        require(entry["classification"] == "non_performance", "Big Pine classification changed")
        require(entry["club_id"] == 573, "Big Pine club mismatch")
        require(timestamp(entry["date"]) == timestamp(entry["source_start_date"]), "Big Pine source date mismatch")
        require(entry["source_url"] == entry["show_page_url"], "Big Pine source URL mismatch")
        require(bool(entry["evidence_quote"]) and bool(entry["subtype"]), "Big Pine evidence missing")
        timestamp(entry["retrieved_at"])

    pag = read("ac-pag/pagliacci-source.json")
    require(pag["cutoff"] == CUTOFF, "Pagliacci cutoff changed")
    fields = pag["public_profile_fields"]
    require(fields == {"upcomingEvents": [], "upcomingEventsTotal": 0, "hasMoreUpcoming": False, "upcomingEventsFailed": False}, "Pagliacci public feed not verified empty")
    require(pag["upcoming_database_shows"] == [], "Pagliacci database coverage changed")
    require(all(timestamp(e["startDate"]) < cutoff for e in pag["collection_events"]), "Historical Pagliacci card is upcoming")
    url(pag["source_url"])
    timestamp(pag["retrieved_at"])

    shoppe = public_lets["comedy_shoppe"]
    shoppe_events = index(shoppe["events"], "id", "Shoppe event ID")
    venues = index(shoppe["venues"], "id", "Shoppe venue ID")
    require(len(shoppe_events) == 24, "Expected 24 current Shoppe calendar entries")
    for event in shoppe_events.values():
        local = datetime.fromisoformat(event["datetime"])
        # These seven venues are in NJ, PA or SC: all use America/New_York.
        venue = venues[event["venue_id"]]
        require(venue["state"] in {"NJ", "PA", "SC"}, "Shoppe venue timezone needs review")
        local = local.replace(tzinfo=ZoneInfo("America/New_York")) if local.tzinfo is None else local
        require(local > cutoff, "Shoppe calendar row is not upcoming")
        require(event["venue_address"] == venue, "Shoppe event/venue join mismatch")
        require(event["venue"] == venue["name"], "Shoppe venue name mismatch")
        require(event["database_matching_show_ids"] == [], "Shoppe current event now has database row")
        ticket = url(event["ticket_link"])
        if ticket.hostname == "event.tixologi.com":
            require(ticket.path.split("/")[-2] == event["tixologi_event_id"], "Shoppe ticket ID mismatch")
        else:
            require(event["tixologi_event_id"] is None and ticket.hostname == "ci.ovationtix.com", "Unrecognized Shoppe ticket provider")
    url(shoppe["source_url"])
    timestamp(shoppe["retrieved_at"])

    counts = dict(Counter(classified[i]["classification"] for i in direct))
    extra_counts = dict(Counter(s["classification"] for s in extras))
    expected = manifest["expected"]
    require(expected["direct_rows"] == len(direct), "Manifest direct total mismatch")
    require(expected["direct_classifications"] == counts, "Manifest direct classification totals mismatch")
    require(expected["additional_rows"] == len(extras), "Manifest additional total mismatch")
    require(expected["additional_classifications"] == extra_counts, "Manifest additional classification totals mismatch")
    print(json.dumps({"status": "passed", "cutoff_utc": CUTOFF, "direct_rows": len(direct), "direct_classifications": counts, "additional_rows": len(extras), "additional_classifications": extra_counts, "shoppe_current_calendar_not_ingested": len(shoppe_events), "verified_manifest_files": len(hashes)}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (KeyError, ValueError, TypeError, OSError) as error:
        raise SystemExit(f"Audit replay failed: {error}") from error
