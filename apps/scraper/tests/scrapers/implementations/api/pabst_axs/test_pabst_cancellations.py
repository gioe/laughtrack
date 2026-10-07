from datetime import datetime, timezone
from laughtrack.scrapers.implementations.api.pabst_axs.cancellations import extract_detail_identity, match_cancellation

URL = 'https://www.pabsttheatergroup.com/events/detail/zarna-garg-2026'
HTML = '''<meta property="og:url" content="%s"><div class="event_detail">
<h1 class="title">Zarna Garg</h1><img src="https://www.pabsttheatergroup.com/assets/img/2026.10.04-T-Zarna.png">
<li class="sidebar_event_date"><span>CANCELED</span></li>
<li class="sidebar_event_venue"><span><a>Turner Hall Ballroom</a></span></li></div>''' % URL

def test_cancelled_detail_preserves_stored_instant():
    row = dict(id=1, club_id=9120, production_company_id=None,last_scraped_by='pabst_theater_group',
        show_page_url=URL,date=datetime(2026,10,5,tzinfo=timezone.utc),source_performance_id=None,
        name='Zarna Garg',venue_name='Turner Hall Ballroom',venue_address='1040 Vel R. Phillips Avenue',venue_zip='53203')
    detail=extract_detail_identity(HTML,URL)
    intent=match_cancellation(detail,[row],'pabst_theater_group',URL)
    assert intent.show_id == 1
    assert intent.date == row['date']

import pytest
from unittest.mock import AsyncMock
from laughtrack.foundation.infrastructure.http.diagnostics import ScrapeDiagnostics, bind_diagnostics, reset_diagnostics

@pytest.mark.parametrize('html', ['', '<html>Not found</html>', HTML.replace('CANCELED','Oct 4') + '<footer>Cancelled FAQ</footer>', HTML.replace('CANCELED','Sold Out')])
def test_missing_or_scheduled_detail_never_means_cancellation(html):
    detail=extract_detail_identity(html,URL)
    assert detail is None or not detail['cancelled']

@pytest.mark.parametrize('html', [HTML.replace(URL,URL+'-wrong'), HTML.replace('2026.10.04','2026.99.99'), HTML.replace('class="event_detail"','class="other"'), HTML+HTML])
def test_cancelled_identity_requires_one_valid_detail(html):
    assert extract_detail_identity(html,URL) is None

@pytest.mark.asyncio
@pytest.mark.parametrize('response', ['', '<html>404</html>', RuntimeError('fetch failed')])
async def test_missing_cancel_detail_holds_inventory_and_disables_cleanup(response):
    from .test_pabst_group import _operator_proxy, _EVENTS_HTML
    from laughtrack.scrapers.implementations.api.pabst_axs.group_scraper import PabstTheaterGroupScraper
    from laughtrack.scrapers.implementations.api.pabst_axs.extractor import extract_events
    scraper=PabstTheaterGroupScraper(_operator_proxy())
    scraper._club_handler.execute_with_cursor=lambda *a,**kw: []
    scraper.fetch_html=AsyncMock(side_effect=response) if isinstance(response,Exception) else AsyncMock(return_value=response)
    diagnostics=ScrapeDiagnostics()
    token=bind_diagnostics(diagnostics)
    try:
        events=extract_events(_EVENTS_HTML)
        assert await scraper._review_cancellations(events) == events
        assert scraper._cancellations == []
        assert diagnostics.fetches_failed == 2
    finally:
        reset_diagnostics(token)

@pytest.mark.asyncio
async def test_pervenue_cancelled_event_not_inserted_without_existing_row():
    from .test_pabst_axs import _make_scraper
    from laughtrack.core.entities.event.pabst_axs import PabstAXSEvent
    scraper=_make_scraper()
    scraper.fetch_html=AsyncMock(return_value=HTML)
    event=PabstAXSEvent(title='Zarna Garg',date_str='2026-10-04',show_page_url=URL)
    assert await scraper._review_cancellations([event]) == []
    assert scraper._cancellations == []
    assert scraper._club_handler.execute_with_cursor.call_args.args[1] == ('pabst_axs',999)

@pytest.mark.asyncio
async def test_scheduled_detail_retains_normal_event():
    from .test_pabst_axs import _make_scraper
    from laughtrack.core.entities.event.pabst_axs import PabstAXSEvent
    scraper=_make_scraper()
    scraper.fetch_html=AsyncMock(return_value=HTML.replace('CANCELED','October 4'))
    event=PabstAXSEvent(title='Zarna Garg',date_str='2026-10-04',show_page_url=URL)
    assert await scraper._review_cancellations([event]) == [event]
    assert scraper._cancellations == []
