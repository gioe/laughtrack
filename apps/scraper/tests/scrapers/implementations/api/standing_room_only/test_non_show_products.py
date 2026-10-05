"""Season products must not become performances through artificial child dates."""
import copy
import json
from pathlib import Path

import pytest

from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.implementations.api.standing_room_only.extractor import StandingRoomOnlyExtractor as E

AUDIT = Path(__file__).resolve().parents[5] / 'docs/audits/2026-09-27-price-extraction/venues'
PASS = json.loads((AUDIT / 'sro-season-pass.json').read_text())['source_events'][0]
FEED = json.loads((AUDIT / 'sro-feed.json').read_text())
ORIGIN = 'https://www.standingroomonlytickets.com'

@pytest.fixture(autouse=True)
def audit_clock(monkeypatch):
    # Before the artificial pass date: past-date filtering must not hide the bug.
    monkeypatch.setattr('laughtrack.scrapers.implementations.api.standing_room_only.extractor.time.time', lambda: 1790467200)


def test_real_pass_description_and_dated_child_do_not_make_a_show():
    assert 'covers all shows' in PASS['Description']
    assert PASS['Shows'][0]['Id'] == 1655
    assert E.extract_events({'Data': [PASS]}, ORIGIN) == []


def test_real_performances_and_unknown_prices_are_preserved():
    ordinary = [r for r in FEED['Data'] if r['Id'] != 536]
    expected = [(r['Id'], E._parse_dotnet_ms(s['Start'])) for r in ordinary for s in r['Shows']
                if s.get('IsShowOld') is not True and (E._parse_dotnet_ms(s.get('Start')) or 0) > 1790467200000]
    actual = E.extract_events(FEED, ORIGIN)
    assert expected
    assert [(e.event_id, e.start_ms) for e in actual] == expected
    club = Club(id=11473, name='One Night Stans', address='', website=ORIGIN, popularity=0,
                zip_code='', phone_number='', visible=True, timezone='America/Detroit')
    for event in actual:
        show = event.to_show(club)
        assert show is not None
        assert len(show.tickets) == 1
        assert show.tickets[0].price is None


@pytest.mark.parametrize('title', ['Season Pass', 'Summer Season Pass', '2027 Winter Season Pass',
    'season-pass', 'Summer&nbsp;Season Pass', 'Annual Membership', 'VIP Membership Pass', 'Membership'])
def test_explicit_product_titles_are_excluded(title):
    raw = copy.deepcopy(PASS)
    raw['EventTitle'] = title
    assert E.extract_events({'Data': [raw]}, ORIGIN) == []


@pytest.mark.parametrize('title', ['Pass the Mic', 'Summer Comedy', 'Season Pass Comedy Night',
    'Membership Has Its Privileges: Stand-Up', 'Kate Brindle', 'Backstage Pass'])
def test_ordinary_titles_and_incidental_pass_text_are_not_excluded(title):
    raw = copy.deepcopy(PASS)
    raw['EventTitle'] = title
    raw['Description'] = 'A stand-up performance. Season pass members welcome; buy tickets at the box office.'
    assert len(E.extract_events({'Data': [raw]}, ORIGIN)) == 1
