"""Retained public headers corroborate narrowly repaired obsolete Alberta offsets."""

import json
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup
import pytest

from laughtrack.scrapers.implementations.next_stop_comedy.extractor import extract_json_ld_events


FIXTURES = Path(__file__).parent / "fixtures"
SLUGS = ["big-beaver-brewing-2027-03-13", "leduc-brewing-company-2027-03-12"]


def evidence(slug=SLUGS[0], *, obsolete=True):
    soup = BeautifulSoup((FIXTURES / f"{slug}.html").read_text(), "html.parser")
    script = soup.find("script", type="application/ld+json")
    node = json.loads(script.string)
    if obsolete:
        node["startDate"] = node["startDate"].replace("-06:00", "-07:00")
    return soup, script, node


def extract(soup, script, node):
    script.string = json.dumps(node)
    return extract_json_ld_events(str(soup))


@pytest.mark.parametrize("slug", SLUGS)
def test_timezone_verified_march_wall_time_repairs_obsolete_offset(slug):
    soup, script, node = evidence(slug)
    event = extract(soup, script, node)[0]
    expected = datetime.fromisoformat(node["startDate"].replace("-07:00", "-06:00"))
    assert event.start_date == expected
    assert event.start_date.hour == 19
    assert event.start_date.date() == expected.date()
    assert event.start_date.astimezone(timezone.utc).hour == 1
    assert event.venue_timezone == "America/Edmonton"


@pytest.mark.parametrize("slug", SLUGS)
def test_timezone_current_valid_explicit_offset_is_unchanged(slug):
    soup, script, node = evidence(slug, obsolete=False)
    event = extract(soup, script, node)[0]
    assert event.start_date.isoformat() == node["startDate"]


@pytest.mark.parametrize(
    "day,hour,corrected",
    [("2026-11-21", 19, True), ("2026-12-31", 20, True),
     ("2027-02-13", 20, True), ("2026-10-24", 19, False),
     ("2026-01-10", 19, False)],
)
def test_timezone_wall_clock_dates_and_other_start_hours(day, hour, corrected):
    soup, script, node = evidence()
    wall = datetime.fromisoformat(f"{day}T{hour}:00:00")
    node["startDate"] = wall.isoformat() + "-07:00"
    header = soup.h1.parent.parent
    header.select_one("div.text-foreground").string = wall.strftime("%A, %B %d, %Y")
    header.select_one("div.text-muted-foreground").string = f"Seating Begins 6:30 PM · Show {hour - 12}:00 p.m."
    actual = extract(soup, script, node)[0].start_date
    assert actual.isoformat() == wall.isoformat() + ("-06:00" if corrected else "-07:00")


@pytest.mark.parametrize(
    "change",
    ["header_time", "header_date", "weekday", "header_title", "missing_header",
     "seating_only", "duplicate_header", "duplicate_date", "missing_props", "slug",
     "event_id", "event_date", "zone", "conflicting_zone", "region", "country", "utc"],
)
def test_timezone_missing_or_conflicting_evidence_retains_explicit_instant(change):
    soup, script, node = evidence()
    header = soup.h1.parent.parent
    date = header.select_one("div.text-foreground")
    clock = header.select_one("div.text-muted-foreground")
    flight_script = soup.find_all("script")[-1]
    raw = json.loads(flight_script.string.removeprefix("self.__next_f.push(").removesuffix(")"))[1]
    props = json.loads(raw.split(":", 1)[1])[3]
    if change == "header_time":
        clock.string = "Seating Begins 6:30 PM · Show 8:00 p.m."
    elif change == "header_date":
        date.string = "Sunday, March 14, 2027"
    elif change == "weekday":
        date.string = "Sunday, March 13, 2027"
    elif change == "header_title":
        soup.h1.string = "Another venue"
    elif change == "missing_header":
        header.decompose()
    elif change == "seating_only":
        clock.string = "Seating Begins 7:00 PM"
    elif change == "duplicate_header":
        soup.main.append(BeautifulSoup(str(header), "html.parser"))
    elif change == "duplicate_date":
        date.parent.append(BeautifulSoup(str(date) + str(clock), "html.parser"))
    elif change == "missing_props":
        flight_script.decompose()
    elif change == "slug":
        props["eventSlug"] = "another-event"
    elif change == "event_id":
        props["currentEventId"] = "another-id"
    elif change == "event_date":
        props["eventDate"] = "2027-03-14T03:00:00Z"
    elif change == "zone":
        props["venueTimezone"] = "America/Denver"
    elif change == "region":
        node["location"]["address"]["addressRegion"] = "BC"
    elif change == "country":
        node["location"]["address"]["addressCountry"] = "US"
    elif change == "utc":
        node["startDate"] = "2027-03-14T02:00:00+00:00"
    if change != "missing_props":
        values = [props, dict(props, venueTimezone="America/Denver")] if change == "conflicting_zone" else props
        flight_script.string = "self.__next_f.push(" + json.dumps([1, "1:" + json.dumps(values) + "\n"]) + ")"
    event = extract(soup, script, node)[0]
    assert event.start_date.isoformat() == node["startDate"]


def test_timezone_split_main_props_and_unrelated_nearby_time():
    soup, script, node = evidence()
    flight = soup.find_all("script")[-1]
    raw = json.loads(flight.string.removeprefix("self.__next_f.push(").removesuffix(")"))[1]
    flight.decompose()
    for chunk in [raw[: len(raw) // 2], raw[len(raw) // 2 :]]:
        tag = soup.new_tag("script")
        tag.string = "self.__next_f.push(" + json.dumps([1, chunk]) + ")"
        soup.append(tag)
    soup.main.append(BeautifulSoup('<aside>Sunday, March 14, 2027 Seating Begins 8:00 PM · Show 9:00 p.m.</aside>', "html.parser"))
    assert extract(soup, script, node)[0].start_date.isoformat() == "2027-03-13T19:00:00-06:00"


def test_timezone_cancelled_alberta_event_is_not_restored_by_header():
    soup, script, node = evidence()
    node["eventStatus"] = "https://schema.org/EventCancelled"
    assert extract(soup, script, node) == []
