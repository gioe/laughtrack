"""
Unit tests for McCurdysExtractor.extract_detail_page_urls and extract_events.
"""

import pytest

from laughtrack.scrapers.implementations.venues.mccurdys_comedy_theatre.extractor import (
    McCurdysExtractor,
)


BASE_URL = "https://www.mccurdyscomedy.com/shows/"


def _listing_html(*show_ids: int) -> str:
    """Build minimal listing-page HTML with show cards."""
    cards = "\n".join(
        f'<div class="card" onclick="location.href=\'/shows/show.cfm?shoID={sid}\';">'
        f'<h2 class="summary">Show {sid}</h2></div>'
        for sid in show_ids
    )
    return f"<html><body>{cards}</body></html>"


def _detail_html(
    title: str = "Jamie Lissow",
    performances: list | None = None,
) -> str:
    """Build minimal detail-page HTML with title and performance rows."""
    if performances is None:
        performances = [
            ("Thursday, April 09 at 7:00 PM", "80809268"),
            ("Friday, April 10 at 7:30 PM", "80809269"),
        ]
    perf_items = "\n".join(
        f'<li><p> {date_str} </p><a href="/shows/buy.cfm?timTicketID={tid}">Buy</a></li>'
        for date_str, tid in performances
    )
    return (
        f'<html><body>'
        f'<h1 class="summary">{title}</h1>'
        f'<div class="upcoming-shows-sidebar"><ul>{perf_items}</ul></div>'
        f'</body></html>'
    )


# ── extract_detail_page_urls ────────────────────────────────────────────


class TestExtractDetailPageUrls:
    def test_extracts_urls_from_listing(self):
        html = _listing_html(101, 202)
        urls = McCurdysExtractor.extract_detail_page_urls(html, BASE_URL)
        assert urls == [
            "https://www.mccurdyscomedy.com/shows/show.cfm?shoID=101",
            "https://www.mccurdyscomedy.com/shows/show.cfm?shoID=202",
        ]

    def test_deduplicates_urls(self):
        html = _listing_html(101, 101, 202)
        urls = McCurdysExtractor.extract_detail_page_urls(html, BASE_URL)
        assert len(urls) == 2

    def test_empty_html_returns_empty(self):
        assert McCurdysExtractor.extract_detail_page_urls("", BASE_URL) == []

    def test_no_matches_returns_empty(self):
        html = "<html><body><p>No shows</p></body></html>"
        assert McCurdysExtractor.extract_detail_page_urls(html, BASE_URL) == []

    def test_base_url_without_shows_subpath(self):
        urls = McCurdysExtractor.extract_detail_page_urls(
            _listing_html(55),
            "https://www.mccurdyscomedy.com",
        )
        assert urls == ["https://www.mccurdyscomedy.com/shows/show.cfm?shoID=55"]

    def test_base_url_with_trailing_slash(self):
        urls = McCurdysExtractor.extract_detail_page_urls(
            _listing_html(55),
            "https://www.mccurdyscomedy.com/shows/",
        )
        assert urls == ["https://www.mccurdyscomedy.com/shows/show.cfm?shoID=55"]


# ── extract_events ──────────────────────────────────────────────────────


class TestExtractEvents:
    def test_extracts_performances(self):
        html = _detail_html()
        events = McCurdysExtractor.extract_events(html)
        assert len(events) == 2
        assert events[0].title == "Jamie Lissow"
        assert events[0].ticket_url == "https://www.etix.com/ticket/p/80809268"
        assert events[1].ticket_url == "https://www.etix.com/ticket/p/80809269"

    def test_preserves_date_str(self):
        html = _detail_html(performances=[("Friday, April 10 at 7:30 PM", "123")])
        events = McCurdysExtractor.extract_events(html)
        assert events[0].date_str == "Friday, April 10 at 7:30 PM"

    def test_empty_html_returns_empty(self):
        assert McCurdysExtractor.extract_events("") == []

    def test_no_title_returns_empty(self):
        html = '<html><body><p>No title here</p><li><p>Friday, April 10 at 7:30 PM</p><a href="/shows/buy.cfm?timTicketID=1">Buy</a></li></body></html>'
        assert McCurdysExtractor.extract_events(html) == []

    def test_empty_title_returns_empty(self):
        html = _detail_html(title="")
        assert McCurdysExtractor.extract_events(html) == []

    def test_whitespace_title_returns_empty(self):
        html = _detail_html(title="   ")
        assert McCurdysExtractor.extract_events(html) == []

    def test_title_with_no_performances(self):
        html = _detail_html(performances=[])
        assert McCurdysExtractor.extract_events(html) == []

    def test_single_performance(self):
        html = _detail_html(
            title="John Mulaney",
            performances=[("Saturday, January 15 at 9:00 PM", "99999")],
        )
        events = McCurdysExtractor.extract_events(html)
        assert len(events) == 1
        assert events[0].title == "John Mulaney"
        assert events[0].ticket_url == "https://www.etix.com/ticket/p/99999"
