"""Unit tests for the Hennepin Arts scraper."""

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.hennepin_arts.extractor import (
    extract_hits,
    extract_performances_from_detail,
    slug_from_hit,
)


def _club() -> Club:
    source = ScrapingSource(
        id=1,
        club_id=9001,
        platform="custom",
        scraper_key="hennepin_arts",
        source_url="https://hennepinarts.org/events?refinementList%5Bgenre%5D%5B0%5D=Comedy",
    )
    return Club(
        id=9001,
        name="Hennepin Arts",
        address="900 Hennepin Ave",
        website="https://hennepinarts.org",
        popularity=0,
        zip_code="55403",
        phone_number="",
        visible=True,
        timezone="America/Chicago",
        scraping_sources=[source],
        active_scraping_source=source,
    )


ALGOLIA_PAYLOAD = {
    "results": [
        {
            "hits": [
                {
                    "name": "Aries Spears",
                    "slug": "aries-spears-2027",
                    "venue": "State Theatre",
                    "genre": "Comedy",
                }
            ],
            "nbPages": 3,
        }
    ]
}


# Far-future sentinel dates (2036 — pre-2037 because to_show localizes via pytz,
# per convention 309) so the to_show past-drop never rots this fixture (TASK-3586).
# 2036-01-30 is a Wednesday, 2036-01-31 a Thursday.
DETAIL_HTML = """
<script>
{"fields":{"title":"Event > Aries Spears > Jan 30, 2036 > Wed Eve",
"startDate":"2036-01-30T19:00",
"ticketsUrl":"https://www.ticketmaster.com/event/06006495CB0290D5",
"ticketsButtonText":"Buy Tickets"}}
["Event > Aries Spears > Jan 30, 2036 > Wed Eve",
"2036-01-30T19:00",
"https://www.ticketmaster.com/event/06006495CB0290D5",
"Buy Tickets"]
["Event > Other Show > Jan 31, 2036 > Thu Eve",
"2036-01-31T19:00",
"https://www.ticketmaster.com/event/other",
"Buy Tickets"]
{"description":{"content":[{"value":"Aries brought a fresh hip style."}]},"artistWebsite":"https://ariesspears.com/"}
</script>
"""


def test_extract_hits_reads_algolia_multi_query_result():
    hits, nb_pages = extract_hits(ALGOLIA_PAYLOAD)

    assert nb_pages == 3
    assert slug_from_hit(hits[0]) == "aries-spears-2027"


def test_extract_detail_performance_builds_event_and_show():
    events = extract_performances_from_detail(
        DETAIL_HTML,
        title="Aries Spears",
        slug="aries-spears-2027",
        venue="State Theatre",
    )

    assert len(events) == 1
    event = events[0]
    assert event.start_date == "2036-01-30T19:00"
    assert event.ticket_url == "https://www.ticketmaster.com/event/06006495CB0290D5"
    assert event.venue == "State Theatre"

    show = event.to_show(_club())
    assert show is not None
    assert show.name == "Aries Spears"
    assert show.room == "State Theatre"
    assert show.tickets[0].purchase_url == "https://www.ticketmaster.com/event/06006495CB0290D5"
