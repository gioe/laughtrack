"""Pipeline smoke tests for RumorsComedyClubScraper."""

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.venues.rumors_comedy_club.extractor import (
    RumorsComedyClubExtractor,
)
from laughtrack.scrapers.implementations.venues.rumors_comedy_club.scraper import (
    RumorsComedyClubScraper,
)

SCRAPING_URL = "https://rumorscomedyclub.com/events"

NUXT_HTML = r"""
<html><body>
<script>
window.__NUXT__=(function(a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p,q,r){
r.facebook="https:\u002F\u002Fwww.facebook.com\u002FRumorsComedyClub\u002F";
return {layout:"default",data:[{events:[
  {id:g,name:h,startDate:"2026-07-23",endDate:"2026-07-25",description:"",useBioForDescription:b,
   comedian:{name:h,biography:i},
   shows:[
    {id:j,date:k,ticketPrice:c,type:l,totalTickets:d,ticketsSold:e},
    {id:m,date:n,ticketPrice:f,type:o,totalTickets:d,ticketsSold:d},
    {id:p,date:q,ticketPrice:f,type:o,totalTickets:d},
    {id:"show-open-vip",date:q,ticketPrice:79,type:"DATE NIGHT PACKAGE",totalTickets:d}
   ]},
  {id:"simple",name:"Closed",isSimpleEvent:true,startDate:"2026-06-30",endDate:"2026-06-30",shows:[]}
]}],fetch:{"1":{venueInfo:{venueName:"Rumor's Restaurant and Comedy Club",address:"190-2025 Corydon Avenue",city:"Winnipeg",region:"MB",postalZipCode:"R3P 0N5",country:"CA"}}},
error:null,state:{},serverRendered:true,routePath:"/events",config:{}}
}(0,true,48,200,199,65,"1760126678693","Preacher Lawson","\u003Cp\u003EHigh energy stand-up.\u003C\u002Fp\u003E","show-early","2026-07-23T19:45","Regular","show-sold","2026-07-23T21:45","VIP","show-open","2026-07-24T19:15",{}));
</script>
</body></html>
"""


def _club() -> Club:
    club = Club(
        id=9998,
        name="Rumor's Comedy Club",
        address="190-2025 Corydon Avenue",
        website="https://rumorscomedyclub.com/",
        popularity=0,
        zip_code="R3P 0N5",
        phone_number="(204) 488-4520",
        visible=True,
        timezone="America/Winnipeg",
        city="Winnipeg",
        state="MB",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="custom",
        scraper_key="rumors_comedy_club",
        source_url=SCRAPING_URL,
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def test_extract_events_from_nuxt_payload_skips_sold_out_and_simple_events():
    events = RumorsComedyClubExtractor.extract_events(NUXT_HTML)

    assert len(events) == 2
    assert [event.name for event in events] == ["Preacher Lawson", "Preacher Lawson"]
    assert [event.start_date for event in events] == ["2026-07-23T19:45", "2026-07-24T19:15"]
    assert [event.ticket_price for event in events] == [48.0, 65.0]
    assert [event.ticket_type for event in events] == ["Regular", "VIP"]
    assert [event.ticket_url for event in events] == [
        "https://rumorscomedyclub.com/events/1760126678693/show-early",
        "https://rumorscomedyclub.com/events/1760126678693/show-open",
    ]
    assert events[1].ticket_options == [
        {
            "purchase_url": "https://rumorscomedyclub.com/events/1760126678693/show-open",
            "price": 65.0,
            "type": "VIP",
        },
        {
            "purchase_url": "https://rumorscomedyclub.com/events/1760126678693/show-open-vip",
            "price": 79.0,
            "type": "DATE NIGHT PACKAGE",
        },
    ]
    assert events[0].description == "High energy stand-up."


def test_event_to_show_uses_winnipeg_timezone_and_ticket_price():
    event = RumorsComedyClubExtractor.extract_events(NUXT_HTML)[0]

    show = event.to_show(_club())

    assert show is not None
    assert show.name == "Preacher Lawson"
    assert show.date.isoformat() == "2026-07-23T19:45:00-05:00"
    assert show.tickets[0].price == 48.0
    assert show.tickets[0].purchase_url == "https://rumorscomedyclub.com/events/1760126678693/show-early"


def test_event_to_show_keeps_multiple_ticket_types_for_same_showtime():
    event = RumorsComedyClubExtractor.extract_events(NUXT_HTML)[1]

    show = event.to_show(_club())

    assert show is not None
    assert [(ticket.price, ticket.type) for ticket in show.tickets] == [
        (65.0, "VIP"),
        (79.0, "DATE NIGHT PACKAGE"),
    ]


@pytest.mark.asyncio
async def test_get_data_fetches_source_page(monkeypatch):
    scraper = RumorsComedyClubScraper(_club())
    fetched = []

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        fetched.append(url)
        return NUXT_HTML

    monkeypatch.setattr(RumorsComedyClubScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(SCRAPING_URL)

    assert result is not None
    assert len(result.event_list) == 2
    assert fetched == [SCRAPING_URL]


def test_scraper_class_has_correct_key():
    assert RumorsComedyClubScraper.key == "rumors_comedy_club"
