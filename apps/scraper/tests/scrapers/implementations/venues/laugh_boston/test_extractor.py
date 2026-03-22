"""
Unit tests for LaughBostonEventExtractor.extract_tixr_urls().
"""

from laughtrack.scrapers.implementations.venues.laugh_boston.extractor import (
    LaughBostonEventExtractor,
)


def _html_with_tixr_links(*slugs: str, group: str = "laughboston") -> str:
    """Build minimal HTML containing Tixr event links for the given slugs."""
    links = "\n".join(
        f'<a href="https://www.tixr.com/groups/{group}/events/{slug}">Buy Tickets</a>'
        for slug in slugs
    )
    return f"<html><body>{links}</body></html>"


class TestExtractTixrUrls:
    def test_extracts_single_event_url(self):
        html = _html_with_tixr_links("comedy-night-april-4-12345")
        urls = LaughBostonEventExtractor.extract_tixr_urls(html)
        assert urls == ["https://www.tixr.com/groups/laughboston/events/comedy-night-april-4-12345"]

    def test_extracts_multiple_event_urls(self):
        html = _html_with_tixr_links("show-march-28-11111", "show-march-31-22222")
        urls = LaughBostonEventExtractor.extract_tixr_urls(html)
        assert len(urls) == 2
        assert all("tixr.com" in u and "/events/" in u for u in urls)

    def test_deduplicates_repeated_urls(self):
        slug = "comedy-night-april-4-12345"
        html = _html_with_tixr_links(slug, slug)
        urls = LaughBostonEventExtractor.extract_tixr_urls(html)
        assert len(urls) == 1

    def test_ignores_non_event_tixr_links(self):
        """Group-level Tixr links without /events/ are excluded by post-filter."""
        html = """<html><body>
<a href="https://www.tixr.com/groups/laughboston">Full Schedule</a>
<a href="https://www.tixr.com/groups/laughboston/events/comedy-night-99999">Buy</a>
</body></html>"""
        urls = LaughBostonEventExtractor.extract_tixr_urls(html)
        assert len(urls) == 1
        assert "/events/" in urls[0]

    def test_accepts_any_tixr_group(self):
        """The extractor uses a generic regex and accepts event links from any Tixr group."""
        html = """<html><body>
<a href="https://www.tixr.com/groups/improvasylum/events/ia-event-456">IA</a>
<a href="https://www.tixr.com/groups/laughboston/events/lb-event-789">LB</a>
</body></html>"""
        urls = LaughBostonEventExtractor.extract_tixr_urls(html)
        assert len(urls) == 2

    def test_returns_empty_for_no_tixr_links(self):
        html = "<html><body><a href='https://laughboston.com'>Home</a></body></html>"
        urls = LaughBostonEventExtractor.extract_tixr_urls(html)
        assert urls == []

    def test_returns_empty_for_empty_html(self):
        urls = LaughBostonEventExtractor.extract_tixr_urls("")
        assert urls == []
