"""Unit tests for RevolutionHallExtractor: HTML parsing, event-wrapper filtering,
field extraction, and status detection."""

from laughtrack.scrapers.implementations.venues.revolution_hall.extractor import (
    RevolutionHallExtractor,
)


def _event_div(
    name: str = "Shane Gillis",
    ticket_url: str = "https://www.etix.com/ticket/p/77680474/shane-gillis",
    date_text: str = "Fri, April 10th, 2026",
    doors_iso: str = "2026-04-11T01:00:00Z",
    time_text: str = "Doors: 6PM / Show: 7PM",
    age_text: str = "All Ages",
    status_class: str = "event-status--on-sale",
    image_src: str = "https://cdn.etix.com/images/poster.jpg",
    hall_class: str = "revolution-hall",
) -> str:
    """Build a minimal event-wrapper HTML block matching the Revolution Hall structure."""
    status_link = f'<a class="btn {status_class}">Tickets</a>' if status_class else ""
    img_tag = f'<img src="{image_src}" />' if image_src else ""
    age_span = f'<span class="event-age-restriction">{age_text}</span>' if age_text else ""
    return f"""
    <div class="event-wrapper {hall_class}">
      <div class="event">
        <h3 itemprop="name"><a href="{ticket_url}">{name}</a></h3>
        <span class="event-date--full">{date_text}</span>
        <span class="event-doors-showtime" data-event-doors="{doors_iso}">{time_text}</span>
        {age_span}
        {status_link}
        {img_tag}
      </div>
    </div>"""


def _page_html(*event_divs: str) -> str:
    """Wrap event divs in a minimal page."""
    body = "\n".join(event_divs)
    return f"<html><body>{body}</body></html>"


# ---------------------------------------------------------------------------
# extract_events — happy path
# ---------------------------------------------------------------------------


class TestExtractEvents:
    def test_single_event(self):
        html = _page_html(_event_div())
        events = RevolutionHallExtractor.extract_events(html)
        assert len(events) == 1

    def test_event_fields(self):
        html = _page_html(_event_div())
        e = RevolutionHallExtractor.extract_events(html)[0]
        assert e.name == "Shane Gillis"
        assert e.ticket_url == "https://www.etix.com/ticket/p/77680474/shane-gillis"
        assert e.date_text == "Fri, April 10th, 2026"
        assert e.doors_iso == "2026-04-11T01:00:00Z"
        assert e.time_text == "Doors: 6PM / Show: 7PM"
        assert e.age_restriction == "All Ages"
        assert e.image_url == "https://cdn.etix.com/images/poster.jpg"

    def test_multiple_events(self):
        html = _page_html(
            _event_div(name="Show A"),
            _event_div(name="Show B"),
            _event_div(name="Show C"),
        )
        events = RevolutionHallExtractor.extract_events(html)
        assert [e.name for e in events] == ["Show A", "Show B", "Show C"]


# ---------------------------------------------------------------------------
# _is_main_hall — venue filtering
# ---------------------------------------------------------------------------


class TestIsMainHall:
    def test_excludes_show_bar(self):
        """Show Bar events (class 'show-bar-at-revolution-hall') are excluded."""
        html = _page_html(_event_div(hall_class="show-bar-at-revolution-hall"))
        events = RevolutionHallExtractor.extract_events(html)
        assert len(events) == 0

    def test_includes_main_hall(self):
        html = _page_html(_event_div(hall_class="revolution-hall"))
        events = RevolutionHallExtractor.extract_events(html)
        assert len(events) == 1

    def test_excludes_unknown_hall(self):
        """Wrapper without 'revolution-hall' class is excluded."""
        html = _page_html(_event_div(hall_class="other-venue"))
        events = RevolutionHallExtractor.extract_events(html)
        assert len(events) == 0

    def test_mixed_venues(self):
        """Only main hall events are returned from a mix."""
        html = _page_html(
            _event_div(name="Main Hall Show", hall_class="revolution-hall"),
            _event_div(name="Bar Show", hall_class="show-bar-at-revolution-hall"),
        )
        events = RevolutionHallExtractor.extract_events(html)
        assert len(events) == 1
        assert events[0].name == "Main Hall Show"


# ---------------------------------------------------------------------------
# Status detection
# ---------------------------------------------------------------------------


class TestStatusDetection:
    def test_on_sale(self):
        html = _page_html(_event_div(status_class="event-status--on-sale"))
        e = RevolutionHallExtractor.extract_events(html)[0]
        assert e.status == "on_sale"

    def test_sold_out(self):
        html = _page_html(_event_div(status_class="event-status--sold-out"))
        e = RevolutionHallExtractor.extract_events(html)[0]
        assert e.status == "sold_out"

    def test_not_on_sale(self):
        html = _page_html(_event_div(status_class="event-status--not-on-sale"))
        e = RevolutionHallExtractor.extract_events(html)[0]
        assert e.status == "not_on_sale"

    def test_no_status_button_defaults_on_sale(self):
        html = _page_html(_event_div(status_class=""))
        e = RevolutionHallExtractor.extract_events(html)[0]
        assert e.status == "on_sale"


# ---------------------------------------------------------------------------
# Edge cases / missing fields
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_html(self):
        assert RevolutionHallExtractor.extract_events("<html></html>") == []

    def test_missing_title_skips_event(self):
        html = _page_html("""
        <div class="event-wrapper revolution-hall">
          <div class="event">
            <span class="event-date--full">Fri, April 10th, 2026</span>
          </div>
        </div>""")
        assert RevolutionHallExtractor.extract_events(html) == []

    def test_missing_date_and_doors_iso_skips_event(self):
        html = _page_html(_event_div(date_text="", doors_iso=""))
        assert RevolutionHallExtractor.extract_events(html) == []

    def test_missing_event_inner_div_skips(self):
        """Wrapper without inner div.event is skipped."""
        html = _page_html("""
        <div class="event-wrapper revolution-hall">
          <h3 itemprop="name"><a href="https://etix.com">Show</a></h3>
        </div>""")
        assert RevolutionHallExtractor.extract_events(html) == []

    def test_missing_ticket_url_skips(self):
        html = _page_html(_event_div(ticket_url=""))
        assert RevolutionHallExtractor.extract_events(html) == []

    def test_no_image(self):
        html = _page_html(_event_div(image_src=""))
        e = RevolutionHallExtractor.extract_events(html)[0]
        assert e.image_url == ""

    def test_no_age_restriction(self):
        html = _page_html(_event_div(age_text=""))
        e = RevolutionHallExtractor.extract_events(html)[0]
        assert e.age_restriction == ""

    def test_doors_iso_only_no_date_text(self):
        """Event with doors_iso but no date_text is still extracted."""
        html = _page_html(_event_div(date_text="", doors_iso="2026-04-11T01:00:00Z"))
        events = RevolutionHallExtractor.extract_events(html)
        assert len(events) == 1

    def test_date_text_only_no_doors_iso(self):
        """Event with date_text but no doors_iso is still extracted."""
        html = _page_html(_event_div(doors_iso="", date_text="Fri, April 10th, 2026"))
        events = RevolutionHallExtractor.extract_events(html)
        assert len(events) == 1
