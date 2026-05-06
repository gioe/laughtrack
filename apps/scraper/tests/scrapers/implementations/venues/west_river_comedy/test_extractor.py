from laughtrack.scrapers.implementations.venues.west_river_comedy.extractor import (
    extract_event_urls,
    extract_pagination_urls,
)


def test_extract_event_urls_deduplicates_detail_links_and_skips_select_date():
    html = """
    <a href="/events/westrivercomedyclub/2196315">Details</a>
    <a href="/events/westrivercomedyclub/2196315">Buy tickets</a>
    <a href="/events/westrivercomedyclub/2160756/select-date?modal_widget=true&amp;widget=true">Select date</a>
    <a href="https://www.tickettailor.com/events/westrivercomedyclub/2160756">Details</a>
    <a href="https://www.westrivercomedy.com/seating">Seating</a>
    """

    assert extract_event_urls(html, "https://www.tickettailor.com/events/westrivercomedyclub") == [
        "https://www.tickettailor.com/events/westrivercomedyclub/2196315",
        "https://www.tickettailor.com/events/westrivercomedyclub/2160756",
    ]


def test_extract_pagination_urls_keeps_listing_pages_only():
    html = """
    <a href="/events/westrivercomedyclub?page=2" rel="next">Next</a>
    <a href="/events/westrivercomedyclub/2196315" class="pagination-link">Event</a>
    <a href="https://www.example.com/events/westrivercomedyclub?page=3" rel="next">Other host</a>
    """

    assert extract_pagination_urls(
        html,
        "https://www.tickettailor.com/events/westrivercomedyclub",
    ) == ["https://www.tickettailor.com/events/westrivercomedyclub?page=2"]
