"""
Unit tests for LaughBostonEventExtractor.extract_tixr_urls_from_pixl().
"""

from laughtrack.scrapers.implementations.venues.laugh_boston.extractor import (
    LaughBostonEventExtractor,
)


def _pixl_response(*ticket_urls: str) -> dict:
    """Build a minimal Pixl Calendar API response with the given ticket URLs."""
    return {
        "events": [
            {"id": f"id-{i}", "title": f"Show {i}", "ticketUrl": url}
            for i, url in enumerate(ticket_urls)
        ]
    }


def _tixr_url(slug: str) -> str:
    return f"https://www.tixr.com/groups/laughboston/events/{slug}"


class TestExtractTixrUrlsFromPixl:
    def test_extracts_single_event_url(self):
        data = _pixl_response(_tixr_url("comedy-night-12345"))
        urls = LaughBostonEventExtractor.extract_tixr_urls_from_pixl(data)
        assert urls == [_tixr_url("comedy-night-12345")]

    def test_extracts_multiple_event_urls(self):
        data = _pixl_response(_tixr_url("show-one-11111"), _tixr_url("show-two-22222"))
        urls = LaughBostonEventExtractor.extract_tixr_urls_from_pixl(data)
        assert len(urls) == 2
        assert all("tixr.com" in u and "/events/" in u for u in urls)

    def test_deduplicates_repeated_urls(self):
        url = _tixr_url("comedy-night-12345")
        data = _pixl_response(url, url)
        urls = LaughBostonEventExtractor.extract_tixr_urls_from_pixl(data)
        assert len(urls) == 1

    def test_preserves_order(self):
        slugs = ["show-a-1", "show-b-2", "show-c-3"]
        data = _pixl_response(*[_tixr_url(s) for s in slugs])
        urls = LaughBostonEventExtractor.extract_tixr_urls_from_pixl(data)
        assert urls == [_tixr_url(s) for s in slugs]

    def test_skips_events_without_tixr_url(self):
        data = {
            "events": [
                {"id": "a", "ticketUrl": "https://eventbrite.com/e/12345"},
                {"id": "b", "ticketUrl": _tixr_url("comedy-night-99999")},
                {"id": "c", "ticketUrl": ""},
                {"id": "d"},  # no ticketUrl key
            ]
        }
        urls = LaughBostonEventExtractor.extract_tixr_urls_from_pixl(data)
        assert urls == [_tixr_url("comedy-night-99999")]

    def test_skips_tixr_urls_without_events_segment(self):
        """Group-level Tixr links without /events/ are excluded."""
        data = {
            "events": [
                {"id": "a", "ticketUrl": "https://www.tixr.com/groups/laughboston"},
                {"id": "b", "ticketUrl": _tixr_url("valid-show-111")},
            ]
        }
        urls = LaughBostonEventExtractor.extract_tixr_urls_from_pixl(data)
        assert len(urls) == 1
        assert "/events/" in urls[0]

    def test_returns_empty_for_no_events(self):
        urls = LaughBostonEventExtractor.extract_tixr_urls_from_pixl({"events": []})
        assert urls == []

    def test_returns_empty_for_empty_dict(self):
        urls = LaughBostonEventExtractor.extract_tixr_urls_from_pixl({})
        assert urls == []
