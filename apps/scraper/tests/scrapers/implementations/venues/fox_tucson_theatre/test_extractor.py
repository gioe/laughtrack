from datetime import date

from laughtrack.scrapers.implementations.venues.fox_tucson_theatre.extractor import (
    FoxTucsonTheatreExtractor,
)


LISTING_HTML = """
<div class="event-card col-12 col-sm-6 outburst-comedy ">
  <div class="event-card-upper" onclick="location.href='https://foxtucson.com/event/leslie-jones/';">
    <div class="details">
      <a class="white" href="https://foxtucson.com/event/leslie-jones/">
        <h1>Leslie Jones: I'm Hot Tour</h1>
      </a>
    </div>
  </div>
  <div class="event-card-lower">
    <div class="date">
      <div class="day-of-month">18</div>
      <div class="month-time">
        <div class="month">September</div>
        <div class="time">7:30 pm</div>
      </div>
    </div>
    <div class="tickets">
      <a class="btn btn-red" href="https://foxtucson.com/event/leslie-jones/tickets">$24-$76 all in</a>
    </div>
  </div>
</div>
<div class="event-card col-12 col-sm-6 music ">
  <div class="details">
    <a href="https://foxtucson.com/event/not-comedy/"><h1>Music Event</h1></a>
  </div>
  <div class="event-card-lower">
    <div class="date"><div class="day-of-month">20</div><div class="month">September</div><div class="time">8:00 pm</div></div>
    <div class="tickets"><a href="https://foxtucson.com/event/not-comedy/tickets">$10</a></div>
  </div>
</div>
"""


def test_extract_events_reads_official_comedy_card_fields():
    events = FoxTucsonTheatreExtractor.extract_events(
        LISTING_HTML,
        "https://foxtucson.com/events/",
        reference_date=date(2026, 5, 18),
    )

    assert len(events) == 1
    event = events[0]
    assert event.title == "Leslie Jones: I'm Hot Tour"
    assert event.date_time.isoformat() == "2026-09-18T19:30:00"
    assert event.show_page_url == "https://foxtucson.com/event/leslie-jones/"
    assert event.ticket_url == "https://foxtucson.com/event/leslie-jones/tickets"
    assert event.price_text == "$24-$76 all in"


def test_extract_spektrix_iframe_url_reads_wordpress_ticket_page():
    html = """
    <iframe id="SpektrixIFrame" name="SpektrixIFrame"
      src="https://tickets.foxtucson.com/foxtucsontheatre/website/EventDetails.aspx?WebEventId=leslie-jones&amp;resize=true">
    </iframe>
    """

    url = FoxTucsonTheatreExtractor.extract_spektrix_iframe_url(
        html, "https://foxtucson.com/event/leslie-jones/tickets"
    )

    assert url == (
        "https://tickets.foxtucson.com/foxtucsontheatre/website/"
        "EventDetails.aspx?WebEventId=leslie-jones&resize=true"
    )
    assert FoxTucsonTheatreExtractor.extract_web_event_id(url) == "leslie-jones"


def test_extract_spektrix_instance_ids_reads_event_dates_list():
    html = """
    <select name="ctl00$ContentPlaceHolder$InstanceList"
      id="ctl00_ContentPlaceHolder_InstanceList"
      class="EventDatesList" aria-label="Event Dates">
      <option value="165401">Fri Sep 18, 2026 - 7:30 PM</option>
      <option value="169401">Fri Oct 02, 2026 - 7:30 PM</option>
    </select>
    """

    assert FoxTucsonTheatreExtractor.extract_spektrix_instance_ids(html) == ["165401", "169401"]
