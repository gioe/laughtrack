"""Matched streamed admission evidence; frozen audit time is not current inventory."""
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
import pytest
from laughtrack.scrapers.implementations.venues.denver_comedy_lounge.extractor import DenverComedyLoungeExtractor as E

AUDIT = Path(__file__).resolve().parents[5] / "docs/audits/2026-09-27-price-extraction/venues"
EVENT = json.loads((AUDIT / "denver-event-rsc.json").read_text())
NOW = datetime(2026, 9, 27, tzinfo=timezone.utc)
SHOW = E._build_show({"item": {"url": EVENT["url"], "name": EVENT["name"]}})

def html(event, streamed=True):
    raw = json.dumps(event)
    if streamed:
        # Deliberately split inside the object to exercise stream concatenation.
        return ''.join('<script>self.__next_f.push([1,' + json.dumps(p) + '])</script>'
                       for p in [raw[:111], raw[111:]])
    return '<script type="application/ld+json">' + raw + '</script>'

def price(event):
    return E.extract_offer_price(html(event), SHOW, now=NOW)

def test_retained_stream_recovers_admission_and_excludes_vip_package():
    content = (AUDIT / "denver_comedy_lounge-1.html").read_text()
    assert E.extract_offer_price(content, SHOW, now=NOW) == 21
    assert E.extract_offer_price(content, SHOW, now=datetime(2026,10,5,tzinfo=timezone.utc)) is None

@pytest.mark.parametrize("streamed", [True, False])
def test_literal_and_split_stream_parity(streamed):
    assert E.extract_offer_price(html(EVENT, streamed), SHOW, now=NOW) == 21

@pytest.mark.parametrize("field,value", [
    ("url", "https://denvercomedylounge.com/shows/friday-9pm-2026-10-02"),
    ("url", "https://evil.example/shows/friday-7pm-2026-10-02"),
    ("startDate", "2026-10-02T21:00:00-06:00"), ("startDate", "2026-10-02T19:00:00"),
    ("startDate", None), ("eventStatus", "https://schema.org/EventCancelled"),
    ("@type", "EntertainmentBusiness")])
def test_event_identity_and_status(field, value):
    event = copy.deepcopy(EVENT); event[field] = value
    assert price(event) is None

@pytest.mark.parametrize("field,value", [
    ("price", 0), ("price", -1), ("price", True), ("price", "NaN"), ("price", "Infinity"),
    ("price", "$21"), ("priceCurrency", "CAD"), ("name", "VIP"),
    ("availability", "https://schema.org/SoldOut"), ("url", "https://evil.example/"),
    ("eligibleQuantity", {"value": 2}), ("description", "Two tickets"),
    ("validFrom", "2099-01-01T00:00:00Z"), ("validThrough", "2020-01-01T00:00:00Z"),
    ("validFrom", "broken"), ("validFrom", "2026-01-01")])
def test_unsafe_offers(field, value):
    event = copy.deepcopy(EVENT); event["offers"][0][field] = value
    assert price(event) is None

def test_vip_is_not_used_when_admission_missing():
    event = copy.deepcopy(EVENT); event["offers"] = event["offers"][1:]
    assert price(event) is None

def test_conflicting_matching_blocks_are_unknown():
    event = copy.deepcopy(EVENT); event["offers"][0]["price"] = 25
    assert E.extract_offer_price(html(EVENT)+html(event), SHOW, now=NOW) is None

def test_related_show_and_business_are_not_candidates():
    content = html({"show": {"relatedShows": [EVENT]}, "priceRange": "$$"}) + "Tickets from $20"
    assert E.extract_offer_price(content, SHOW, now=NOW) is None

def test_duplicate_identical_event_blocks_are_safe():
    assert E.extract_offer_price(html(EVENT)+html(EVENT,False), SHOW, now=NOW) == 21
