"""Unit tests for AsyncPaginator.async_pages().

Covers the three PaginatorConfig fields consumed exclusively by
AsyncPaginator (not by the Paginator base class): stop_condition,
track_visited, and delay_seconds. A FakeAsyncSession stands in for
curl_cffi's AsyncSession so pagination can be driven without real HTTP.
"""

from typing import Callable, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock

import pytest

from laughtrack.utilities.infrastructure.paginator import async_paginator as _ap_mod
from laughtrack.utilities.infrastructure.paginator.async_paginator import AsyncPaginator
from laughtrack.utilities.infrastructure.paginator.paginator import PaginatorConfig


class _FakeResponse:
    def __init__(self, status_code: int, text: str):
        self.status_code = status_code
        self.text = text


class FakeAsyncSession:
    """Minimal curl_cffi AsyncSession stand-in for AsyncPaginator tests.

    Configured with a {url: (status, text)} map; each ``await get(url)``
    returns the matching response and records the URL in ``calls``.
    Unknown URLs produce a 404 so the paginator's non-200 break path is
    exercised predictably.
    """

    def __init__(self, responses: Dict[str, Tuple[int, str]]):
        self._responses = responses
        self.calls: List[str] = []

    async def get(self, url: str) -> _FakeResponse:
        self.calls.append(url)
        status, text = self._responses.get(url, (404, ""))
        return _FakeResponse(status, text)


@pytest.fixture
def fake_async_session() -> Callable[[Dict[str, Tuple[int, str]]], FakeAsyncSession]:
    """Factory fixture: pass a {url: (status, text)} map, get a FakeAsyncSession."""

    def _build(responses: Dict[str, Tuple[int, str]]) -> FakeAsyncSession:
        return FakeAsyncSession(responses)

    return _build


def _next_url_finder(mapping: Dict[str, Optional[str]]) -> Callable[[str, str], Optional[str]]:
    """Build a find_next_url callback from a base_url -> next_url map."""

    def _finder(html: str, base_url: str) -> Optional[str]:
        return mapping.get(base_url)

    return _finder


def _parent_scraper_stub() -> MagicMock:
    """AsyncPaginator only reads ``parent_scraper.logger_context``."""
    stub = MagicMock()
    stub.logger_context = {}
    return stub


async def _collect(async_iter) -> List[Dict[str, str]]:
    return [item async for item in async_iter]


async def test_fake_async_session_drives_paginator_end_to_end(fake_async_session):
    """Baseline: FakeAsyncSession + AsyncPaginator yields every page once."""
    session = fake_async_session({
        "https://example.com/p1": (200, "<html>1</html>"),
        "https://example.com/p2": (200, "<html>2</html>"),
    })
    config = PaginatorConfig(
        find_next_url=_next_url_finder({
            "https://example.com/p1": "https://example.com/p2",
        })
    )
    paginator = AsyncPaginator(session, _parent_scraper_stub(), config=config)

    pages = await _collect(paginator.async_pages("https://example.com/p1"))

    assert [p["url"] for p in pages] == [
        "https://example.com/p1",
        "https://example.com/p2",
    ]
    assert [p["html_content"] for p in pages] == ["<html>1</html>", "<html>2</html>"]
    assert session.calls == [
        "https://example.com/p1",
        "https://example.com/p2",
    ]


async def test_stop_condition_terminates_pagination_early(fake_async_session):
    """stop_condition returning True prevents the next page from being fetched."""
    session = fake_async_session({
        "https://example.com/p1": (200, "page1"),
        "https://example.com/p2": (200, "STOP"),
        "https://example.com/p3": (200, "page3"),
    })
    config = PaginatorConfig(
        find_next_url=_next_url_finder({
            "https://example.com/p1": "https://example.com/p2",
            "https://example.com/p2": "https://example.com/p3",
        }),
        stop_condition=lambda html, url: "STOP" in html,
    )
    paginator = AsyncPaginator(session, _parent_scraper_stub(), config=config)

    pages = await _collect(paginator.async_pages("https://example.com/p1"))

    assert [p["url"] for p in pages] == [
        "https://example.com/p1",
        "https://example.com/p2",
    ]
    assert "https://example.com/p3" not in session.calls


async def test_track_visited_breaks_on_self_referential_next_url(fake_async_session):
    """A finder that returns the same URL is halted by track_visited."""
    session = fake_async_session({
        "https://example.com/loop": (200, "loop"),
    })
    config = PaginatorConfig(
        find_next_url=lambda html, base: "https://example.com/loop",
        track_visited=True,
    )
    paginator = AsyncPaginator(session, _parent_scraper_stub(), config=config)

    pages = await _collect(
        paginator.async_pages("https://example.com/loop", max_pages=10)
    )

    assert [p["url"] for p in pages] == ["https://example.com/loop"]
    assert session.calls == ["https://example.com/loop"]


async def test_delay_seconds_awaits_sleep_between_pages(
    monkeypatch, fake_async_session
):
    """delay_seconds > 0 awaits asyncio.sleep(delay) once per page transition."""
    fake_sleep = AsyncMock()
    monkeypatch.setattr(_ap_mod.asyncio, "sleep", fake_sleep)

    session = fake_async_session({
        "https://example.com/p1": (200, "page1"),
        "https://example.com/p2": (200, "page2"),
        "https://example.com/p3": (200, "page3"),
    })
    config = PaginatorConfig(
        find_next_url=_next_url_finder({
            "https://example.com/p1": "https://example.com/p2",
            "https://example.com/p2": "https://example.com/p3",
        }),
        delay_seconds=0.25,
    )
    paginator = AsyncPaginator(session, _parent_scraper_stub(), config=config)

    pages = await _collect(paginator.async_pages("https://example.com/p1"))

    assert len(pages) == 3
    assert fake_sleep.await_count == 2
    for call in fake_sleep.await_args_list:
        assert call.args == (0.25,)
