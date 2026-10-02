"""Bounded OCR tests using real pixels and captured Tesseract 5.5.3 TSV."""
import dataclasses
import hashlib
import json
from pathlib import Path
import shutil
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from laughtrack.core.clients.gotham.models.models import GothamFeedEvent
from laughtrack.scrapers.implementations.venues.gotham import poster
from laughtrack.scrapers.implementations.venues.gotham.scraper import GothamComedyClubScraper

FIXTURES = Path(__file__).parent / "fixtures/posters"


def poster_event(key="main"):
    date = {"main": "2026-10-01T20:00:00-04:00", "spotlight": "2026-10-06T19:30:00-04:00", "vintage": "2026-09-26T19:00:00-04:00"}[key]
    event = GothamFeedEvent.from_feed_item({"id": key, "fieldData": {
        "event-title": "The Vintage Lounge" if key == "vintage" else "Gotham All-Stars",
        "event-times": date, "event-description": "<p>Showcase</p>",
        "event-image-url": f"https://sc-events.s3.amazonaws.com/{key}.png",
        "event-url-slug": key,
    }})
    event.price = 25.0
    return event


def captured_poster(monkeypatch, key):
    fixture = json.loads((FIXTURES / f"{key}.json").read_text())
    data = (FIXTURES / f"{key}.png").read_bytes()
    assert hashlib.sha256(data).hexdigest() == fixture["sha256"]
    rows = iter(fixture["tsv"])
    with monkeypatch.context() as m:
        m.setattr(poster.shutil, "which", lambda _: "tesseract")
        m.setattr(poster.subprocess, "run", lambda *a, **kw: SimpleNamespace(stdout=next(rows).encode()))
        result = poster.read_poster(data)
    assert dataclasses.asdict(result) == {**fixture["expected"], "captions": tuple(fixture["expected"]["captions"])}
    return result


@pytest.mark.parametrize("key", ["main", "spotlight", "vintage"])
def test_captured_layout_matches_exact_performance(monkeypatch, key):
    result = captured_poster(monkeypatch, key)
    assert result.matches(poster_event(key))


@pytest.mark.parametrize("date", ["FRI 10/1 @8PM", "THURS 10/2 @8PM", "THURS 11/1 @8PM", "THURS 10/1 @9PM", "THURS 10/1 @8PM 2025", "THURS @8PM", "10/1 @8PM"])
def test_date_guards(monkeypatch, date):
    result = dataclasses.replace(captured_poster(monkeypatch, "main"), date=date)
    assert not result.matches(poster_event())


def test_room_and_brand_guards(monkeypatch):
    result = captured_poster(monkeypatch, "main")
    assert not dataclasses.replace(result, room="THE VINTAGE LOUNGE").matches(poster_event())
    assert not dataclasses.replace(result, brand="Other Theatre").matches(poster_event())
    assert not dataclasses.replace(result, room="unreadable").matches(poster_event())
    assert not dataclasses.replace(result, date="THURS 10/1 @20PM").matches(poster_event())
    vintage = captured_poster(monkeypatch, "vintage")
    assert not dataclasses.replace(vintage, room="").matches(poster_event("vintage"))


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="optional local OCR binary unavailable")
@pytest.mark.parametrize("key", ["main", "spotlight", "vintage"])
def test_real_tesseract_supported_layouts(key):
    result = poster.read_poster((FIXTURES / f"{key}.png").read_bytes())
    expected = json.loads((FIXTURES / f"{key}.json").read_text())["expected"]
    assert result is not None and result.matches(poster_event(key))
    assert set(result.captions) == set(expected["captions"])


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["date", "room", "same_bytes_other_url"])
async def test_asset_reuse_is_rejected(monkeypatch, change):
    first, second = poster_event(), poster_event()
    second.id = "another"
    if change == "date":
        second.start = "2026-10-02T20:00:00-04:00"
    elif change == "room":
        second.name = "The Vintage Lounge"
    else:
        second._raw_data["fieldData"]["event-image-url"] = "https://sc-events.s3.amazonaws.com/alias.png"
    reader = poster.PosterReader(AsyncMock())
    monkeypatch.setattr(reader, "fetch", AsyncMock(return_value=("samehash", b"image")))
    read = AsyncMock()
    monkeypatch.setattr(reader, "read", read)
    await reader.enrich([first, second], lambda names: {n:n for n in names})
    assert first._poster_billing is None and second._poster_billing is None
    read.assert_not_called()


@pytest.mark.asyncio
async def test_explicit_description_billing_wins(monkeypatch):
    event = poster_event()
    event._raw_data["fieldData"]["event-description"] = "<p>Hosted by Shaun Eli</p>"
    reader = poster.PosterReader(AsyncMock())
    monkeypatch.setattr(reader, "fetch", AsyncMock(return_value=("hash", b"image")))
    read = AsyncMock()
    monkeypatch.setattr(reader, "read", read)
    await reader.enrich([event], lambda names: {})
    read.assert_not_called()


def test_db_gate_rejects_ambiguous_substring_parent_and_denied(monkeypatch):
    from laughtrack.core.entities.lineup import handler as handlers
    def comic(name, uuid="one", parent=None):
        return SimpleNamespace(name=name, uuid=uuid, parent_comedian_id=parent)
    handler = MagicMock()
    handler.get_comedians_from_show_names.return_value = {
        "NATHAN MACINTOSH": [comic("Nathan Macintosh")],
        "DEAN EDWARDS": [comic("Dean Edwards"), comic("Dean Edwards", "two")],
        "DAN ST. GERMAIN": [comic("Dan St. Germain")],
        "KUNAL ARORA": [comic("Kunal")],
        "RAFI BASTOS": [comic("Rafi Bastos", parent=123)],
    }
    handler.execute_with_cursor.return_value = [{"name": "Dan St. Germain"}]
    monkeypatch.setattr(handlers, "LineupHandler", lambda: handler)
    result = GothamComedyClubScraper._corroborate_poster_names(list(handler.get_comedians_from_show_names.return_value))
    assert result == {"NATHAN MACINTOSH": "Nathan Macintosh"}


