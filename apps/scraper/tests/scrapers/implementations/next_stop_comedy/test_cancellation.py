import json
from laughtrack.scrapers.implementations.next_stop_comedy import extractor

URL = 'https://www.nextstopcomedy.com/events/venue-2027-01-15'

def cancelled_html(status='https://schema.org/EventCancelled', url=URL):
    node = {'@type': 'ComedyEvent', 'name': 'Venue', 'url': url, 'startDate': '2027-01-15T20:00:00-05:00',
            'eventStatus': status, 'location': {'name': 'Venue', 'address': {
                'streetAddress': '1 Main St', 'addressLocality': 'Boston', 'addressRegion': 'MA',
                'postalCode': '02116', 'addressCountry': 'US'}}}
    return f'<link rel="canonical" href="{url}"><main><h1>Venue</h1></main><script type="application/ld+json">{json.dumps(node)}</script>'

def test_cancelled_exact_main_event_is_retained_as_evidence():
    assert len(extractor.extract_cancelled_events(cancelled_html(), URL)) == 1
    assert extractor.extract_json_ld_events(cancelled_html()) == []

from datetime import datetime
from unittest.mock import MagicMock
import pytest
from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.implementations.next_stop_comedy.scraper import NextStopComedyScraper


def scraper_and_row():
    club = Club(id=0, name='Next Stop', address='', website='', popularity=0, zip_code='', phone_number='',
                visible=False, is_synthetic=True, production_company_id=35)
    scraper = NextStopComedyScraper(club)
    row = dict(id=101, club_id=5, production_company_id=35, last_scraped_by='next_stop_comedy',
               name='Venue', venue_name='Venue', venue_address='1 Main St', venue_zip='02116',
               show_page_url=URL, source_performance_id=None, date=datetime.fromisoformat('2027-01-16T01:00:00+00:00'),
               is_future=True)
    scraper._stored_events = [row]
    return scraper, row


def test_cancelled_exact_legacy_identity_builds_frozen_intent():
    from dataclasses import FrozenInstanceError
    scraper, row = scraper_and_row()
    intents = scraper._match_cancellations(extractor.extract_cancelled_events(cancelled_html(), URL), [])
    assert len(intents) == 1
    assert intents[0].show_id == row['id']
    assert intents[0].source_performance_id is None
    with pytest.raises(FrozenInstanceError):
        intents[0].show_id = 2


@pytest.mark.asyncio
@pytest.mark.parametrize('listing', ['', '<html><body>No events</body></html>', f'<a href="{URL}">Event</a>'])
async def test_cancelled_stored_url_is_checked_when_absent_from_listing(monkeypatch, listing):
    scraper, row = scraper_and_row()
    calls = []
    async def fetch(url):
        calls.append(url)
        return cancelled_html() if url == URL else listing
    async def api():
        return []
    monkeypatch.setattr(scraper._club_handler, 'execute_with_cursor', lambda *args, **kwargs: [row])
    monkeypatch.setattr(scraper, '_fetch_page', fetch)
    monkeypatch.setattr(scraper, '_collect_api_events', api)
    monkeypatch.setattr(scraper, '_upsert_venue', MagicMock(side_effect=AssertionError('No cancellation venue writes')))
    assert await scraper.scrape_async() == []
    assert calls.count(URL) == 1
    assert [intent.show_id for intent in scraper._cancellations] == [101]
    assert await scraper.scrape_async() == []
    assert len(scraper._cancellations) == 1


def test_cancelled_only_run_hands_evidence_to_result(monkeypatch):
    scraper, row = scraper_and_row()
    def scrape():
        scraper._cancellations = scraper._match_cancellations(extractor.extract_cancelled_events(cancelled_html(), URL), [])
        return []
    monkeypatch.setattr(scraper, 'scrape', scrape)
    result = scraper.scrape_with_result()
    assert not result.shows
    assert result.cancellations[0].show_id == row['id']


@pytest.mark.parametrize('status', ['https://schema.org/EventScheduled', None, 'https://schema.org/EventRescheduled', 'unknown'])
def test_cancellation_non_cancelled_status_is_not_evidence(status):
    assert extractor.extract_cancelled_events(cancelled_html(status=status), URL) == []


@pytest.mark.parametrize('html', ['', '<h1>404</h1>', cancelled_html(url=URL + '-changed'),
                                  cancelled_html().replace('<h1>Venue</h1>', '<h1>Other</h1>'),
                                  cancelled_html().replace('2027-01-15T20:00:00-05:00', '2027-01-15T20:00:00')])
def test_cancellation_missing_redirect_wrong_main_or_naive_date_is_held(html):
    assert extractor.extract_cancelled_events(html, URL) == []


@pytest.mark.parametrize('change', [
    {'production_company_id': 36}, {'last_scraped_by': 'other'}, {'show_page_url': URL + '-other'},
    {'name': 'Other event'}, {'venue_name': 'Other venue'}, {'venue_address': '2 Main St'},
    {'venue_zip': '10001'}, {'date': datetime.fromisoformat('2027-01-17T01:00:00+00:00')},
])
def test_cancellation_wrong_stored_identity_is_held(change):
    scraper, row = scraper_and_row()
    row.update(change)
    assert scraper._match_cancellations(extractor.extract_cancelled_events(cancelled_html(), URL), []) == []


def test_cancellation_ambiguous_stored_identity_is_held():
    scraper, row = scraper_and_row()
    scraper._stored_events.append(dict(row, id=102))
    assert scraper._match_cancellations(extractor.extract_cancelled_events(cancelled_html(), URL), []) == []


def test_cancellation_scheduled_conflict_marks_incomplete():
    from laughtrack.foundation.infrastructure.http.diagnostics import ScrapeDiagnostics, bind_diagnostics, reset_diagnostics
    scraper, _ = scraper_and_row()
    diagnostics = ScrapeDiagnostics()
    token = bind_diagnostics(diagnostics)
    try:
        cancelled = extractor.extract_cancelled_events(cancelled_html(), URL)
        scheduled = extractor.extract_json_ld_events(cancelled_html(status='https://schema.org/EventScheduled'))
        assert scraper._match_cancellations(cancelled, scheduled) == []
        assert diagnostics.fetches_failed == 1
        assert scraper._detail_events(URL, cancelled_html() + cancelled_html(status='https://schema.org/EventScheduled')) == []
        assert diagnostics.fetches_failed == 2
    finally:
        reset_diagnostics(token)


def test_cancellation_inconsistent_main_native_date_is_not_url_fallback():
    ident = '1df52ed6-a1f9-4f4f-9002-87a6eff110cf'
    props = dict(eventId=ident, currentEventId=ident, eventSlug=URL.rsplit('/', 1)[-1],
                 eventDate='2027-01-17T01:00:00Z')
    html = cancelled_html() + '<script>self.__next_f.push(' + json.dumps([1, '1:' + json.dumps(props) + '\n']) + ')</script>'
    assert extractor.extract_cancelled_events(html, URL) == []
