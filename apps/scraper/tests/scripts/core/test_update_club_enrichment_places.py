"""Integration test for the Places fallback inside update_club_enrichment.

Mocks the HTTP fetch + Places client; verifies that:
- Places is called for clubs with no LD-JSON hours and a usable city.
- LD-JSON hits do NOT trigger a Places call (cost guard).
- Clubs without a city are skipped (Places needs disambiguation).
- The summary reports per-source hours counts and total places_calls.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Match the path setup the script does at runtime so imports resolve in tests.
_repo_root = Path(__file__).resolve().parents[3]
_src_path = _repo_root / "src"
for p in (str(_src_path), str(_repo_root)):
    if p not in sys.path:
        sys.path.insert(0, p)

from scripts.core import update_club_enrichment as mod  # noqa: E402
from laughtrack.core.clients.google.places import PlacesHoursResult  # noqa: E402


def _target(
    club_id: int,
    name: str,
    city: str | None = "New York",
    state: str | None = "NY",
    has_hours: bool = False,
) -> mod._ClubTarget:
    return mod._ClubTarget(
        id=club_id,
        name=name,
        website=f"https://{name.lower().replace(' ', '')}.example.com",
        city=city,
        state=state,
        has_hours=has_hours,
    )


def _ldjson_html(hours_block: str = "") -> str:
    if hours_block:
        return f'<html><head><script type="application/ld+json">{{"openingHours": {hours_block}}}</script></head></html>'
    return "<html><head><title>nothing</title></head></html>"


def _places_query_returns(mapping: dict[str, dict[str, str] | None]) -> MagicMock:
    """Return a Places client mock whose fetch_hours pulls from mapping (by query)."""
    client = MagicMock()
    client.is_configured = True
    client.calls_remaining = 100
    client.calls_made = 0

    def fake_fetch(query: str) -> PlacesHoursResult:
        client.calls_made += 1
        hours = mapping.get(query)
        return PlacesHoursResult(place_id="ChIJfake" if hours else None, hours=hours)

    client.fetch_hours.side_effect = fake_fetch
    return client


@pytest.fixture
def patch_fetch_html():
    """Patch HttpClient.fetch_html with a per-URL mapping."""

    pages: dict[str, str] = {}

    async def fake_fetch_html(session, url, logger_context=None):
        return pages.get(url, "")

    with patch.object(mod.HttpClient, "fetch_html", new=fake_fetch_html), patch.object(
        mod, "close_js_browser", new=lambda: _noop_async()
    ):
        yield pages


async def _noop_async() -> None:
    return None


def _run_enrich(targets, places_client, force=False, dry_run=True):
    return asyncio.run(
        mod._enrich(targets, force=force, dry_run=dry_run, places_client=places_client)
    )


def test_places_fallback_fires_when_ldjson_yields_no_hours(patch_fetch_html):
    target = _target(1, "Comedy Cellar", city="New York", state="NY")
    patch_fetch_html[target.website] = _ldjson_html()  # no hours in HTML

    expected_query = "Comedy Cellar, New York, NY"
    places_client = _places_query_returns({
        expected_query: {"monday": "7pm-11pm", "tuesday": "7pm-11pm"},
    })

    summary = _run_enrich([target], places_client)

    assert places_client.fetch_hours.call_count == 1
    assert places_client.fetch_hours.call_args.args[0] == expected_query
    assert summary["hours_hits"] == 1
    assert summary["hours_from_places"] == 1
    assert summary["hours_from_ldjson"] == 0
    assert summary["places_calls"] == 1


def test_places_skipped_when_ldjson_already_has_hours(patch_fetch_html):
    target = _target(1, "Open Mic Hub", city="New York", state="NY")
    patch_fetch_html[target.website] = _ldjson_html(
        '"Mo-Fr 17:00-23:00"'
    )

    places_client = _places_query_returns({})

    summary = _run_enrich([target], places_client)

    assert places_client.fetch_hours.call_count == 0
    assert summary["hours_hits"] == 1
    assert summary["hours_from_ldjson"] == 1
    assert summary["hours_from_places"] == 0


def test_places_skipped_for_clubs_without_city(patch_fetch_html):
    target = _target(1, "Mystery Club", city=None, state="CA")
    patch_fetch_html[target.website] = _ldjson_html()

    places_client = _places_query_returns({})

    summary = _run_enrich([target], places_client)

    assert places_client.fetch_hours.call_count == 0
    assert summary["hours_hits"] == 0
    assert summary["places_calls"] == 0


def test_places_skipped_when_db_already_has_hours_without_force(patch_fetch_html):
    # has_hours=True means a NULL-fill run should NOT spend a Places call
    # even though LD-JSON came back empty.
    target = _target(1, "Already Known", city="Austin", state="TX", has_hours=True)
    patch_fetch_html[target.website] = _ldjson_html()

    places_client = _places_query_returns({"Already Known, Austin, TX": {"monday": "5pm-9pm"}})

    summary = _run_enrich([target], places_client, force=False)

    assert places_client.fetch_hours.call_count == 0
    assert summary["places_calls"] == 0


def test_places_runs_for_known_hours_club_when_force(patch_fetch_html):
    target = _target(1, "Already Known", city="Austin", state="TX", has_hours=True)
    patch_fetch_html[target.website] = _ldjson_html()

    places_client = _places_query_returns({"Already Known, Austin, TX": {"monday": "5pm-9pm"}})

    summary = _run_enrich([target], places_client, force=True)

    assert places_client.fetch_hours.call_count == 1
    assert summary["hours_from_places"] == 1


def test_disabled_places_client_makes_no_calls(patch_fetch_html):
    target = _target(1, "Some Club", city="Boston", state="MA")
    patch_fetch_html[target.website] = _ldjson_html()

    summary = _run_enrich([target], places_client=None)

    assert summary["hours_hits"] == 0
    assert summary["places_calls"] == 0


def test_places_query_format_omits_state_when_missing():
    assert mod._places_query("X", "Boise", None) == "X, Boise"
    assert mod._places_query("X", "Boise", "ID") == "X, Boise, ID"
    assert mod._places_query("X", None, "ID") is None
    assert mod._places_query("", "Boise", "ID") is None


def test_places_recovers_hours_when_website_fetch_fails(patch_fetch_html):
    # Empty HTML simulates a network/TLS failure that even Playwright
    # couldn't recover from — the Places fallback should still run and
    # the recovered hours should land in the returned result with
    # status="extracted" so the row gets written.
    target = _target(7, "Recovered Club", city="Denver", state="CO")
    patch_fetch_html[target.website] = ""

    places_client = _places_query_returns({
        "Recovered Club, Denver, CO": {"friday": "8pm-11pm"},
    })

    summary = _run_enrich([target], places_client)

    assert places_client.fetch_hours.call_count == 1
    assert summary["hours_hits"] == 1
    assert summary["hours_from_places"] == 1
    assert summary["extracted"] == 1


def test_places_recovers_hours_when_bot_blocked(patch_fetch_html):
    # Cloudflare-style interstitial — _bot_block_reason returns a signature
    # so status starts as "bot_blocked".  Places should still attempt the
    # lookup, and a hit should promote status back to "extracted".
    target = _target(8, "Blocked Club", city="Chicago", state="IL")
    patch_fetch_html[target.website] = (
        "<html><body>Just a moment... cf-browser-verification "
        "Checking your browser before accessing</body></html>"
    )

    places_client = _places_query_returns({
        "Blocked Club, Chicago, IL": {"saturday": "9pm-1am"},
    })

    summary = _run_enrich([target], places_client)

    assert places_client.fetch_hours.call_count == 1
    assert summary["hours_hits"] == 1
    assert summary["hours_from_places"] == 1
    # bot_blocked must NOT be incremented when Places recovered the data —
    # otherwise a bot-block alarm fires for a club whose data is intact.
    assert summary["bot_blocked"] == 0
    assert summary["extracted"] == 1
