"""Published TicketSource pagination must prove complete inventory before cleanup."""
import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.venues.comedy_clubhouse.scraper import ComedyClubhouseScraper

FIXTURES = Path(__file__).parent / 'fixtures'
URL = 'https://www.ticketsource.com/thecomedyclubhouse'


def venue():
    club = Club(id=189, name='The Comedy Clubhouse', address='1462 N Ashland Ave',
                website='https://www.thecomedyclubhouse.com', popularity=0, zip_code='60622',
                phone_number='', visible=True, timezone='America/Chicago')
    club.active_scraping_source = ScrapingSource(id=623, club_id=189, platform='custom',
                                               scraper_key='comedy_clubhouse', source_url=URL)
    return club


def captured():
    return json.loads((FIXTURES / 'page-13.json').read_text())


@pytest.mark.asyncio
async def test_complete_public_page_produces_performance_dates_and_tickets():
    page = json.loads((FIXTURES / 'page-49.json').read_text())
    scraper = ComedyClubhouseScraper(venue())
    scraper.post_form = AsyncMock(return_value=json.dumps(page))
    scraper.fetch_html = AsyncMock(side_effect=AssertionError('primary should be public pagination'))
    result = await scraper.get_data(URL)
    assert len(result.event_list) == 11
    first = result.event_list[0].to_show(venue(), enhanced=False)
    assert first.date.strftime('%Y-%m-%dT%H:%M') == page['events'][0]['performanceDateTimeMeta']
    assert first.tickets[0].purchase_url == 'https://www.ticketsource.com' + page['events'][0]['buttonLink']
    assert first.tickets[0].price is None
    assert first.show_page_url == 'https://www.ticketsource.com' + page['events'][0]['infoLinkTime']


def pages():
    return [(FIXTURES / f'page-{offset}.json').read_text() for offset in (1, 13, 25, 37, 49)]


@pytest.mark.asyncio
@pytest.mark.parametrize('proxy', [None, 'http://approved-proxy.example:8080'])
async def test_public_calendar_preserves_configured_proxy_routing(proxy, monkeypatch):
    from laughtrack.scrapers.implementations.venues.comedy_clubhouse import scraper as module
    keys = []
    def resolve(key):
        keys.append(key)
        return proxy
    monkeypatch.setattr(module.HttpClient, 'resolve_proxy_url', resolve)
    scraper = ComedyClubhouseScraper(venue())
    scraper.post_form = AsyncMock(side_effect=pages())
    result = await scraper.get_data(URL)
    assert len(result.event_list) == 59
    assert keys == ['comedy_clubhouse']
    assert all(call.kwargs['proxy'] == proxy for call in scraper.post_form.call_args_list)


@pytest.mark.asyncio
async def test_all_59_captured_performances_survive_full_pipeline():
    from types import SimpleNamespace
    from urllib.parse import parse_qs
    scraper = ComedyClubhouseScraper(venue())
    scraper.post_form = AsyncMock(side_effect=pages())
    scraper.rate_limiter = SimpleNamespace(await_if_needed=AsyncMock())
    shows = await scraper.scrape_async()
    assert len(shows) == 59
    assert len({s.tickets[0].purchase_url for s in shows}) == 59
    assert all(s.date.utcoffset().total_seconds() in {-18000, -21600} for s in shows)
    assert [parse_qs(c.args[1])['startat'] for c in scraper.post_form.call_args_list] == [['1'], ['13'], ['25'], ['37'], ['49']]


@pytest.mark.asyncio
@pytest.mark.parametrize('state', ['complete', 'verified_empty', 'blocked', 'transport', 'unknown_empty', 'missing_events_false', 'empty_error', 'missing_eof',
                                  'string_eof', 'repeated_page', 'bad_row', 'truncated', 'page_limit'])
