"""Real PostgreSQL: only cancellation changes, references and stored instant survive."""
from dataclasses import replace
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest
from psycopg2.extras import RealDictCursor

from .test_next_stop_cancellation_lifecycle import lifecycle, snapshot
from laughtrack.scrapers.implementations.api.pabst_axs.cancellations import extract_detail_identity, match_cancellation

URL='https://www.pabsttheatergroup.com/events/detail/zarna-garg-2026'


def setup_pabst(conn, show):
    with conn.cursor() as cur:
        cur.execute("UPDATE shows SET production_company_id=NULL,last_scraped_by='pabst_theater_group',show_page_url=%s,name='Zarna Garg' WHERE id=%s",(URL,show.id))
        cur.execute("UPDATE clubs SET name='Turner Hall Ballroom' WHERE id=1")
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute('SELECT s.*,c.name AS venue_name,c.address AS venue_address,c.zip_code AS venue_zip FROM shows s JOIN clubs c ON c.id=s.club_id')
        row=dict(cur.fetchone())
    day=row['date'].astimezone(ZoneInfo('America/Chicago')).strftime('%Y.%m.%d')
    html=f'''<div class="event_detail"><h1 class="title">Zarna Garg</h1><img src="https://www.pabsttheatergroup.com/assets/img/{day}-T-Zarna.png">
    <li class="sidebar_event_venue"><a>Turner Hall Ballroom</a></li><li class="sidebar_event_date"><span>CANCELED</span></li></div>'''
    intent=match_cancellation(extract_detail_identity(html,URL),[row],'pabst_theater_group',URL)
    return intent,row,html


def test_cancel_pabst_preserves_all_references_and_replay(lifecycle):
    conn,show,handler,_,_=lifecycle
    intent,_,_=setup_pabst(conn,show)
    before=snapshot(conn)
    assert handler.apply_cancellations([intent]) == [show.id]
    assert handler.apply_cancellations([intent]) == [show.id]
    after=snapshot(conn)
    expected=before
    expected['shows'][0]['is_cancelled']=True
    assert after == expected
    assert after['shows'][0]['date'] == before['shows'][0]['date']


@pytest.mark.parametrize('field,value',[('club_id',999),('name','Wrong'),('scraper_key','unknown'),('venue_name','Wrong'),('production_company_id',35)])
def test_cancel_pabst_rejects_changed_identity(lifecycle,field,value):
    conn,show,handler,_,_=lifecycle
    intent,_,_=setup_pabst(conn,show)
    before=snapshot(conn)
    with pytest.raises(ValueError):
        handler.apply_cancellations([replace(intent,**{field:value})])
    assert snapshot(conn) == before


@pytest.mark.parametrize('field,value',[('name','Wrong'),('venue_name','Wrong'),('date',datetime(2020,1,1,tzinfo=timezone.utc)),('last_scraped_by','unknown'),('show_page_url',URL+'wrong')])
def test_cancel_pabst_evidence_mismatch_produces_no_intent(lifecycle,field,value):
    conn,show,_,_,_=lifecycle
    _,row,html=setup_pabst(conn,show)
    row[field]=value
    assert match_cancellation(extract_detail_identity(html,URL),[row],'pabst_theater_group',URL) is None


def test_cancel_pabst_ambiguous_null_company_identity_rejected(lifecycle):
    conn,show,handler,_,_=lifecycle
    intent,row,html=setup_pabst(conn,show)
    assert match_cancellation(extract_detail_identity(html,URL),[row,row],'pabst_theater_group',URL) is None
    with conn.cursor() as cur:
        cur.execute('INSERT INTO shows(name,show_page_url,date,club_id,last_scraped_by,source_performance_id) SELECT name,show_page_url,date,club_id,last_scraped_by,\'different\' FROM shows WHERE id=%s',(show.id,))
    with pytest.raises(ValueError,match='Ambiguous'):
        handler.apply_cancellations([intent])
