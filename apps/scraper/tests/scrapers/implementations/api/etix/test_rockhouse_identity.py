"""Canonical Rockhouse individual posts adjudicate corrupted series labels."""

import json
from unittest.mock import AsyncMock

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.etix.scraper import EtixScraper

SOURCE = "https://www.comedycastle.com/events/"
ADDRESS = (
    '<script type="application/ld+json">'
    + json.dumps(
        {
            "@type": "Place",
            "@id": "https://www.comedycastle.com/#place",
            "address": {
                "streetAddress": "310 South Troy Street",
                "addressLocality": "Royal Oak",
                "addressRegion": "MI",
                "postalCode": "48067",
            },
        }
    )
    + "</script>"
)
TICKET = "https://www.etix.com/ticket/p/62115951/mike-cronin?partner_id=100"
CANONICAL = "https://www.comedycastle.com/event/mike-cronin/mark-ridleys-comedy-castle/royal-oak/"


def venue():
    club = Club(
        id=4756,
        name="Mark Ridley's Comedy Castle",
        address="310 S Troy St, Royal Oak, MI 48067",
        website=SOURCE,
        popularity=0,
        zip_code="48067",
        phone_number="",
        visible=True,
        timezone="America/Detroit",
        city="Royal Oak",
        state="MI",
    )
    club.active_scraping_source = ScrapingSource(
        id=6960, club_id=4756, platform="etix", scraper_key="etix", source_url=SOURCE
    )
    return club


def card(title, post=34020):
    return f"""<div class="rhp-event__single-series--list"><h2 class="rhpEventHeader"><a href="{SOURCE}{title}">{title}</a></h2>
    <li class="rhp-event-series-individual"><span class="rhp-event-series-date">Oct 15</span>
    <span class="rhp-event-series-time">Show | 7:30 pm</span><span id="ctaspan-{post}"><a href="{TICKET}">Tickets</a></span></li></div>"""


def detail(**changes):
    event = {
        "@type": "Event",
        "name": "MIKE CRONIN",
        "startDate": "2026-10-15T19:30:00-0400",
        "url": CANONICAL,
        "location": {"name": "Mark Ridley&#8217;s Comedy Castle", "address": "310 South Troy Street, Royal Oak, "},
        "offers": {"url": TICKET, "price": 0},
    }
    event.update(changes)
    return f"""<script type="application/ld+json">{json.dumps(event)}</script>
    <div class="singleEventDetails"><h1>MIKE CRONIN</h1><span class="eventStDate">Thursday, October 15</span>
    <div class="eventDoorStartDate">Show | 7:30 pm</div><div class="eventVenue"><a class="venueLink">Mark Ridley’s Comedy Castle</a></div>
    <span id="ctaspan-34020"><a href="{TICKET}">Purchase Tickets</a></span></div>"""


@pytest.mark.asyncio
@pytest.mark.parametrize("reverse", [False, True])
async def test_individual_post_resolves_conflicting_series_identity(reverse):
    scraper = EtixScraper(venue())
    cards = [card("CAM ROWE"), card("MIKE CRONIN")]
    if reverse:
        cards.reverse()
    calendar = ADDRESS + '<div class="rhp-events-list-separator-month">October 2026</div>' + "".join(cards)
    scraper.fetch_html_bare = AsyncMock(side_effect=[calendar, detail()])
    result = await scraper._get_rockhouse_public_data(SOURCE)
    assert result is not None
    assert [(e.title, e.start_date) for e in result.event_list] == [("MIKE CRONIN", "2026-10-15T19:30:00")]
    assert result.event_list[0].ticket_price is None
    assert result.event_list[0].event_url == CANONICAL
    assert scraper.fetch_html_bare.call_args_list[1].args == ("https://www.comedycastle.com/?p=34020",)


def verified(html):
    from laughtrack.scrapers.implementations.api.etix.rockhouse_identity import verify_individual_post

    return verify_individual_post(
        html,
        "34020",
        "62115951",
        [{"start_date": "2026-10-15T19:30:00"}],
        SOURCE,
        venue(),
        ("310 south troy street", "royal oak"),
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"offers": {"url": TICKET.replace("62115951", "99999999")}},
        {"offers": {"url": "https://evil.example/ticket/p/62115951/"}},
        {"startDate": "2026-10-15T20:30:00-0400"},
        {"startDate": "2026-10-15T19:30:00-0500"},
        {"startDate": "2026-10-15T19:30:00"},
        {"name": "Different event"},
        {"url": "https://evil.example/event/mike-cronin/"},
        {"url": SOURCE},
        {"location": {"name": "Another venue", "address": "310 South Troy Street, Royal Oak, "}},
        {"location": {"name": "Mark Ridley's Comedy Castle", "address": "269 E Fourth Street, Royal Oak"}},
        {"location": {"name": "Mark Ridley's Comedy Castle", "address": "310 South Troy Street, Chicago"}},
    ],
)
def test_disagreeing_structured_evidence_never_resolves(changes):
    assert verified(detail(**changes)) is None


