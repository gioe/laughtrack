"""
Unit tests for BitTheaterExtractor (listing extraction, category filtering,
pagination detection, and detail price extraction).
"""

from laughtrack.core.entities.event.the_bit_theater import is_comedy_relevant
from laughtrack.scrapers.implementations.venues.the_bit_theater.extractor import (
    BitTheaterExtractor,
)


# ---------------------------------------------------------------------------
# Helper: build minimal Odoo listing HTML
# ---------------------------------------------------------------------------

def _article(
    title: str = "Test Show",
    start_date: str = "2026-04-17T01:00:00",
    badges: list[str] | None = None,
    href: str = "/event/test-show-123/",
) -> str:
    """Build a single Odoo article card with its parent <a> wrapper."""
    badge_html = ""
    if badges:
        badge_html = "\n".join(
            f'<span class="badge">{b}</span>' for b in badges
        )
    return f"""
    <a class="text-decoration-none text-reset" href="{href}" data-publish="on">
      <article itemscope itemtype="http://schema.org/Event" class="h-100 card">
        <meta content="{start_date}" itemprop="startDate"/>
        <div id="event_details">
          {badge_html}
          <h5 class="card-title my-2"><span itemprop="name">{title}</span></h5>
        </div>
      </article>
    </a>
    """


def _listing_page(articles_html: str, next_page_url: str | None = None) -> str:
    """Wrap article cards into a full listing page."""
    pagination = ""
    if next_page_url:
        pagination = f"""
        <ul class="pagination m-0">
          <li class="page-item active"><a class="page-link" href="/event">1</a></li>
          <li class="page-item"><a class="page-link" href="{next_page_url}">2</a></li>
        </ul>
        """
    return f"<html><body>{articles_html}{pagination}</body></html>"


def _detail_page(price: str | None = None) -> str:
    """Build a minimal Odoo event detail page."""
    price_html = ""
    if price is not None:
        price_html = f"""
        <div id="o_wevent_tickets">
          <span itemprop="price">{price}</span>
        </div>
        """
    return f"<html><body>{price_html}</body></html>"


# ---------------------------------------------------------------------------
# is_comedy_relevant
# ---------------------------------------------------------------------------

class TestIsComedyRelevant:
    def test_standup_is_relevant(self):
        assert is_comedy_relevant(["Stand-up"]) is True

    def test_short_form_is_relevant(self):
        assert is_comedy_relevant(["Short Form"]) is True

    def test_long_form_is_relevant(self):
        assert is_comedy_relevant(["Long Form"]) is True

    def test_improv_is_relevant(self):
        assert is_comedy_relevant(["Improv"]) is True

    def test_sketch_is_relevant(self):
        assert is_comedy_relevant(["Sketch"]) is True

    def test_play_is_excluded(self):
        assert is_comedy_relevant(["Play"]) is False

    def test_class_is_excluded(self):
        assert is_comedy_relevant(["Class"]) is False

    def test_burlesque_is_excluded(self):
        assert is_comedy_relevant(["Burlesque"]) is False

    def test_exclude_overrides_include(self):
        assert is_comedy_relevant(["Stand-up", "Class"]) is False

    def test_empty_list_is_not_relevant(self):
        assert is_comedy_relevant([]) is False

    def test_unknown_category_is_not_relevant(self):
        assert is_comedy_relevant(["Fox Country Players"]) is False

    def test_case_insensitive(self):
        assert is_comedy_relevant(["STAND-UP"]) is True
        assert is_comedy_relevant(["PLAY"]) is False


# ---------------------------------------------------------------------------
# extract_listing_events
# ---------------------------------------------------------------------------

