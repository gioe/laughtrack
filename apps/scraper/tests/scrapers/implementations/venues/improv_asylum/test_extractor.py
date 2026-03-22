"""
Unit tests for ImprovAsylumEventExtractor.extract_tixr_urls().
"""

from laughtrack.scrapers.implementations.venues.improv_asylum.extractor import (
    ImprovAsylumEventExtractor,
)


def _html_with_tixr_links(*slugs: str) -> str:
    """Build minimal HTML containing Tixr event links for the given slugs."""
    links = "\n".join(
        f'<a href="https://www.tixr.com/groups/improvasylum/events/{slug}">Buy Tickets</a>'
        for slug in slugs
    )
    return f"<html><body>{links}</body></html>"


class TestExtractTixrUrls:
    def test_extracts_single_event_url(self):
        html = _html_with_tixr_links("main-stage-april-4-12345")
        urls = ImprovAsylumEventExtractor.extract_tixr_urls(html)
        assert urls == ["https://www.tixr.com/groups/improvasylum/events/main-stage-april-4-12345"]

    def test_extracts_multiple_event_urls(self):
        html = _html_with_tixr_links("raunch-march-28-11111", "house-teams-march-31-22222")
        urls = ImprovAsylumEventExtractor.extract_tixr_urls(html)
        assert len(urls) == 2
        assert all("improvasylum/events/" in u for u in urls)

    def test_deduplicates_repeated_urls(self):
        slug = "main-stage-april-4-12345"
        html = _html_with_tixr_links(slug, slug)
        urls = ImprovAsylumEventExtractor.extract_tixr_urls(html)
        assert len(urls) == 1

    def test_ignores_non_event_tixr_links(self):
        """Group-level and non-event Tixr links are excluded by post-filter."""
        html = """<html><body>
<a href="https://www.tixr.com/groups/improvasylum">Full Schedule</a>
<a href="https://www.tixr.com/groups/improvasylum/events/main-stage-99999">Buy</a>
</body></html>"""
        urls = ImprovAsylumEventExtractor.extract_tixr_urls(html)
        assert len(urls) == 1
        assert "/events/" in urls[0]

    def test_ignores_other_tixr_groups(self):
        """URLs for other Tixr groups are not matched."""
        html = """<html><body>
<a href="https://www.tixr.com/groups/laughboston/events/some-event-123">LB</a>
<a href="https://www.tixr.com/groups/improvasylum/events/ia-event-456">IA</a>
</body></html>"""
        urls = ImprovAsylumEventExtractor.extract_tixr_urls(html)
        assert len(urls) == 1
        assert "improvasylum" in urls[0]

    def test_returns_empty_for_no_tixr_links(self):
        html = "<html><body><a href='https://improvasylum.com'>Home</a></body></html>"
        urls = ImprovAsylumEventExtractor.extract_tixr_urls(html)
        assert urls == []

    def test_returns_empty_for_empty_html(self):
        urls = ImprovAsylumEventExtractor.extract_tixr_urls("")
        assert urls == []