@pytest.mark.parametrize(
    "old,new",
    [
        ("<h1>MIKE CRONIN</h1>", "<h1>CAM ROWE</h1>"),
        ("Show | 7:30 pm", "Doors | 7:30 pm"),
        ("Show | 7:30 pm", "Show | 8:30 pm"),
        ("Thursday, October 15", "Friday, October 16"),
        ("ctaspan-34020", "ctaspan-999"),
        ("singleEventDetails", "singleEventSection"),
        ('class="venueLink">Mark Ridley’s Comedy Castle', 'class="venueLink">Different venue'),
    ],
)
def test_visible_evidence_must_corroborate_primary_event(old, new):
    assert verified(detail().replace(old, new)) is None


def test_multiple_primary_events_are_ambiguous():
    assert verified(detail() + detail()) is None


def test_canonical_title_can_correct_both_corrupt_series_titles():
    corrected = detail(name="THE NIGHT BEFORE THANKSGIVING COMEDY SPECIAL").replace(
        "<h1>MIKE CRONIN</h1>", "<h1>THE NIGHT BEFORE THANKSGIVING COMEDY SPECIAL</h1>"
    )
    assert verified(corrected).title == "THE NIGHT BEFORE THANKSGIVING COMEDY SPECIAL"


def test_detail_price_uses_explicit_main_display_not_zero_jsonld_or_nested_listing():
    assert verified(detail()).ticket_price is None
    displayed = detail().replace("</h1>", '</h1><div class="eventCost">$26.70</div>')
    assert verified(displayed).ticket_price == 26.7
    nested = detail() + '<div class="singleEventSection"><div class="eventCost">$99</div><h1>OTHER EVENT</h1></div>'
    assert verified(nested).ticket_price is None


@pytest.mark.asyncio
@pytest.mark.parametrize("second_post", [None, 99999])
async def test_missing_or_ambiguous_post_mapping_does_not_fetch(second_post):
    from laughtrack.scrapers.implementations.api.etix.rockhouse import extract_rockhouse_events_with_conflicts
    from laughtrack.scrapers.implementations.api.etix.rockhouse_identity import resolve_rockhouse_conflicts
    from datetime import date

    second = card("MIKE CRONIN", second_post)
    if second_post is None:
        second = second.replace('id="ctaspan-None"', "")
    html = ADDRESS + card("CAM ROWE") + second
    _, conflicts = extract_rockhouse_events_with_conflicts(html, date(2026, 10, 1))
    fetch = AsyncMock(return_value=detail())
    resolved, remaining = await resolve_rockhouse_conflicts(html, SOURCE, venue(), conflicts, fetch)
    assert resolved == []
    assert remaining == conflicts
    fetch.assert_not_called()


@pytest.mark.asyncio
async def test_partial_resolution_preserves_safe_rows_and_blocks_reconciliation():
    from types import SimpleNamespace
    from laughtrack.foundation.infrastructure.http.diagnostics import (
        ScrapeDiagnostics,
        bind_diagnostics,
        reset_diagnostics,
    )
    from laughtrack.utilities.domain.scraper.result import ScrapingResultProcessor

    calendar = ADDRESS + '<div class="rhp-events-list-separator-month">October 2026</div>'
    calendar += card("CAM ROWE") + card("MIKE CRONIN")
    calendar += (card("FIRST LABEL", 34022) + card("SECOND LABEL", 34022)).replace("62115951", "22222222")
    calendar += card("SAFE SHOW", 555).replace("62115951", "11111111")

    async def fetch(url):
        return calendar if url == SOURCE else detail() if url.endswith("34020") else "<html>Access denied</html>"

    scraper = EtixScraper(venue())
    scraper.fetch_html_bare = fetch
    scraper.rate_limiter = SimpleNamespace(await_if_needed=AsyncMock())
    diagnostics = ScrapeDiagnostics()
    token = bind_diagnostics(diagnostics)
    try:
        results = await scraper._fetch_all_raw_data([SOURCE])
    finally:
        reset_diagnostics(token)
    assert {event.title for event in results[0][0].event_list} == {"SAFE SHOW", "MIKE CRONIN"}
    assert diagnostics.fetches_failed == 1
    assert diagnostics.fetches_ok == 1
    assert "22222222" in diagnostics.scrape_errors[0]
    assert "62115951" not in diagnostics.scrape_errors[0]
    result = SimpleNamespace(
        error=None,
        shows=results[0][0].event_list,
        bot_block_detected=False,
        fetches_failed=diagnostics.fetches_failed,
        fetches_ok=diagnostics.fetches_ok,
    )
    assert not ScrapingResultProcessor._is_clean_for_reconciliation(result)


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["missing", "city", "state", "zip", "street"])
async def test_independent_calendar_venue_evidence_is_required(change):
    from laughtrack.scrapers.implementations.api.etix.rockhouse_identity import resolve_rockhouse_conflicts

    altered = ADDRESS
    if change == "missing":
        altered = ""
    elif change == "city":
        altered = altered.replace("Royal Oak", "Chicago")
    elif change == "state":
        altered = altered.replace('"MI"', '"IL"')
    elif change == "zip":
        altered = altered.replace("48067", "60001")
    else:
        altered = altered.replace("310 South Troy Street", "269 E Fourth Street")
    fetch = AsyncMock(return_value=detail())
    conflicts = {"62115951": [{"start_date": "2026-10-15T19:30:00"}]}
    resolved, remaining = await resolve_rockhouse_conflicts(
        altered + card("CAM ROWE"), SOURCE, venue(), conflicts, fetch
    )
    assert resolved == []
    assert remaining == conflicts
