"""Unit tests for TheMoonExtractor: HTML parsing, field extraction, and edge cases."""

from laughtrack.scrapers.implementations.venues.the_moon.extractor import (
    TheMoonExtractor,
)


def _event_card(
    title: str = "Rob Schneider",
    date: str = "Sat, May 30, 2026",
    time: str = "Door Time Is: 6:30 pm",
    ticket_url: str = "https://www.etix.com/ticket/p/37927456/rob-schneider",
) -> str:
    """Build a minimal rhp-events card fragment."""
    time_span = f'<span class="rhp-event__time-text">{time}</span>' if time else ""
    ticket_link = f'<a href="{ticket_url}">Buy Tickets</a>' if ticket_url else ""
    return f"""
    <div class="eventWrapper rhpSingleEvent">
      <h2 class="rhp-event__title">{title}</h2>
      <div class="singleEventDate">{date}</div>
      {time_span}
      {ticket_link}
    </div>"""


def _page_html(*cards: str) -> str:
    """Wrap card fragments with the split marker so extract_events can parse them."""
    body = "<!-- Event List Wrapper -->".join(["<html><body>"] + list(cards))
    return body + "</body></html>"


# ---------------------------------------------------------------------------
# extract_events — happy path
# ---------------------------------------------------------------------------


class TestExtractEvents:
    def test_single_event(self):
        html = _page_html(_event_card())
        events = TheMoonExtractor.extract_events(html)
        assert len(events) == 1

    def test_event_fields(self):
        html = _page_html(_event_card())
        e = TheMoonExtractor.extract_events(html)[0]
        assert e.title == "Rob Schneider"
        assert e.date_str == "Sat, May 30, 2026"
        assert e.time_str == "Door Time Is: 6:30 pm"
        assert e.ticket_url == "https://www.etix.com/ticket/p/37927456/rob-schneider"

    def test_multiple_events(self):
        html = _page_html(
            _event_card(title="Show A"),
            _event_card(title="Show B"),
            _event_card(title="Show C"),
        )
        events = TheMoonExtractor.extract_events(html)
        assert [e.title for e in events] == ["Show A", "Show B", "Show C"]


# ---------------------------------------------------------------------------
# HTML entity / tag handling
# ---------------------------------------------------------------------------


class TestHtmlHandling:
    def test_strips_inner_html_tags_from_title(self):
        html = _page_html(_event_card(title="<strong>Rob</strong> Schneider"))
        e = TheMoonExtractor.extract_events(html)[0]
        assert e.title == "Rob Schneider"

    def test_decodes_html_entities_in_title(self):
        html = _page_html(_event_card(title="Rock &amp; Roll Comedy"))
        e = TheMoonExtractor.extract_events(html)[0]
        assert e.title == "Rock & Roll Comedy"

    def test_strips_tags_from_date(self):
        html = _page_html(_event_card(date="<span>Sat, May 30, 2026</span>"))
        e = TheMoonExtractor.extract_events(html)[0]
        assert e.date_str == "Sat, May 30, 2026"


# ---------------------------------------------------------------------------
# Edge cases / missing fields
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_html(self):
        assert TheMoonExtractor.extract_events("") == []

    def test_no_cards(self):
        assert TheMoonExtractor.extract_events("<html><body></body></html>") == []

    def test_missing_title_skips_card(self):
        card = """
        <div class="eventWrapper rhpSingleEvent">
          <div class="singleEventDate">Sat, May 30, 2026</div>
          <a href="https://www.etix.com/ticket/p/123/show">Buy</a>
        </div>"""
        html = _page_html(card)
        assert TheMoonExtractor.extract_events(html) == []

    def test_missing_date_skips_card(self):
        card = """
        <div class="eventWrapper rhpSingleEvent">
          <h2 class="rhp-event__title">Rob Schneider</h2>
          <a href="https://www.etix.com/ticket/p/123/show">Buy</a>
        </div>"""
        html = _page_html(card)
        assert TheMoonExtractor.extract_events(html) == []

    def test_missing_ticket_url_skips_card(self):
        card = """
        <div class="eventWrapper rhpSingleEvent">
          <h2 class="rhp-event__title">Rob Schneider</h2>
          <div class="singleEventDate">Sat, May 30, 2026</div>
        </div>"""
        html = _page_html(card)
        assert TheMoonExtractor.extract_events(html) == []

    def test_missing_time_still_extracts(self):
        """Time is optional — card without time span is still valid."""
        html = _page_html(_event_card(time=""))
        events = TheMoonExtractor.extract_events(html)
        assert len(events) == 1
        assert events[0].time_str == ""

    def test_mixed_valid_and_invalid_cards(self):
        valid = _event_card(title="Valid Show")
        invalid = """
        <div class="eventWrapper rhpSingleEvent">
          <div class="singleEventDate">Sat, May 30, 2026</div>
        </div>"""
        html = _page_html(valid, invalid)
        events = TheMoonExtractor.extract_events(html)
        assert len(events) == 1
        assert events[0].title == "Valid Show"
