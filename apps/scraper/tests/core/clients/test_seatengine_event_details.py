"""Optional description evidence is event-scoped, bounded, and failure tolerant."""

import asyncio
from copy import deepcopy
from types import SimpleNamespace

import pytest

from laughtrack.core.clients.seatengine.client import SeatEngineClient


def page(event_id=10, description="A stand-up comedy show tonight."):
    return f"""<nav>Comedy venue navigation</nav><div id="event-detail">
      <a href="/events/{event_id}">Other showtimes</a>
      <div id="descr"><div class="custom-content">{description}<script>bad script</script></div></div>
      <div id="bio">Biography: famous comedian.</div></div>"""


def show(sid=1, eid=10):
    return {"id": sid, "event": {"id": eid, "name": "Event"}, "inventories": [{"price": 2000}]}


def client(monkeypatch):
    value = SeatEngineClient.__new__(SeatEngineClient)
    value.club = SimpleNamespace(source_metadata={})
    value.log_warning = lambda *args: None
    value._build_public_show_url = lambda sid: f"https://example.com/shows/{sid}"
    return value


def test_narrow_description_excludes_biography_and_wrong_event():
    text = SeatEngineClient.extract_event_description(page(), "10")
    assert text == "A stand-up comedy show tonight."
    assert SeatEngineClient.extract_event_description(page(), "99") is None
    assert SeatEngineClient.extract_event_description(page(description=""), "10") is None
    assert SeatEngineClient.extract_event_description('<div id="bio">Comedy show</div>', "10") is None


def test_blocks_preserve_panel_provenance_and_paragraph_boundaries():
    html = page(description="<p>Doors open.</p><p>This show features comedy performances.</p>")
    html = html.replace("Biography: famous comedian.", "<p>Artist biography.</p><p>No live comedy tonight.</p>")
    blocks = SeatEngineClient.extract_event_blocks(html, "10")
    assert blocks == [
        {"selector": SeatEngineClient.DETAIL_SELECTOR, "text": "Doors open.\nThis show features comedy performances."},
        {"selector": "#event-detail #bio", "text": "Artist biography.\nNo live comedy tonight."},
    ]
    assert SeatEngineClient.extract_event_blocks(html, "99") == []
    assert SeatEngineClient.extract_event_blocks('<div id="bio">A night of comedy.</div>', "10") == []


def test_combined_page_budget_never_silently_discards_later_negative_panel():
    html = page(description="x" * 15990).replace("Biography: famous comedian.", "No live comedy tonight.")
    assert SeatEngineClient.extract_event_blocks(html, "10") == []


@pytest.mark.asyncio
async def test_one_request_per_event_preserves_occurrences_and_ticket_data(monkeypatch):
    value = client(monkeypatch)
    calls = []

    async def fetch(url):
        calls.append(url)
        return page()

    value.fetch_html = fetch
    inputs = [show(1), show(2)]
    before = deepcopy(inputs)
    output = await value.collect_event_descriptions(inputs)
    assert inputs == before and len(output) == 2 and len(calls) == 1
    for item in output:
        assert item["_comedy_event_detail"]["status"] == "collected"
        assert item["inventories"] == [{"price": 2000}]
        assert item["event"] == before[0]["event"]


@pytest.mark.asyncio
async def test_timeout_cancels_work_and_retains_all_events(monkeypatch):
    value = client(monkeypatch)
    value.DETAIL_TOTAL_TIMEOUT = 0.01
    value.DETAIL_REQUEST_TIMEOUT = 1
    value.DETAIL_MAX_EVENTS = 1
    active = 0

    async def fetch(url):
        nonlocal active
        active += 1
        try:
            await asyncio.sleep(10)
        finally:
            active -= 1

    value.fetch_html = fetch
    result = await value.collect_event_descriptions([show(1, 10), show(2, 20)])
    assert active == 0
    assert len(result) == 2
    assert all(r["_comedy_event_detail"]["status"] == "budget_exhausted" for r in result)


@pytest.mark.asyncio
async def test_failure_and_malformed_id_do_not_remove_events(monkeypatch):
    value = client(monkeypatch)

    async def fetch(url):
        raise RuntimeError("unavailable")

    value.fetch_html = fetch
    inputs = [show(), show(2, None)]
    result = await value.collect_event_descriptions(inputs)
    assert result[0]["_comedy_event_detail"]["status"] == "failed"
    assert result[1] == inputs[1]


@pytest.mark.asyncio
async def test_fetch_optin_only_after_venue_resolution(monkeypatch):
    value = client(monkeypatch)
    value.headers = {}
    value.venue_website = None
    value.log_info = lambda *args: None
    calls = []

    async def json_fetch(*args, **kwargs):
        return {"data": [show()]}

    async def venue(*args):
        return {"website": "https://example.com"}

    async def collect(shows):
        assert value.venue_website == "https://example.com"
        calls.append("details")
        return shows

    value.fetch_json = json_fetch
    value.fetch_venue_details = venue
    value.collect_event_descriptions = collect
    from laughtrack.core.clients.seatengine.circuit_breaker import SeatEngineCircuitBreaker

    monkeypatch.setattr(SeatEngineCircuitBreaker, "check_open", lambda self: None)
    monkeypatch.setattr(SeatEngineCircuitBreaker, "record_success", lambda self: None)
    assert len(await value.fetch_events("3")) == 1
    assert calls == []
    value.club.source_metadata["seatengine_event_details"] = True
    assert len(await value.fetch_events("3")) == 1
    assert calls == ["details"]


@pytest.mark.asyncio
async def test_routed_source_does_not_fetch_global_venue_page(monkeypatch):
    value = client(monkeypatch)
    value.club.source_metadata["seatengine_venue_routes"] = {}
    value.fetch_html = lambda *args: pytest.fail("Routed source must not fetch global venue website")
    inputs = [show()]
    assert await value.collect_event_descriptions(inputs) is inputs
