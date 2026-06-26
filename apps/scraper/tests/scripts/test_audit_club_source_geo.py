"""
Unit tests for ``bin/audit-club-source-geo``.

The script talks to the live scraper DB at runtime; these tests load it as a
module and exercise its pure classification logic (domain parsing and the two
mismatch signals) against synthetic source rows, with no database.
"""

import importlib.machinery
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

_SCRAPER_ROOT = Path(__file__).resolve().parents[2]  # apps/scraper/
_SCRIPT_PATH = _SCRAPER_ROOT / "bin" / "audit-club-source-geo"
_MODULE_NAME = "audit_club_source_geo"


def _load_module() -> ModuleType:
    loader = importlib.machinery.SourceFileLoader(_MODULE_NAME, str(_SCRIPT_PATH))
    spec = importlib.util.spec_from_loader(_MODULE_NAME, loader)
    if spec is None:
        raise AssertionError(f"Could not load spec for {_SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    original = sys.modules.get(_MODULE_NAME)
    try:
        sys.modules[_MODULE_NAME] = module
        loader.exec_module(module)
        return module
    finally:
        if original is None:
            sys.modules.pop(_MODULE_NAME, None)
        else:
            sys.modules[_MODULE_NAME] = original


@pytest.fixture
def mod():
    return _load_module()


def _src(**overrides):
    row = {
        "source_id": 1,
        "club_id": 1,
        "platform": "custom",
        "source_url": None,
        "enabled": True,
        "club_name": "Club",
        "city": "Town",
        "state": "ST",
        "website": None,
        "visible": True,
        "chain_id": None,
        "seatengine_id": None,
        "seatengine_v3_id": None,
        "eventbrite_id": None,
        "ticketmaster_id": None,
        "ovationtix_id": None,
        "wix_event_id": None,
        "squadup_id": None,
    }
    row.update(overrides)
    return row


# ---- registrable_domain -------------------------------------------------

@pytest.mark.parametrize("value,expected", [
    ("https://www.gothamcomedyclub.com", "gothamcomedyclub.com"),
    ("http://redroom.club/", "redroom.club"),
    ("venuepilot.co/graphql", "venuepilot.co"),
    ("https://tickets.tupelohall.com/default.asp", "tupelohall.com"),
    ("ccu.stageti.me", "stageti.me"),          # subdomain collapses to platform
    ("https://shop.example.co.uk/x", "example.co.uk"),  # two-label suffix
    ("tour_dates", None),                       # bare token, no dot
    ("", None),
    (None, None),
])
def test_registrable_domain(mod, value, expected):
    assert mod.registrable_domain(value) == expected


def test_generic_platform_detection(mod):
    assert mod.is_generic_platform("ticketmaster.com")
    assert mod.is_generic_platform("humanitix.com")
    assert mod.is_generic_platform("stageti.me")
    assert not mod.is_generic_platform("redroom.club")
    assert not mod.is_generic_platform("gothamcomedyclub.com")


# ---- website_domain_mismatch -------------------------------------------

def test_website_mismatch_flags_redroom_style(mod):
    """Venue-specific source domain != club's own website domain -> flagged."""
    rows = [_src(
        club_id=461, club_name="Red Room", city="New York", state="NY",
        platform="seatengine", source_url="https://redroom.club/events",
        website="https://nyc-venue.example.com",
    )]
    out = mod._website_domain_mismatch(rows)
    assert len(out) == 1
    assert out[0]["source_domain"] == "redroom.club"
    assert out[0]["website_domain"] == "example.com"


def test_website_mismatch_ignores_generic_platform(mod):
    """Source on a booking-SaaS domain carries no geo signal -> not flagged."""
    rows = [_src(
        source_url="https://events.humanitix.com/host/stomping-ground",
        website="https://stompinggroundcomedy.org",
    )]
    assert mod._website_domain_mismatch(rows) == []


def test_website_mismatch_matching_domains_clean(mod):
    """Post-fix Red Room: website now matches source domain -> not flagged."""
    rows = [_src(
        source_url="https://redroom.club/events",
        website="https://redroom.club/",
    )]
    assert mod._website_domain_mismatch(rows) == []


def test_website_mismatch_skips_when_no_website(mod):
    rows = [_src(source_url="https://redroom.club/events", website=None)]
    assert mod._website_domain_mismatch(rows) == []


# ---- shared_venue_across_geo -------------------------------------------

def test_shared_domain_across_geo_flagged(mod):
    """Same venue-specific domain, two clubs, two cities, no chain -> flagged."""
    rows = [
        _src(source_id=1, club_id=10, source_url="https://shared.example.com",
             city="Boston", state="MA"),
        _src(source_id=2, club_id=11, source_url="https://shared.example.com",
             city="Edmonton", state="AB"),
    ]
    out = mod._shared_venue_across_geo(rows, include_chains=False)
    assert len(out) == 1
    assert out[0]["identifier"] == "example.com"
    assert out[0]["club_count"] == 2
    assert out[0]["same_chain"] is False


def test_shared_domain_same_chain_suppressed(mod):
    """Multi-city chain (shared chain_id) is suppressed by default."""
    rows = [
        _src(source_id=1, club_id=30, chain_id=1, source_url="https://improv.com",
             city="Brea", state="CA"),
        _src(source_id=2, club_id=31, chain_id=1, source_url="https://improv.com",
             city="Schaumburg", state="IL"),
    ]
    assert mod._shared_venue_across_geo(rows, include_chains=False) == []
    shown = mod._shared_venue_across_geo(rows, include_chains=True)
    assert len(shown) == 1
    assert shown[0]["same_chain"] is True


def test_shared_venue_id_across_geo_flagged(mod):
    """Same concrete seatengine_id on clubs in different cities -> flagged."""
    rows = [
        _src(source_id=1, club_id=10, seatengine_id=436,
             source_url="https://www.ticketmaster.com", city="New York", state="NY"),
        _src(source_id=2, club_id=11, seatengine_id=436,
             source_url="https://www.ticketmaster.com", city="Provincetown", state="MA"),
    ]
    out = mod._shared_venue_across_geo(rows, include_chains=False)
    keys = {(r["identifier_kind"], r["identifier"]) for r in out}
    assert ("seatengine_id", "436") in keys


def test_shared_domain_same_geo_not_flagged(mod):
    """Two clubs, same domain, same city -> not a geo mismatch."""
    rows = [
        _src(source_id=1, club_id=10, source_url="https://shared.example.com",
             city="Denver", state="CO"),
        _src(source_id=2, club_id=11, source_url="https://shared.example.com",
             city="Denver", state="CO"),
    ]
    assert mod._shared_venue_across_geo(rows, include_chains=False) == []


def test_shared_squadup_id_across_geo_flagged(mod):
    """squadup.com is denylisted, so squadup_id is the only signal left."""
    rows = [
        _src(source_id=1, club_id=10, squadup_id="sq-7",
             source_url="https://www.squadup.com/x", city="Reno", state="NV"),
        _src(source_id=2, club_id=11, squadup_id="sq-7",
             source_url="https://www.squadup.com/x", city="Tampa", state="FL"),
    ]
    out = mod._shared_venue_across_geo(rows, include_chains=False)
    keys = {(r["identifier_kind"], r["identifier"]) for r in out}
    # The denylisted domain produces no bucket; only the id collision flags.
    assert ("squadup_id", "sq-7") in keys
    assert ("domain", "squadup.com") not in keys


# ---- source_venue_geo_mismatch -----------------------------------------

def _tm(value):
    """Helper: build the venue_locations key for a ticketmaster_id."""
    return ("ticketmaster_id", value)


def test_source_venue_state_mismatch_flagged(mod):
    """The TASK-3363 case: Rockford IL identity, Hollywood FL TM venue."""
    rows = [_src(
        club_id=2844, club_name="Hard Rock Live", city="Rockford", state="IL",
        ticketmaster_id="KovZpZA6AEaA",
    )]
    locs = {_tm("KovZpZA6AEaA"): {
        "name": "Hard Rock Live", "city": "Hollywood", "state": "FL",
        "country": "US"}}
    out = mod._source_venue_geo_mismatch(rows, locs)
    assert len(out) == 1
    assert out[0]["mismatch"] == "state"
    assert out[0]["club_id"] == 2844
    assert out[0]["venue_state"] == "FL"
    assert out[0]["venue_city"] == "Hollywood"
    assert out[0]["venue_id_kind"] == "ticketmaster_id"


def test_source_venue_city_mismatch_flagged(mod):
    """Same state, different city -> lower-confidence city mismatch."""
    rows = [_src(city="Hollywood", state="FL", ticketmaster_id="V1")]
    locs = {_tm("V1"): {"name": "X", "city": "Fort Lauderdale", "state": "FL",
                        "country": "US"}}
    out = mod._source_venue_geo_mismatch(rows, locs)
    assert len(out) == 1
    assert out[0]["mismatch"] == "city"


def test_source_venue_matching_geo_not_flagged(mod):
    rows = [_src(city="Hollywood", state="FL", ticketmaster_id="V1")]
    locs = {_tm("V1"): {"name": "X", "city": "Hollywood", "state": "FL",
                        "country": "US"}}
    assert mod._source_venue_geo_mismatch(rows, locs) == []


def test_source_venue_unresolved_id_not_flagged(mod):
    """An id that resolved to None carries no geo signal."""
    rows = [_src(city="Rockford", state="IL", ticketmaster_id="V1")]
    assert mod._source_venue_geo_mismatch(rows, {_tm("V1"): None}) == []
    # Also: id absent from the resolution map entirely.
    assert mod._source_venue_geo_mismatch(rows, {}) == []


def test_source_venue_no_ticketmaster_id_skipped(mod):
    rows = [_src(city="Rockford", state="IL", ticketmaster_id=None)]
    assert mod._source_venue_geo_mismatch(rows, {}) == []


def test_source_venue_state_sorts_before_city(mod):
    rows = [
        _src(source_id=1, club_id=20, city="Hollywood", state="FL",
             ticketmaster_id="CITY"),   # city mismatch
        _src(source_id=2, club_id=10, city="Rockford", state="IL",
             ticketmaster_id="STATE"),  # state mismatch
    ]
    locs = {
        _tm("CITY"): {"name": "a", "city": "Fort Lauderdale", "state": "FL"},
        _tm("STATE"): {"name": "b", "city": "Hollywood", "state": "FL"},
    }
    out = mod._source_venue_geo_mismatch(rows, locs)
    assert [r["mismatch"] for r in out] == ["state", "city"]


def test_format_csv_source_venue_geo_mismatch(mod):
    rows = mod._source_venue_geo_mismatch(
        [_src(club_id=2844, city="Rockford", state="IL",
              ticketmaster_id="KovZpZA6AEaA")],
        {_tm("KovZpZA6AEaA"): {"name": "Hard Rock Live", "city": "Hollywood",
                               "state": "FL", "country": "US"}},
    )
    out = mod._format_csv("source_venue_geo_mismatch", rows)
    header = out.splitlines()[0]
    assert header.split(",") == [
        "signal", "mismatch", "club_id", "club_name", "city", "state",
        "source_id", "platform", "enabled", "venue_id_kind", "venue_id",
        "venue_name", "venue_city", "venue_state",
    ]
    assert "Hollywood" in out


# ---- network helpers (requests mocked) ---------------------------------

class _FakeResp:
    def __init__(self, status_code, payload=None, raise_json=False):
        self.status_code = status_code
        self._payload = payload
        self._raise_json = raise_json

    @property
    def ok(self):
        return 200 <= self.status_code < 300

    def json(self):
        if self._raise_json:
            raise ValueError("not json")
        return self._payload


def test_resolve_tm_venue_success(mod, monkeypatch):
    import requests
    monkeypatch.setattr(requests, "get", lambda *a, **k: _FakeResp(
        200, {"name": "Hard Rock Live", "city": {"name": "Hollywood"},
              "state": {"stateCode": "FL"}, "country": {"countryCode": "US"}}))
    loc = mod._resolve_ticketmaster_venue("V1", "key")
    assert loc == {"name": "Hard Rock Live", "city": "Hollywood", "state": "FL"}


def test_resolve_tm_venue_404_returns_none(mod, monkeypatch):
    import requests
    monkeypatch.setattr(requests, "get", lambda *a, **k: _FakeResp(404))
    assert mod._resolve_ticketmaster_venue("V1", "key") is None


def test_resolve_tm_venue_non_ok_returns_none(mod, monkeypatch):
    import requests
    monkeypatch.setattr(requests, "get", lambda *a, **k: _FakeResp(500))
    assert mod._resolve_ticketmaster_venue("V1", "key") is None


def test_resolve_tm_venue_non_json_returns_none(mod, monkeypatch):
    import requests
    monkeypatch.setattr(requests, "get",
                        lambda *a, **k: _FakeResp(200, raise_json=True))
    assert mod._resolve_ticketmaster_venue("V1", "key") is None


def test_resolve_tm_venue_no_geo_returns_none(mod, monkeypatch):
    """A record with neither city nor state carries no usable geo signal."""
    import requests
    monkeypatch.setattr(requests, "get", lambda *a, **k: _FakeResp(
        200, {"name": "X", "city": None, "state": None}))
    assert mod._resolve_ticketmaster_venue("V1", "key") is None


def test_resolve_tm_venue_request_exception_returns_none(mod, monkeypatch):
    import requests

    def boom(*a, **k):
        raise requests.RequestException("network down")

    monkeypatch.setattr(requests, "get", boom)
    assert mod._resolve_ticketmaster_venue("V1", "key") is None


def test_resolve_tm_venue_429_retries_then_succeeds(mod, monkeypatch):
    import requests
    calls = {"n": 0}

    def flaky(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            return _FakeResp(429)
        return _FakeResp(200, {"name": "X", "city": {"name": "Reno"},
                               "state": {"stateCode": "NV"}})

    monkeypatch.setattr(requests, "get", flaky)
    monkeypatch.setattr(mod.time, "sleep", lambda *_a, **_k: None)  # no real backoff
    loc = mod._resolve_ticketmaster_venue("V1", "key")
    assert calls["n"] == 2
    assert loc["state"] == "NV"


def test_resolve_tm_venues_dedup_and_pacing(mod, monkeypatch):
    """Driver resolves each id once and paces between calls (not before the first)."""
    import requests
    seen = []
    monkeypatch.setattr(requests, "get", lambda url, *a, **k: (
        seen.append(url) or _FakeResp(200, {"name": "X", "city": {"name": "A"},
                                            "state": {"stateCode": "CA"}})))
    sleeps = []
    monkeypatch.setattr(mod.time, "sleep", lambda s: sleeps.append(s))
    out = mod._resolve_ticketmaster_venues({"B", "A"}, "key")
    assert set(out) == {"A", "B"}
    assert len(seen) == 2          # one network call per distinct id
    assert len(sleeps) == 1        # paced between the 2 calls, none before the first


def test_resolve_tm_venues_max_resolve_caps(mod, monkeypatch):
    import requests
    seen = []
    monkeypatch.setattr(requests, "get", lambda url, *a, **k: (
        seen.append(url) or _FakeResp(200, {"name": "X", "city": {"name": "A"},
                                            "state": {"stateCode": "CA"}})))
    monkeypatch.setattr(mod.time, "sleep", lambda *_a, **_k: None)
    out = mod._resolve_ticketmaster_venues({"A", "B", "C"}, "key", max_resolve=1)
    assert len(seen) == 1
    assert len(out) == 1


# ---- Eventbrite network helpers (requests mocked) ----------------------

def _eb(value):
    """Helper: build the venue_locations key for an eventbrite_id."""
    return ("eventbrite_id", value)


def test_resolve_eb_venue_success(mod, monkeypatch):
    """Eventbrite address.region is the state; address.city is the city."""
    import requests
    captured = {}

    def fake_get(url, *a, **k):
        captured["url"] = url
        captured["headers"] = k.get("headers")
        return _FakeResp(200, {"name": "The Bell House",
                               "address": {"city": "Brooklyn", "region": "NY"}})

    monkeypatch.setattr(requests, "get", fake_get)
    loc = mod._resolve_eventbrite_venue("12345", "tok")
    assert loc == {"name": "The Bell House", "city": "Brooklyn", "state": "NY"}
    # Auth must be a Bearer token; venue id is in the path.
    assert captured["headers"]["Authorization"] == "Bearer tok"
    assert captured["url"].endswith("/venues/12345/")


def test_resolve_eb_venue_404_returns_none(mod, monkeypatch):
    import requests
    monkeypatch.setattr(requests, "get", lambda *a, **k: _FakeResp(404))
    assert mod._resolve_eventbrite_venue("V1", "tok") is None


def test_resolve_eb_venue_non_ok_returns_none(mod, monkeypatch):
    import requests
    monkeypatch.setattr(requests, "get", lambda *a, **k: _FakeResp(500))
    assert mod._resolve_eventbrite_venue("V1", "tok") is None


def test_resolve_eb_venue_non_json_returns_none(mod, monkeypatch):
    import requests
    monkeypatch.setattr(requests, "get",
                        lambda *a, **k: _FakeResp(200, raise_json=True))
    assert mod._resolve_eventbrite_venue("V1", "tok") is None


def test_resolve_eb_venue_no_geo_returns_none(mod, monkeypatch):
    """A record with neither city nor region carries no usable geo signal."""
    import requests
    monkeypatch.setattr(requests, "get", lambda *a, **k: _FakeResp(
        200, {"name": "X", "address": {"city": None, "region": None}}))
    assert mod._resolve_eventbrite_venue("V1", "tok") is None
    # Missing address object entirely is also tolerated.
    monkeypatch.setattr(requests, "get", lambda *a, **k: _FakeResp(
        200, {"name": "X"}))
    assert mod._resolve_eventbrite_venue("V1", "tok") is None


def test_resolve_eb_venue_request_exception_returns_none(mod, monkeypatch):
    import requests

    def boom(*a, **k):
        raise requests.RequestException("network down")

    monkeypatch.setattr(requests, "get", boom)
    assert mod._resolve_eventbrite_venue("V1", "tok") is None


def test_resolve_eb_venue_429_retries_then_succeeds(mod, monkeypatch):
    import requests
    calls = {"n": 0}

    def flaky(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            return _FakeResp(429)
        return _FakeResp(200, {"name": "X",
                               "address": {"city": "Reno", "region": "NV"}})

    monkeypatch.setattr(requests, "get", flaky)
    monkeypatch.setattr(mod.time, "sleep", lambda *_a, **_k: None)  # no real backoff
    loc = mod._resolve_eventbrite_venue("V1", "tok")
    assert calls["n"] == 2
    assert loc["state"] == "NV"


def test_resolve_eb_venues_dedup_and_pacing(mod, monkeypatch):
    """Driver resolves each id once and paces between calls (not before the first)."""
    import requests
    seen = []
    monkeypatch.setattr(requests, "get", lambda url, *a, **k: (
        seen.append(url) or _FakeResp(200, {"name": "X",
                                            "address": {"city": "A", "region": "CA"}})))
    sleeps = []
    monkeypatch.setattr(mod.time, "sleep", lambda s: sleeps.append(s))
    out = mod._resolve_eventbrite_venues({"B", "A"}, "tok")
    assert set(out) == {"A", "B"}
    assert len(seen) == 2          # one network call per distinct id
    assert len(sleeps) == 1        # paced between the 2 calls, none before the first


def test_resolve_eb_venues_max_resolve_caps(mod, monkeypatch):
    import requests
    seen = []
    monkeypatch.setattr(requests, "get", lambda url, *a, **k: (
        seen.append(url) or _FakeResp(200, {"name": "X",
                                            "address": {"city": "A", "region": "CA"}})))
    monkeypatch.setattr(mod.time, "sleep", lambda *_a, **_k: None)
    out = mod._resolve_eventbrite_venues({"A", "B", "C"}, "tok", max_resolve=1)
    assert len(seen) == 1
    assert len(out) == 1


# ---- source_venue_geo_mismatch: eventbrite + multi-platform ------------

def test_source_venue_eventbrite_state_mismatch_flagged(mod):
    """eventbrite_id resolving to a different state -> flagged on its own."""
    rows = [_src(
        club_id=701, club_name="Drifting Venue", city="Rockford", state="IL",
        eventbrite_id="EB1",
    )]
    locs = {_eb("EB1"): {"name": "Real Venue", "city": "Hollywood", "state": "FL"}}
    out = mod._source_venue_geo_mismatch(rows, locs)
    assert len(out) == 1
    assert out[0]["mismatch"] == "state"
    assert out[0]["venue_id_kind"] == "eventbrite_id"
    assert out[0]["venue_id"] == "EB1"
    assert out[0]["venue_state"] == "FL"


def test_source_venue_eventbrite_matching_geo_not_flagged(mod):
    rows = [_src(city="Brooklyn", state="NY", eventbrite_id="EB1")]
    locs = {_eb("EB1"): {"name": "X", "city": "Brooklyn", "state": "NY"}}
    assert mod._source_venue_geo_mismatch(rows, locs) == []


def test_source_venue_eventbrite_unresolved_id_not_flagged(mod):
    rows = [_src(city="Rockford", state="IL", eventbrite_id="EB1")]
    assert mod._source_venue_geo_mismatch(rows, {_eb("EB1"): None}) == []
    assert mod._source_venue_geo_mismatch(rows, {}) == []


def test_source_venue_ticketmaster_takes_priority_over_eventbrite(mod):
    """A source carrying both ids uses ticketmaster_id (first in priority)."""
    rows = [_src(city="Rockford", state="IL",
                 ticketmaster_id="TM1", eventbrite_id="EB1")]
    locs = {
        _tm("TM1"): {"name": "TM Venue", "city": "Hollywood", "state": "FL"},
        _eb("EB1"): {"name": "EB Venue", "city": "Austin", "state": "TX"},
    }
    out = mod._source_venue_geo_mismatch(rows, locs)
    assert len(out) == 1
    assert out[0]["venue_id_kind"] == "ticketmaster_id"
    assert out[0]["venue_state"] == "FL"


def test_source_venue_mixed_platforms_sorted(mod):
    """TM and EB sources mix; state mismatches sort before city, then club_id."""
    rows = [
        _src(source_id=1, club_id=20, city="Hollywood", state="FL",
             ticketmaster_id="TMCITY"),       # city mismatch (TM)
        _src(source_id=2, club_id=10, city="Rockford", state="IL",
             eventbrite_id="EBSTATE"),        # state mismatch (EB)
    ]
    locs = {
        _tm("TMCITY"): {"name": "a", "city": "Fort Lauderdale", "state": "FL"},
        _eb("EBSTATE"): {"name": "b", "city": "Austin", "state": "TX"},
    }
    out = mod._source_venue_geo_mismatch(rows, locs)
    assert [(r["mismatch"], r["venue_id_kind"]) for r in out] == [
        ("state", "eventbrite_id"), ("city", "ticketmaster_id")]


# ---- _normalize_city / benign city-variant suppression -----------------

@pytest.mark.parametrize("a,b", [
    ("New York", "New York City"),       # club 1042 trailing "City"
    ("St Petersburg", "Saint Petersburg"),  # club 2507 St -> Saint
    ("St. Louis", "Saint Louis"),        # club 2509 St. -> Saint
    ("st louis", "SAINT LOUIS"),         # case-insensitive
])
def test_normalize_city_treats_variants_as_equal(mod, a, b):
    assert mod._normalize_city(a) == mod._normalize_city(b)


@pytest.mark.parametrize("a,b", [
    ("Brooklyn", "Manhattan"),
    ("Saint Louis", "Saint Paul"),
    ("Kansas City", "Jersey City"),      # distinct "City" names stay distinct
])
def test_normalize_city_keeps_distinct_cities_distinct(mod, a, b):
    assert mod._normalize_city(a) != mod._normalize_city(b)


def test_normalize_city_blank(mod):
    assert mod._normalize_city("") == ""
    assert mod._normalize_city(None) == ""
    assert mod._normalize_city("   ") == ""


@pytest.mark.parametrize("club_city,venue_city", [
    ("New York", "New York City"),       # club 1042
    ("St Petersburg", "Saint Petersburg"),  # club 2507
    ("St. Louis", "Saint Louis"),        # club 2509
])
def test_source_venue_benign_city_variant_not_flagged(mod, club_city, venue_city):
    """Known benign same-state city spelling variants must not surface."""
    rows = [_src(city=club_city, state="NY" if "York" in club_city else "MO",
                 ticketmaster_id="V1")]
    state = "NY" if "York" in club_city else "MO"
    locs = {_tm("V1"): {"name": "X", "city": venue_city, "state": state}}
    assert mod._source_venue_geo_mismatch(rows, locs) == []


def test_source_venue_genuine_city_mismatch_still_flagged(mod):
    """Normalization must not mask a real same-state different-city corruption."""
    rows = [_src(city="Hollywood", state="FL", ticketmaster_id="V1")]
    locs = {_tm("V1"): {"name": "X", "city": "Fort Lauderdale", "state": "FL"}}
    out = mod._source_venue_geo_mismatch(rows, locs)
    assert len(out) == 1
    assert out[0]["mismatch"] == "city"


# ---- CSV / _flatten_shared ---------------------------------------------

def test_format_csv_website_mismatch(mod):
    rows = mod._website_domain_mismatch([_src(
        source_url="https://redroom.club/events",
        website="https://nyc-venue.example.com",
    )])
    out = mod._format_csv("website_domain_mismatch", rows)
    header = out.splitlines()[0]
    assert header.split(",") == [
        "signal", "club_id", "club_name", "city", "state", "source_id",
        "platform", "enabled", "source_domain", "website_domain",
        "source_url", "website",
    ]
    assert "redroom.club" in out


def test_format_csv_shared_venue_flattens_one_row_per_club(mod):
    groups = mod._shared_venue_across_geo([
        _src(source_id=1, club_id=10, source_url="https://shared.example.com",
             city="Boston", state="MA"),
        _src(source_id=2, club_id=11, source_url="https://shared.example.com",
             city="Edmonton", state="AB"),
    ], include_chains=False)
    out = mod._format_csv("shared_venue_across_geo", groups)
    lines = out.strip().splitlines()
    assert lines[0].split(",")[:3] == ["signal", "identifier_kind", "identifier"]
    # header + one row per member club
    assert len(lines) == 1 + 2


def test_format_csv_empty_is_blank(mod):
    assert mod._format_csv("website_domain_mismatch", []) == ""