async def test_verified_calendar_states(state, monkeypatch):
    from types import SimpleNamespace
    from laughtrack.foundation.infrastructure.http.diagnostics import ScrapeDiagnostics, bind_diagnostics, reset_diagnostics
    from laughtrack.utilities.domain.scraper.result import ScrapingResultProcessor
    from laughtrack.scrapers.implementations.venues.comedy_clubhouse import scraper as module
    responses = pages()
    if state == 'verified_empty':
        responses = [(FIXTURES / 'page-61.json').read_text()]
    elif state == 'missing_events_false':
        responses[1] = json.dumps({'eof': False})
    elif state == 'empty_error':
        responses[1] = json.dumps({'eof': True, 'error': 'blocked'})
    elif state == 'blocked':
        responses[1] = '<html>Access denied HTTP ERROR 429</html>'
    elif state == 'transport':
        responses[1] = RuntimeError('HTTP403')
    elif state == 'unknown_empty':
        responses[1] = json.dumps({'eof': False, 'events': []})
    elif state in {'missing_eof', 'string_eof'}:
        page = json.loads(responses[1]);page.pop('eof')
        if state == 'string_eof':page['eof'] = 'true'
        responses[1] = json.dumps(page)
    elif state == 'repeated_page':
        responses[1] = responses[0]
    elif state == 'bad_row':
        page = json.loads(responses[1]);page['events'][0]['venueName'] = 'Another Club'
        responses[1] = json.dumps(page)
    elif state == 'truncated':
        page = json.loads(responses[1]);page['events'].pop();responses[1] = json.dumps(page)
    elif state == 'page_limit':
        monkeypatch.setattr(module, 'MAX_PAGES', 1)
    scraper = ComedyClubhouseScraper(venue())
    scraper.post_form = AsyncMock(side_effect=responses)
    scraper.rate_limiter = SimpleNamespace(await_if_needed=AsyncMock())
    diagnostics = ScrapeDiagnostics()
    token = bind_diagnostics(diagnostics)
    try:
        data = await scraper._fetch_all_raw_data([URL])
    finally:
        reset_diagnostics(token)
    healthy = state in {'complete', 'verified_empty'}
    assert diagnostics.fetches_failed == int(not healthy)
    assert diagnostics.fetches_ok == int(healthy)
    result = SimpleNamespace(error=None, bot_block_detected=diagnostics.bot_block_detected,
                             fetches_failed=diagnostics.fetches_failed, fetches_ok=diagnostics.fetches_ok,
                             shows=[object()] if state == 'complete' else [], items_before_filter=0)
    assert ScrapingResultProcessor._is_clean_for_reconciliation(result) is healthy
    if healthy:
        assert len(data[0][0].event_list) == (59 if state == 'complete' else 0)


@pytest.mark.parametrize('field,value', [
    ('performanceId', ''), ('performanceDateTimeMeta', 'invalid'), ('eventTitle', ''),
    ('venueLocation', 'WI'), ('buttonLink', 'https://evil.example/booking/init/ABC'),
    ('infoLinkTime', '/thecomedyclubhouse/comedy/2027-10-21/19:30/t-glydvem'),
    ('infoLinkEvent', '/anotherclub/comedy/e-abc'), ('buttonStatus', 'cancelled'),
])
def test_unverified_performance_field_fails_entire_page(field, value):
    from laughtrack.scrapers.implementations.venues.comedy_clubhouse.calendar import parse_page
    page = captured();page['events'][0][field] = value
    with pytest.raises(ValueError):parse_page(page)


@pytest.mark.asyncio
async def test_legacy_html_with_pending_pagination_cannot_be_clean():
    from laughtrack.foundation.exceptions.scraping_errors import DataError
    club = venue();club.id = 999
    scraper = ComedyClubhouseScraper(club)
    scraper.fetch_html = AsyncMock(return_value='<html><body data-initialeof=""></body></html>')
    with pytest.raises(DataError, match='unconsumed pagination'):
        await scraper.get_data(URL)
