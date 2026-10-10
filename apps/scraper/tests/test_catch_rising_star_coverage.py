"""Verified TicketWeb Princeton calendar and source-local identity normalization."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.json_ld.scraper import JsonLdScraper
from laughtrack.scrapers.implementations.json_ld.extractor import EventExtractor
from laughtrack.scrapers.implementations.json_ld.transformer import JsonLdTransformer
from laughtrack.utilities.domain.show.utils import ShowUtils

URL = 'https://www.ticketweb.com/venue/hyatt-regency-princeton-princeton-nj/44754'
FIXTURE = Path(__file__).parent / 'fixtures' / 'catch_rising_star_ticketweb.html'
META = {'force_js_rendering': True, 'location_name_filter': 'Hyatt Regency Princeton', 'localize_naive_dates': True,
        'infer_lineup_from_title': False,
        'performer_prefixes': ["NJ 101.5's ", 'Special Event Headlining Comedian '],
        'performer_aliases': {'Jackie "The Joke Man" Martling': 'Jackie Martling'}}

def club(metadata=None):
    c = Club(id=4744, name='Catch a Rising Star at Hyatt Regency Princeton',
        address='102 Carnegie Center', website='https://www.catcharisingstar.com/',
        popularity=0, zip_code='08540', phone_number='', visible=True, timezone='America/New_York')
    s = ScrapingSource(club_id=4744, platform='custom', scraper_key='json_ld', source_url=URL,
        metadata=META if metadata is None else metadata)
    c.active_scraping_source = s
    c.scraping_sources = [s]
    return c

def events():
    return EventExtractor.extract_events(FIXTURE.read_text(), base_url=URL)

def test_full_calendar_times_tickets_lineups_and_repeat():
    transformer = JsonLdTransformer(club())
    shows = [transformer.transform_to_show(e) for e in events()]
    assert len(shows) == 16 and all(shows)
    assert all(s.club_id == 4744 and not s.infer_lineup_from_title for s in shows)
    assert all(s.tickets[0].price is None and s.tickets[0].purchase_url == s.show_page_url for s in shows)
    assert [c.name for c in shows[0].lineup] == ['Fred Rubino', 'Fat Jay', 'Mario Bosco']
    assert [c.name for c in shows[1].lineup] == ['Eric Potts']
    assert [c.name for c in shows[4].lineup] == ['Jackie Martling']
    dates = [s.date.astimezone(ZoneInfo('America/New_York')) for s in shows]
    assert [(d.day, d.hour, d.minute) for d in dates[-3:]] == [(18,20,0),(19,20,0),(26,19,30)]
    assert dates[0].utcoffset().total_seconds() == -14400
    assert dates[-1].utcoffset().total_seconds() == -18000
    baseline = {'14269974','14297294','14289694','14289704','14371324','14371334'}
    assert baseline <= {s.show_page_url.rsplit('/',1)[-1] for s in shows}
    expected = {'14269974':'2026-10-18T00:00:00+00:00', '14297294':'2026-10-24T00:00:00+00:00',
        '14289694':'2026-11-07T01:00:00+00:00', '14289704':'2026-11-08T00:30:00+00:00',
        '14371324':'2026-12-05T01:00:00+00:00', '14371334':'2026-12-06T00:30:00+00:00'}
    assert {s.show_page_url.rsplit('/',1)[-1]:s.date.isoformat() for s in shows
        if s.show_page_url.rsplit('/',1)[-1] in baseline} == expected
    assert len(ShowUtils.deduplicate_shows(shows + [transformer.transform_to_show(e) for e in events()])) == 16

@pytest.mark.asyncio
async def test_native_source_guard_and_browser_route():
    scraper = JsonLdScraper(club())
    scraper._fetch_html_with_js = AsyncMock(return_value=FIXTURE.read_text())
    scraper.fetch_html = AsyncMock(side_effect=AssertionError('requires browser'))
    data = await scraper.get_data(URL)
    assert len(data.event_list) == 16
    scraper._fetch_html_with_js.assert_awaited_once_with(URL)
    scraper._fetch_html_with_js.return_value = FIXTURE.read_text().replace('Hyatt Regency Princeton', 'Agoros Somerset')
    assert await scraper.get_data(URL) is None

def test_empty_lineup_never_infers_title_and_unlisted_prefixed_name_normalizes():
    event = events()[0]
    event.performers = []
    assert JsonLdTransformer(club()).transform_to_show(event).infer_lineup_from_title is False
    event = events()[1]
    event.performers[0].name = "NJ 101.5's Future Guest"
    assert JsonLdTransformer(club()).transform_to_show(event).lineup[0].name == 'Future Guest'

def test_defaults_unchanged_and_raw_events_not_mutated():
    event = events()[1]
    original = event.performers[0].name
    JsonLdTransformer(club()).transform_to_show(event)
    assert event.performers[0].name == original
    assert JsonLdTransformer(club({})).transform_to_show(event).infer_lineup_from_title is True

def test_explicit_offset_and_soldout_preserved():
    event = events()[0]
    event.start_date = datetime(2026, 10, 11, 0, tzinfo=timezone.utc)
    event.offers[0].availability = 'SoldOut'
    show = JsonLdTransformer(club()).transform_to_show(event)
    assert show.date == event.start_date and show.date.tzinfo is timezone.utc
    assert show.tickets[0].sold_out

def test_explicit_alias_suppression_leaves_no_inferred_lineup():
    metadata = dict(META, performer_aliases={"Eric Potts": None})
    show = JsonLdTransformer(club(metadata)).transform_to_show(events()[1])
    assert show.lineup == [] and show.infer_lineup_from_title is False

@pytest.mark.parametrize('metadata', [{'performer_aliases':[]}, {'performer_prefixes':'wrong'}, {'performer_aliases':{'Fred Rubino':42}}])
def test_invalid_source_options_fail(metadata):
    with pytest.raises(ValueError):
        JsonLdTransformer(club(metadata)).transform_to_show(events()[0])
