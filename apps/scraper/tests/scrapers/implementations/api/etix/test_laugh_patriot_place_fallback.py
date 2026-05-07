from datetime import date

import pytest


ETIX_URL = "https://www.etix.com/ticket/mvc/online/upcomingEvents/venue?venue_id=32411&orderBy=1&pageNumber=1"
CALENDAR_URL = "https://laughpatriotplace.com/calendar/"
DETAIL_URL = "https://laughpatriotplace.com/shows/agostino-zoida/"
NEXT_MONTH_DETAIL_URL = "https://laughpatriotplace.com/shows/mike-hanley/"
TICKET_URL = "https://www.etix.com/ticket/e/1057557/az-foxboro-laugh-patriot-place"
NEXT_MONTH_TICKET_URL = "https://www.etix.com/ticket/e/1057556/hanley-foxboro-laugh-patriot-place"


def _club():
    from laughtrack.core.entities.club.model import Club, ScrapingSource

    club = Club(
        id=332,
        name="Laugh Patriot Place",
        address="23 Patriot Place",
        website="https://laughpatriotplace.com",
        popularity=0,
        zip_code="02035",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="etix",
        scraper_key="etix",
        source_url="https://www.etix.com/ticket/v/32411/laugh-patriot-place",
        external_id=None,
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _calendar_html(day: int, title: str = "Agostino Zoida", detail_url: str = DETAIL_URL) -> str:
    return f"""
    <html><body>
      <table><tbody>
        <tr>
          <td class="has-events">
            <span class="calendar-date">{day}</span>
            <div class="post-details">
              <div class="post-flex">
                <h3>{title}</h3>
                <a class="btn" href="{detail_url}">Buy Tickets</a>
              </div>
            </div>
          </td>
          <td class="has-events">
            <span class="calendar-date">1</span>
            <div class="post-details disable-events">
              <div class="post-flex">
                <h3>Past Comic</h3>
                <a class="btn noevent" href="">Event Passed</a>
              </div>
            </div>
          </td>
        </tr>
      </tbody></table>
    </body></html>
    """


def _detail_html(ticket_url: str = TICKET_URL) -> str:
    return f"""
    <html><body>
      <h1>Agostino Zoida</h1>
      <a href="{ticket_url}">Buy Tickets</a>
    </body></html>
    """


@pytest.mark.asyncio
async def test_laugh_patriot_place_fallback_uses_public_calendar(monkeypatch):
    from laughtrack.scrapers.implementations.api.etix.data import EtixPageData
    from laughtrack.scrapers.implementations.api.etix.scraper import EtixScraper

    scraper = EtixScraper(_club())
    calls = []
    today = date.today()
    next_month_index = today.month
    next_year = today.year + next_month_index // 12
    next_month = next_month_index % 12 + 1
    next_month_url = f"{CALENDAR_URL}?cal_year={next_year}&month={next_month}"

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        calls.append(url)
        if url == ETIX_URL:
            return "<html><title>DataDome</title></html>"
        if url == CALENDAR_URL:
            return _calendar_html(today.day)
        if url == next_month_url:
            return _calendar_html(4, title="Mike Hanley", detail_url=NEXT_MONTH_DETAIL_URL)
        if url.startswith(f"{CALENDAR_URL}?cal_year="):
            return "<html><body><table></table></body></html>"
        if url == DETAIL_URL:
            return _detail_html()
        if url == NEXT_MONTH_DETAIL_URL:
            return _detail_html(NEXT_MONTH_TICKET_URL)
        raise AssertionError(f"unexpected URL: {url}")

    monkeypatch.setattr(EtixScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(ETIX_URL)

    assert isinstance(result, EtixPageData)
    assert calls[:3] == [ETIX_URL, CALENDAR_URL, next_month_url]
    assert DETAIL_URL in calls
    assert NEXT_MONTH_DETAIL_URL in calls
    assert len(result.event_list) == 2
    events_by_title = {event.title: event for event in result.event_list}
    assert events_by_title["Agostino Zoida"].event_url == DETAIL_URL
    assert events_by_title["Agostino Zoida"].ticket_url == TICKET_URL
    assert events_by_title["Agostino Zoida"].start_date == today.isoformat()
    assert events_by_title["Mike Hanley"].event_url == NEXT_MONTH_DETAIL_URL
    assert events_by_title["Mike Hanley"].ticket_url == NEXT_MONTH_TICKET_URL
    assert events_by_title["Mike Hanley"].start_date == date(next_year, next_month, 4).isoformat()


def test_etix_event_can_use_public_event_page_for_show_page_url():
    from laughtrack.core.entities.event.etix import EtixEvent

    event = EtixEvent(
        title="Agostino Zoida",
        start_date="2099-05-08",
        time_str="",
        ticket_url=TICKET_URL,
        event_url=DETAIL_URL,
    )

    show = event.to_show(_club())

    assert show is not None
    assert show.show_page_url == DETAIL_URL.rstrip("/")
    assert show.tickets[0].purchase_url == TICKET_URL
