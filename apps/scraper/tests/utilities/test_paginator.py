from typing import Optional

import pytest
import requests

from laughtrack.utilities.infrastructure.paginator.paginator import (
    Paginator,
    PaginatorConfig,
)


class FakeResponse:
    def __init__(self, text: str, status: int = 200):
        self.text = text
        self.status = status

    def raise_for_status(self):
        if self.status and self.status >= 400:
            raise RuntimeError(f"HTTP {self.status}")


class FakeSession(requests.Session):
    def __init__(self, pages: dict[str, tuple[str, int]]):
        super().__init__()
        # url -> (html, status)
        self.pages = pages
        self.calls: list[tuple[str, Optional[float]]] = []

    def get(self, url: str, timeout: Optional[float] = None, *args, **kwargs) -> FakeResponse:  # type: ignore[override]
        self.calls.append((url, timeout))
        text, status = self.pages.get(url, ("", 404))
        return FakeResponse(text=text, status=status)

    def close(self):
        pass


def test_pages_without_finder_yields_first_only(monkeypatch):
    start = "https://example.com/start"
    session = FakeSession({start: ("PAGE-1", 200)})
    cfg = PaginatorConfig(session=session)
    p = Paginator(config=cfg)

    pages = list(p.pages(start_url=start, max_pages=5))

    assert pages == ["PAGE-1"]
    assert session.calls == [(start, cfg.request_timeout)]


def test_find_next_advances_until_none():
    start = "https://example.com/start"
    next_url = "https://example.com/p2"
    session = FakeSession({start: ("P1", 200), next_url: ("P2", 200)})

    def finder(html: str, base: str) -> Optional[str]:
        return next_url if base == start else None

    cfg = PaginatorConfig(session=session, find_next_url=finder)
    p = Paginator(config=cfg)

    pages = list(p.pages(start_url=start, max_pages=10))

    assert pages == ["P1", "P2"]
    assert session.calls == [(start, cfg.request_timeout), (next_url, cfg.request_timeout)]


def test_track_visited_prevents_loop():
    start = "https://example.com/p"
    session = FakeSession({start: ("P", 200)})

    def loop_finder(html: str, base: str) -> Optional[str]:
        return base  # points to the same URL, should be detected as visited

    cfg = PaginatorConfig(session=session, find_next_url=loop_finder, track_visited=True)
    p = Paginator(config=cfg)

    pages = list(p.pages(start_url=start, max_pages=10))

    assert pages == ["P"]
    # Only one GET should be made because second iteration stops due to visited
    assert session.calls == [(start, cfg.request_timeout)]


def test_stop_condition_stops_after_yield():
    start = "https://example.com/start"
    p2 = "https://example.com/p2"
    session = FakeSession({start: ("OK", 200), p2: ("STOP", 200)})

    def finder(html: str, base: str) -> Optional[str]:
        return p2 if base == start else None

    def stop_condition(html: str, url: str) -> bool:
        return "STOP" in html

    cfg = PaginatorConfig(session=session, find_next_url=finder, stop_condition=stop_condition)
    p = Paginator(config=cfg)

    pages = list(p.pages(start_url=start, max_pages=10))

    # Second page is yielded, then stop condition triggers
    assert pages == ["OK", "STOP"]


def test_headers_applied_on_init():
    cfg = PaginatorConfig(headers={"X-Test": "1"})
    p = Paginator(config=cfg)
    try:
        assert p.session.headers.get("X-Test") == "1"
    finally:
        p.close()


def test_timeout_passed_to_session_get():
    start = "https://example.com/p"
    session = FakeSession({start: ("P", 200)})
    cfg = PaginatorConfig(session=session, request_timeout=3.5)
    p = Paginator(config=cfg)

    _ = list(p.pages(start_url=start))

    assert session.calls == [(start, 3.5)]


def test_delay_sleep_is_called(monkeypatch):
    calls = []

    def fake_sleep(secs):
        calls.append(secs)

    monkeypatch.setattr("time.sleep", fake_sleep)

    start = "https://example.com/p"
    session = FakeSession({start: ("P", 200)})
    cfg = PaginatorConfig(session=session, delay_seconds=0.25)
    p = Paginator(config=cfg)

    # Single page; delay is still applied after first iteration
    _ = list(p.pages(start_url=start))

    assert calls == [0.25]


def test_get_url_by_anchor_id_resolves_absolute():
    base = "https://example.com/start/page"
    html = '<html><body><a id="next" href="p2">Next</a></body></html>'
    p = Paginator()
    url = p.get_url_by_anchor_id(html, base_url=base, anchor_id="next")
    assert url == "https://example.com/start/page/p2"
    p.close()
