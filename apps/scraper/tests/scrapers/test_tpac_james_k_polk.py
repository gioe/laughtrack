"""Tests for the TPAC James K. Polk Theater comedy scraper."""

from laughtrack.scrapers.implementations.venues.tpac_james_k_polk.extractor import (
    TpacJamesKPolkExtractor,
)

CATEGORY_URL = (
    "https://www.tpac.org/multicategory/category_json/0"
    "?category=5&venue=4&team=0&exclude=&per_page=6&came_from_page=event-list-page"
)
DETAIL_URL = "https://www.tpac.org/events/detail/kevin-langue-2026"
TICKET_URL = "https://my.tpac.org/overview/kevin-langue"


def _category_json_payload() -> str:
    return f"""
    "<div class='event_card'>
      <a class='event_card_link' href='{DETAIL_URL}'>
        <h3 class='event_card_title'>Kevin Langue</h3>
      </a>
      <a class='button tickets' href='{TICKET_URL}'>Tickets</a>
    </div>
    <div class='event_card'>
      <a class='event_card_link' href='/events/detail/jk-live-2026'>
        <h3 class='event_card_title'>JK LIVE!</h3>
      </a>
    </div>"
    """


def _detail_page() -> str:
    return f"""
    <html>
      <body>
        <main>
          <div class="event_heading">
            <h1 class="title">Kevin Langue</h1>
          </div>
          <aside>
            <div class="sidebar_event_date"><span>Jun 13, 2026</span></div>
            <div class="sidebar_event_starts"><span>7:30 PM</span></div>
            <div class="sidebar_event_venue"><span>James K. Polk Theater</span></div>
          </aside>
          <div class="buttons">
            <a class="tickets" href="{TICKET_URL}?utm_source=tpac">Buy Tickets</a>
          </div>
          <div class="description_wrapper">
            <p>Kevin Langue brings his comedy tour to TPAC.</p>
            <script>ignored()</script>
          </div>
        </main>
      </body>
    </html>
    """


def test_extracts_category_json_event_cards():
    events = TpacJamesKPolkExtractor.extract_category_events(
        _category_json_payload(),
        CATEGORY_URL,
    )

    assert len(events) == 2
    assert events[0].title == "Kevin Langue"
    assert events[0].detail_url == DETAIL_URL
    assert events[0].ticket_url == TICKET_URL
    assert events[1].title == "JK LIVE!"
    assert events[1].detail_url == "https://www.tpac.org/events/detail/jk-live-2026"


def test_extracts_detail_page_fields():
    event = TpacJamesKPolkExtractor.extract_category_events(
        _category_json_payload(),
        CATEGORY_URL,
    )[0]

    enriched = TpacJamesKPolkExtractor.enrich_event_from_detail_page(event, _detail_page())

    assert enriched.title == "Kevin Langue"
    assert enriched.date_str == "Jun 13, 2026"
    assert enriched.time_str == "7:30 PM"
    assert enriched.venue == "James K. Polk Theater"
    assert enriched.ticket_url.startswith(TICKET_URL)
    assert enriched.description == "Kevin Langue brings his comedy tour to TPAC."


def test_extracts_first_showing_time_when_sidebar_start_is_absent():
    event = TpacJamesKPolkExtractor.extract_category_events(
        _category_json_payload(),
        CATEGORY_URL,
    )[1]
    html = """
    <html>
      <body>
        <div class="event_heading"><h1 class="title">JK LIVE!</h1></div>
        <ul class="eventDetailList">
          <li class="item sidebar_event_date">
            <span><span class="m-date__month">June </span><span class="m-date__day">20</span><span class="m-date__year">, 2026</span></span>
          </li>
          <li class="item sidebar_event_venue"><span>Polk Theater</span></li>
        </ul>
        <div class="showings_wrapper">
          <span class="time cell">3:00 PM</span>
        </div>
        <div class="event_description"><p>Sketch comedy from JK Studios.</p></div>
      </body>
    </html>
    """

    enriched = TpacJamesKPolkExtractor.enrich_event_from_detail_page(event, html)

    assert enriched.date_str == "June 20, 2026"
    assert enriched.time_str == "3:00 PM"
    assert enriched.description == "Sketch comedy from JK Studios."
