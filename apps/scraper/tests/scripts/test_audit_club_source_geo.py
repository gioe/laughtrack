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
        "eventbrite_id": None,
        "ticketmaster_id": None,
        "ovationtix_id": None,
        "wix_event_id": None,
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
