import json
from unittest.mock import AsyncMock, patch

import pytest

from laughtrack.scrapers.implementations.api.etix.scraper import EtixScraper
from laughtrack.core.entities.club.model import Club, ScrapingSource

URL = 'https://www.tickettailor.com/events/milwaukeecomedy/2388761'


def detail(**changes):
    event = dict(**{'@type': 'Event'}, name='Comedy Night', startDate='2026-10-08T19:00:00-05:00',
                 eventStatus='https://schema.org/EventScheduled',
                 location={'name': 'The Laughing Tap', 'address': {'postalCode': '53202'}},
                 offers=[{'url': URL, 'price': '25', 'priceCurrency': 'USD'}])
    event.update(changes)
    return f'''<script type="application/ld+json">{json.dumps(event)}</script>
    <h1 class="hero__title">Comedy Night</h1><div class="hero__meta">
    <span class="event-meta__date">Thu Oct 8, 2026 7:00 PM - 9:00 PM CDT</span>
    <span class="event-meta__location">The Laughing Tap, 53202</span></div>
    <section class="detail-content__description">Doors at 6pm, show starts at 7pm.</section>'''


def club():
    c = Club(id=9070, name='The Laughing Tap', address='706 S 5th St', website='https://laughingtap.com/',
             popularity=0, zip_code='53202', phone_number='', visible=True, timezone='America/Chicago',
             city='Milwaukee', state='WI')
    c.active_scraping_source = ScrapingSource(id=5941, club_id=9070, platform='etix', scraper_key='etix',
                                             source_url='https://www.etix.com/ticket/v/27614/laughing-tap')
    return c


@pytest.mark.asyncio
async def test_blocked_primary_recovers_verified_subset_and_preserves_failure():
    s = EtixScraper(club())
    s._fetch_etix_html = AsyncMock(return_value='<html>datadome</html>')
    s.fetch_html_bare = AsyncMock(side_effect=[f'<a href="{URL}">Tickets</a>', detail()])
    with patch('laughtrack.scrapers.implementations.api.etix.scraper.current_diagnostics') as diagnostics:
        result = await s.get_data(s.club.scraping_url)
    assert [e.ticket_url for e in result.event_list] == [URL]
    assert result.event_list[0].start_date == '2026-10-08T19:00:00-05:00'
    diagnostics.return_value.record_fetch_failed.assert_called()
    diagnostics.return_value.record_scrape_error.assert_called()


@pytest.mark.parametrize('changes', [
    {'startDate': '2026-10-08T18:00:00-05:00'},
    {'startDate': '2026-10-08T19:00:00-04:00'},
    {'name': 'Other'},
    {'location': {'name': 'Other', 'address': {'postalCode': '53202'}}},
    {'eventStatus': 'https://schema.org/EventCancelled'},
    {'offers': [{'url': URL.replace('2388761', '123'), 'price': '25'}]},
])
def test_mismatched_evidence_rejected(changes):
    from laughtrack.scrapers.implementations.api.etix.public_ticket_tailor import verify_detail
    assert verify_detail(detail(**changes), URL, club()) is None


@pytest.mark.parametrize('replacement', ['Doors at 7pm.', 'Show starts at 10pm.', 'Show starts at 7pm. Show at 10pm.'])
def test_doors_only_or_conflicting_showtime_rejected(replacement):
    from laughtrack.scrapers.implementations.api.etix.public_ticket_tailor import verify_detail
    html = detail().replace('Doors at 6pm, show starts at 7pm.', replacement)
    assert verify_detail(html, URL, club()) is None


def test_duplicate_structured_events_are_ambiguous():
    from laughtrack.scrapers.implementations.api.etix.public_ticket_tailor import verify_detail
    assert verify_detail(detail() + detail(), URL, club()) is None


@pytest.mark.asyncio
async def test_partial_detail_failure_keeps_safe_subset_and_owned_links_only():
    from laughtrack.scrapers.implementations.api.etix.public_ticket_tailor import fetch_highlights, HOME
    other = URL.replace('2388761', '2388786')
    home = ''.join(f'<a href="{u}">Tickets</a>' for u in [URL, URL, other,
        'https://evil.example/events/milwaukeecomedy/123',
        'https://www.tickettailor.com/events/other/123'])
    fetch = AsyncMock(side_effect=[home, detail(), RuntimeError('unavailable')])
    assert len(await fetch_highlights(fetch, club())) == 1
    assert [call.args[0] for call in fetch.call_args_list] == [HOME, URL, other]


@pytest.mark.asyncio
async def test_healthy_primary_does_not_fetch_home():
    s = EtixScraper(club())
    s._fetch_etix_html = AsyncMock(return_value='<html>healthy listing</html>')
    s.fetch_html_bare = AsyncMock()
    with patch('laughtrack.scrapers.implementations.api.etix.scraper.EtixExtractor.extract_events', return_value=[object()]):
        result = await s.get_data(s.club.scraping_url)
    assert len(result.event_list) == 1
    s.fetch_html_bare.assert_not_called()


@pytest.mark.asyncio
async def test_recovered_subset_cannot_reconcile_missing_inventory():
    from types import SimpleNamespace
    from laughtrack.foundation.infrastructure.http.diagnostics import ScrapeDiagnostics, bind_diagnostics, reset_diagnostics
    from laughtrack.utilities.domain.scraper.result import ScrapingResultProcessor
    diagnostics = ScrapeDiagnostics()
    token = bind_diagnostics(diagnostics)
    try:
        s = EtixScraper(club())
        s._fetch_etix_html = AsyncMock(return_value='<html>datadome</html>')
        s.fetch_html_bare = AsyncMock(side_effect=[f'<a href="{URL}">Tickets</a>', detail()])
        result = await s.get_data(s.club.scraping_url)
        diagnostics.record_fetch_ok()
    finally:
        reset_diagnostics(token)
    assert not ScrapingResultProcessor._is_clean_for_reconciliation(SimpleNamespace(
        error=None, bot_block_detected=diagnostics.bot_block_detected, fetches_failed=diagnostics.fetches_failed,
        fetches_ok=diagnostics.fetches_ok, shows=result.event_list))


@pytest.mark.asyncio
async def test_detail_budget_is_bounded():
    from laughtrack.scrapers.implementations.api.etix.public_ticket_tailor import fetch_highlights, MAX_DETAILS
    home = ''.join(f'<a href="https://www.tickettailor.com/events/milwaukeecomedy/{n}">Tickets</a>' for n in range(100, 130))
    fetch = AsyncMock(side_effect=[home] + ['invalid'] * MAX_DETAILS)
    assert await fetch_highlights(fetch, club()) == []
    assert fetch.await_count == MAX_DETAILS + 1


@pytest.mark.asyncio
async def test_nonempty_unrecognized_failure_page_still_attempts_partial_recovery():
    s = EtixScraper(club())
    s._fetch_etix_html = AsyncMock(return_value='<html><h1>Forbidden</h1></html>')
    s.fetch_html_bare = AsyncMock(side_effect=[f'<a href="{URL}">Tickets</a>', detail()])
    assert len((await s.get_data(s.club.scraping_url)).event_list) == 1
