from datetime import datetime

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.event import JsonLdEvent, Offer, Place, PostalAddress
from laughtrack.scrapers.implementations.api.seatengine_web.scraper import SeatEngineWebScraper
from laughtrack.utilities.domain.show.enhancement import ShowEnhancement


def _club() -> Club:
    source = ScrapingSource(
        id=571,
        club_id=850,
        platform="seatengine",
        scraper_key="seatengine_web",
        source_url="https://www.bananascomedyclub.com",
    )
    club = Club(
        id=850,
        name="Bananas Comedy Club",
        address="801 Rutherford Ave",
        website="https://www.bananascomedyclub.com",
        popularity=0,
        zip_code="07070",
        phone_number="",
        visible=True,
        scraping_sources=[source],
        active_scraping_source=source,
    )
    return club


def _config_html(config_json: str) -> str:
    return f"""
    <html>
      <body>
        <script>
        //<![CDATA[
        window.seat_engine_app_config = {config_json}
        //]]>
        </script>
      </body>
    </html>
    """


def test_extracts_available_seatengine_web_inventory_as_offers():
    html = _config_html(
        """
        {
          "showtime": {
            "sold_out": false,
            "inventories": [
              {"available": 193, "name": "General Admission", "title": "General Admission", "price": 2587, "service_charge": 599},
              {"available": 45, "name": "Reserved", "title": "Reserved", "price": 3415, "service_charge": 699}
            ]
          }
        }
        """
    )

    offers = SeatEngineWebScraper._extract_offers_from_app_config(
        html,
        "https://www.bananascomedyclub.com/shows/368164",
    )

    assert [(offer.name, offer.price, offer.availability) for offer in offers] == [
        ("General Admission", "31.86", "https://schema.org/InStock"),
        ("Reserved", "41.14", "https://schema.org/InStock"),
    ]
    assert {offer.url for offer in offers} == {"https://www.bananascomedyclub.com/shows/368164"}


def test_extracts_sold_out_seatengine_web_inventory_as_sold_out_offers():
    html = _config_html(
        """
        {
          "showtime": {
            "sold_out": true,
            "inventories": []
          }
        }
        """
    )

    offers = SeatEngineWebScraper._extract_offers_from_app_config(
        html,
        "https://www.bananascomedyclub.com/shows/362220",
    )

    assert len(offers) == 1
    assert offers[0].name == "General Admission"
    assert offers[0].price == "0.00"
    assert offers[0].availability == "https://schema.org/SoldOut"


def test_extracts_sold_out_offer_when_cart_config_is_absent():
    html = '<div class="se-show-form"><h1 style="text-align: right;">Currently<br>Sold Out</h1></div>'

    offers = SeatEngineWebScraper._extract_offers_from_app_config(
        html,
        "https://www.bananascomedyclub.com/shows/362220",
    )

    assert len(offers) == 1
    assert offers[0].name == "General Admission"
    assert offers[0].price == "0.00"
    assert offers[0].availability == "https://schema.org/SoldOut"


def test_offer_name_becomes_ticket_type_for_json_ld_tickets():
    event = JsonLdEvent(
        name="Nicky Smigs",
        start_date=datetime(2026, 5, 15, 19, 0),
        location=Place(
            name="Bananas Comedy Club",
            address=PostalAddress("", "", "", "", ""),
        ),
        offers=[
            Offer(
                url="https://www.bananascomedyclub.com/shows/368164",
                price_currency="USD",
                price="41.14",
                availability="https://schema.org/InStock",
                name="Reserved",
            )
        ],
        url="https://www.bananascomedyclub.com/shows/368164",
        description="",
    )

    tickets = ShowEnhancement.enhance_tickets_from_event(event)

    assert len(tickets) == 1
    assert tickets[0].type == "Reserved"
    assert tickets[0].price == 41.14
    assert tickets[0].purchase_url == "https://www.bananascomedyclub.com/shows/368164"
    assert tickets[0].sold_out is False


def test_seatengine_web_pipeline_persists_enriched_ticket_types():
    scraper = SeatEngineWebScraper(_club())
    html = _config_html(
        """
        {
          "showtime": {
            "sold_out": false,
            "inventories": [
              {"available": 10, "name": "Reserved", "title": "Reserved", "price": 3415, "service_charge": 699}
            ]
          }
        }
        """
    )
    offers = scraper._extract_offers_from_app_config(
        html,
        "https://www.bananascomedyclub.com/shows/368164",
    )
    event = JsonLdEvent(
        name="Nicky Smigs",
        start_date=datetime(2026, 5, 15, 19, 0),
        location=Place(
            name="Bananas Comedy Club",
            address=PostalAddress("", "", "", "", ""),
        ),
        offers=offers,
        url="https://www.bananascomedyclub.com/shows/368164",
        description="",
    )

    show = event.to_show(scraper.club)

    assert show is not None
    assert len(show.tickets) == 1
    assert show.tickets[0].type == "Reserved"
    assert show.tickets[0].price == 41.14
