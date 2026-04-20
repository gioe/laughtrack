from typing import Optional

from laughtrack.utilities.infrastructure.paginator.paginator import (
    Paginator,
    PaginatorConfig,
)


def test_get_next_page_url_without_finder_returns_none():
    p = Paginator()
    assert p.get_next_page_url("<html></html>", "https://example.com/") is None


def test_get_next_page_url_delegates_to_finder():
    def finder(html: str, base: str) -> Optional[str]:
        return base + "next" if "MORE" in html else None

    p = Paginator(config=PaginatorConfig(find_next_url=finder))
    assert p.get_next_page_url("MORE", "https://example.com/") == "https://example.com/next"
    assert p.get_next_page_url("DONE", "https://example.com/") is None


def test_get_next_page_url_swallows_finder_exceptions():
    def bad_finder(html: str, base: str) -> Optional[str]:
        raise RuntimeError("boom")

    p = Paginator(config=PaginatorConfig(find_next_url=bad_finder))
    assert p.get_next_page_url("<html></html>", "https://example.com/") is None


def test_debug_mode_propagates_from_config():
    p = Paginator(config=PaginatorConfig(debug_mode=True))
    assert p.debug_mode is True

    p_default = Paginator()
    assert p_default.debug_mode is False


def test_visited_urls_initialized_empty():
    p = Paginator()
    assert p._visited_urls == set()