@pytest.mark.asyncio
async def test_db_failure_leaves_unknown(monkeypatch):
    event = poster_event()
    reader = poster.PosterReader(AsyncMock())
    monkeypatch.setattr(reader, "fetch", AsyncMock(return_value=("hash", b"image")))
    monkeypatch.setattr(reader, "read", AsyncMock(return_value=captured_poster(monkeypatch, "main")))
    def fail(names):
        raise RuntimeError("database unavailable")
    await reader.enrich([event], fail)
    assert event._poster_billing is None


@pytest.mark.asyncio
async def test_negative_caches_and_attempt_bound(monkeypatch):
    get_session = AsyncMock(side_effect=RuntimeError("offline"))
    reader = poster.PosterReader(get_session)
    for i in range(poster.MAX_ASSETS + 5):
        await reader.fetch(f"https://sc-events.s3.amazonaws.com/{i}.png")
    await reader.fetch("https://sc-events.s3.amazonaws.com/0.png")
    assert get_session.await_count == poster.MAX_ASSETS
    read = MagicMock(side_effect=ValueError("bad image"))
    monkeypatch.setattr(poster, "read_poster", read)
    assert await reader.read("hash", b"image") is None
    assert await reader.read("hash", b"image") is None
    assert read.call_count == 1


def test_missing_binary_and_oversize_image(monkeypatch):
    monkeypatch.setattr(poster.shutil, "which", lambda _: None)
    assert poster.read_poster(b"image") is None
    assert poster.read_poster(b"x" * (poster.MAX_BYTES + 1)) is None


@pytest.mark.asyncio
async def test_download_size_status_and_url_cache(monkeypatch):
    from contextlib import asynccontextmanager
    class Response:
        status_code = 200
        headers = {"content-type": "image/png"}
        async def aiter_content(self):
            yield b"a" * (poster.MAX_BYTES + 1)
    calls = []
    @asynccontextmanager
    async def stream(*args, **kwargs):
        calls.append((args, kwargs))
        yield Response()
    reader = poster.PosterReader(AsyncMock(return_value=SimpleNamespace(stream=stream)))
    assert await reader.fetch("https://sc-events.s3.amazonaws.com/big.png") is None
    assert await reader.fetch("https://sc-events.s3.amazonaws.com/big.png") is None
    assert len(calls) == 1
    assert calls[0][1]["allow_redirects"] is False
    assert calls[0][1]["timeout"] == 10
    Response.status_code = 302
    assert await reader.fetch("https://sc-events.s3.amazonaws.com/redirect.png") is None


@pytest.mark.asyncio
async def test_successful_hash_ocr_cache(monkeypatch):
    expected = captured_poster(monkeypatch, "main")
    read = MagicMock(return_value=expected)
    monkeypatch.setattr(poster, "read_poster", read)
    reader = poster.PosterReader(AsyncMock())
    assert await reader.read("hash", b"same") == expected
    assert await reader.read("hash", b"same") == expected
    assert read.call_count == 1


def test_unknown_tba_captions_are_ignored(monkeypatch):
    texts = iter(["", "THURS 10/1 @8PM", "COMEDY CLUB", "NATHAN MACINTOSH", "+MORE TBA", "SPECIAL GUEST", "GOTHAN COMEDY"])
    monkeypatch.setattr(poster, "_read_crop", lambda *a, **kw: next(texts))
    monkeypatch.setattr(poster.shutil, "which", lambda _: "tesseract")
    result = poster.read_poster((FIXTURES / "main.png").read_bytes())
    assert result.captions == ("NATHAN MACINTOSH",)


def test_generic_no_date_and_pixel_limit(monkeypatch):
    monkeypatch.setattr(poster.shutil, "which", lambda _: "tesseract")
    read = MagicMock(return_value="COMEDY CLUB")
    monkeypatch.setattr(poster, "_read_crop", read)
    assert poster.read_poster((FIXTURES / "main.png").read_bytes()) is None
    assert read.call_count == 3
    monkeypatch.setattr(poster, "MAX_PIXELS", 100)
    read.reset_mock()
    assert poster.read_poster((FIXTURES / "main.png").read_bytes()) is None
    read.assert_not_called()


@pytest.mark.asyncio
async def test_deadline_stops_additional_work(monkeypatch):
    session = AsyncMock()
    reader = poster.PosterReader(session)
    reader.deadline = 0
    assert await reader.fetch("https://sc-events.s3.amazonaws.com/main.png") is None
    assert await reader.read("hash", b"image") is None
    session.assert_not_called()


@pytest.mark.asyncio
async def test_all_pages_are_associated_before_transform(monkeypatch):
    from laughtrack.scrapers.base.base_scraper import BaseScraper
    from laughtrack.scrapers.implementations.venues.gotham.data import GothamPageData
    from .test_pipeline_smoke import _club
    events = [poster_event(), poster_event("vintage")]
    pages = [(GothamPageData([events[0]]), "page1"), (GothamPageData([events[1]]), "page2")]
    monkeypatch.setattr(BaseScraper, "_fetch_all_raw_data", AsyncMock(return_value=pages))
    enrich = AsyncMock()
    monkeypatch.setattr(poster.PosterReader, "enrich", enrich)
    scraper = GothamComedyClubScraper(_club())
    assert await scraper._fetch_all_raw_data(["page1", "page2"]) == pages
    assert enrich.call_args.args[0] == events