class TestExtractListingEvents:
    def test_extracts_comedy_events(self):
        html = _listing_page(
            _article("Thursday Triple Threat", badges=["Short Form", "Long Form"])
            + _article("Stand Up @ The Bit", badges=["Stand-up"])
        )
        events, next_url = BitTheaterExtractor.extract_listing_events(html)
        assert len(events) == 2
        assert events[0].title == "Thursday Triple Threat"
        assert events[1].title == "Stand Up @ The Bit"
        assert next_url is None

    def test_filters_non_comedy_events(self):
        html = _listing_page(
            _article("Improv Show", badges=["Short Form"])
            + _article("The Last Flapper", badges=["Play"])
            + _article("Tuesday Drop-IN", badges=["Class"])
        )
        events, _ = BitTheaterExtractor.extract_listing_events(html)
        assert len(events) == 1
        assert events[0].title == "Improv Show"

    def test_extracts_start_date(self):
        html = _listing_page(
            _article("Show", start_date="2026-04-17T01:00:00", badges=["Stand-up"])
        )
        events, _ = BitTheaterExtractor.extract_listing_events(html)
        assert events[0].start_datetime_utc == "2026-04-17T01:00:00"

    def test_constructs_full_event_url(self):
        html = _listing_page(
            _article("Show", href="/event/my-show-123/", badges=["Stand-up"])
        )
        events, _ = BitTheaterExtractor.extract_listing_events(html)
        assert events[0].event_url == "https://www.bitimprov.org/event/my-show-123/"

    def test_strips_register_suffix_from_url(self):
        html = _listing_page(
            _article("Show", href="/event/my-show-123/register", badges=["Stand-up"])
        )
        events, _ = BitTheaterExtractor.extract_listing_events(html)
        assert events[0].event_url == "https://www.bitimprov.org/event/my-show-123/"

    def test_empty_html_returns_empty(self):
        events, next_url = BitTheaterExtractor.extract_listing_events("")
        assert events == []
        assert next_url is None

    def test_no_articles_returns_empty(self):
        html = "<html><body><p>No events</p></body></html>"
        events, _ = BitTheaterExtractor.extract_listing_events(html)
        assert events == []

    def test_article_missing_start_date_skipped(self):
        html = _listing_page("""
        <a href="/event/no-date-123/">
          <article itemscope itemtype="http://schema.org/Event" class="h-100 card">
            <span class="badge">Stand-up</span>
            <span itemprop="name">No Date Show</span>
          </article>
        </a>
        """)
        events, _ = BitTheaterExtractor.extract_listing_events(html)
        assert events == []

    def test_article_missing_name_skipped(self):
        html = _listing_page("""
        <a href="/event/no-name-123/">
          <article itemscope itemtype="http://schema.org/Event" class="h-100 card">
            <meta content="2026-04-17T01:00:00" itemprop="startDate"/>
            <span class="badge">Stand-up</span>
          </article>
        </a>
        """)
        events, _ = BitTheaterExtractor.extract_listing_events(html)
        assert events == []


# ---------------------------------------------------------------------------
# Pagination detection
# ---------------------------------------------------------------------------

class TestPaginationDetection:
    def test_detects_next_page(self):
        html = _listing_page(
            _article("Show", badges=["Stand-up"]),
            next_page_url="/event/page/2?search=&date=scheduled",
        )
        _, next_url = BitTheaterExtractor.extract_listing_events(html)
        assert next_url == "https://www.bitimprov.org/event/page/2?search=&date=scheduled"

    def test_no_pagination_returns_none(self):
        html = _listing_page(_article("Show", badges=["Stand-up"]))
        _, next_url = BitTheaterExtractor.extract_listing_events(html)
        assert next_url is None

    def test_last_page_returns_none(self):
        html = """<html><body>
        <ul class="pagination m-0">
          <li class="page-item"><a class="page-link" href="/event">1</a></li>
          <li class="page-item active"><a class="page-link" href="/event/page/2">2</a></li>
          <li class="page-item disabled"><a class="page-link"><span class="oi oi-chevron-right"></span></a></li>
        </ul>
        </body></html>"""
        _, next_url = BitTheaterExtractor.extract_listing_events(html)
        assert next_url is None


# ---------------------------------------------------------------------------
# extract_detail_price
# ---------------------------------------------------------------------------

class TestExtractDetailPrice:
    def test_extracts_price_from_itemprop(self):
        html = _detail_page("25.0")
        price = BitTheaterExtractor.extract_detail_price(html)
        assert price == 25.0

    def test_extracts_price_from_dollar_sign_fallback(self):
        html = """<html><body>
        <div id="o_wevent_tickets">
          <span class="badge">$20.00</span>
        </div>
        </body></html>"""
        price = BitTheaterExtractor.extract_detail_price(html)
        assert price == 20.0

    def test_no_price_returns_none(self):
        html = "<html><body><p>No price info</p></body></html>"
        price = BitTheaterExtractor.extract_detail_price(html)
        assert price is None

    def test_empty_html_returns_none(self):
        price = BitTheaterExtractor.extract_detail_price("")
        assert price is None

    def test_non_numeric_price_returns_none(self):
        html = _detail_page("free")
        price = BitTheaterExtractor.extract_detail_price(html)
        assert price is None
