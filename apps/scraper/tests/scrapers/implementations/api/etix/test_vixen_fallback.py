import json

import pytest

URL = 'https://vixenmchenry.com/event/comedy-example/'
TITLE = 'FREE STAND UP COMEDY NIGHT FEATURING: EXAMPLE'


def detail(**changes):
    event = {'@type': 'Event', 'name': TITLE, 'url': URL, 'startDate': '2026-10-07T19:30:00-05:00',
             'eventStatus': 'https://schema.org/EventScheduled'}
    event.update(changes)
    return f'''<script type="application/ld+json">{json.dumps([event])}</script><h1>{TITLE}</h1>
    <div class="et_pb_post_content"><h2>{TITLE}<br>WEDNESDAY, OCTOBER 7TH<br>
    DOORS OPEN AT 7:30PM<br>SHOW STARTS AT 8:00PM</h2></div>
    <span class="ecs-eventDate"><span class="decm_date">10/07/2026</span></span>'''


def test_explicit_showtime_overrides_correlated_doors_time():
    from laughtrack.scrapers.implementations.api.etix.public_vixen import verify_detail
    event = verify_detail(detail(), URL)
    assert event.start_date == '2026-10-07T20:00:00-05:00'
    assert event.ticket_price == 0


@pytest.mark.parametrize('changes', [
    {'url': URL + 'wrong/'}, {'name': 'A CONCERT'}, {'startDate': '2027-10-07T19:30:00-05:00'},
    {'startDate': '2026-10-07T18:30:00-05:00'}, {'eventStatus': 'https://schema.org/EventCancelled'},
])
def test_conflicting_identity_or_doors_rejected(changes):
    from laughtrack.scrapers.implementations.api.etix.public_vixen import verify_detail
    assert verify_detail(detail(**changes), URL) is None


@pytest.mark.parametrize('replacement', ['', 'DOORS OPEN AT 8:00PM'])
def test_no_showtime_never_uses_doors(replacement):
    from laughtrack.scrapers.implementations.api.etix.public_vixen import verify_detail
    assert verify_detail(detail().replace('SHOW STARTS AT 8:00PM', replacement), URL) is None


def test_split_main_headings_and_changed_explicit_showtime():
    from laughtrack.scrapers.implementations.api.etix.public_vixen import verify_detail
    html = detail().replace('DOORS OPEN', '</h2><h2>DOORS OPEN').replace('SHOW STARTS AT 8:00PM', 'SHOW STARTS AT 8:15PM')
    assert verify_detail(html, URL).start_date == '2026-10-07T20:15:00-05:00'


def test_related_event_cannot_supply_missing_main_showtime():
    from laughtrack.scrapers.implementations.api.etix.public_vixen import verify_detail
    html = detail().replace('SHOW STARTS AT 8:00PM', '') + '<aside>SHOW STARTS AT 8:00PM</aside>'
    assert verify_detail(html, URL) is None


def test_unrelated_structured_event_does_not_replace_matching_event():
    from laughtrack.scrapers.implementations.api.etix.public_vixen import verify_detail
    unrelated = {'@graph': [{'@type': 'Event', 'url': 'https://vixenmchenry.com/event/concert/',
                           'name': 'Concert', 'startDate': '2027-01-01T20:00:00-06:00'}]}
    html = detail() + f'<script type="application/ld+json">{json.dumps(unrelated)}</script>'
    assert verify_detail(html, URL).start_date.startswith('2026-10-07')


@pytest.mark.asyncio
async def test_only_owned_comedy_links_discovered_and_partial_failure_retained():
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from laughtrack.scrapers.implementations.api.etix.public_vixen import fetch_highlights
    other = 'https://vixenmchenry.com/event/pat-tomasulo/'
    home = f'<a href="{URL}">{TITLE}</a><a href="{other}">Pat Tomasulo, Comedian</a>'
    home += '<a href="https://vixenmchenry.com/event/rock-band/">Rock Band</a>'
    home += '<a href="https://evil.example/event/comedy/">Comedy</a>'
    fetch = AsyncMock(side_effect=[home, detail(), RuntimeError('blocked')])
    events = await fetch_highlights(fetch, SimpleNamespace(id=9074, timezone='America/Chicago'))
    assert len(events) == 1
    assert fetch.await_count == 3


@pytest.mark.asyncio
async def test_vixen_dispatcher_keeps_blocked_diagnostics_with_verified_inventory():
    from unittest.mock import AsyncMock
    from laughtrack.core.entities.club.model import Club, ScrapingSource
    from laughtrack.scrapers.implementations.api.etix.scraper import EtixScraper
    from laughtrack.foundation.infrastructure.http.diagnostics import ScrapeDiagnostics, bind_diagnostics, reset_diagnostics
    club = Club(id=9074, name='The Vixen', address='1208 N Green St', website='https://vixenmchenry.com/',
                popularity=0, zip_code='60050', phone_number='', visible=True, timezone='America/Chicago',
                city='McHenry', state='IL')
    club.active_scraping_source = ScrapingSource(id=5945, club_id=9074, platform='etix', scraper_key='etix',
                                               source_url='https://www.etix.com/ticket/v/28278/the-vixen')
    scraper = EtixScraper(club)
    scraper._fetch_etix_html = AsyncMock(side_effect=RuntimeError('blocked'))
    scraper.fetch_html_bare = AsyncMock(side_effect=[f'<a href="{URL}">{TITLE}</a>', detail()])
    diagnostics = ScrapeDiagnostics()
    token = bind_diagnostics(diagnostics)
    try:
        targets = await scraper.collect_scraping_targets()
        result = await scraper.get_data(targets[0])
    finally:
        reset_diagnostics(token)
    assert len(result.event_list) == 1
    assert diagnostics.fetches_failed > 0
    assert diagnostics.scrape_errors
