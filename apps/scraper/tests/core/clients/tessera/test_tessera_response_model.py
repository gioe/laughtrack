from laughtrack.core.clients.tessera.models.response import TesseraAPIResponse


def test_tessera_api_response_from_dict_parses_sample_payload():
    sample = {
        "productId": "f0400afe-334b-f011-8f7d-000d3a906382",
        "inventorySold": 0,
        "inventoryWillCall": 0,
        "inventoryTotal": 0,
        "quantityRefunded": 0,
        "frontendId": "18152",
        "productName": "2025-08-30 Stand up comedy in New York City.  (5:30 pm)",
        "productCategory": "Show",
        "isLastCall": False,
        "isSoldOut": False,
        "campaigns": [
            {
                "campaignId": "e74a1507-344b-f011-8f7d-000d3a906382",
                "productId": "f0400afe-334b-f011-8f7d-000d3a906382",
                "productTypeId": "954a1507-344b-f011-8f7d-000d3a906382",
                "productTypeSortOrder": 0,
                "name": "Red Room - Standard",
                "description": None,
                "usesSeatingChart": False,
                "minimumPerOrder": None,
                "maximumPerOrder": None,
                "sortOrder": 0,
                "serviceFee": 2.62,
                "price": 25.00,
                "doorPrice": None,
                "discount": None,
                "imageUrl": "",
                "isOnSale": True,
                "isOnSaleType": "present",
                "onSaleStartDate": None,
                "onSaleEndDate": None,
                "isLastCall": False,
                "isSoldOut": False,
                "isVisible": False,
                "currentlyPasswordProtected": False,
                "seatingChartUrl": "",
            }
        ],
        "venueName": "Broadway Comedy Club",
        "eventDate": "2025-08-30T17:30:00",
        "seatingChartUrl": None,
        "headliners": None,
        "supportingActs": None,
        "category": None,
    }

    resp = TesseraAPIResponse.from_dict(sample)

    # Top-level fields
    assert resp.productId == sample["productId"]
    assert resp.inventorySold == 0
    assert resp.inventoryWillCall == 0
    assert resp.inventoryTotal == 0
    assert resp.quantityRefunded == 0
    assert resp.frontendId == "18152"
    assert resp.productName.startswith("2025-08-30 Stand up comedy")
    assert resp.productCategory == "Show"
    assert resp.isLastCall is False
    assert resp.isSoldOut is False

    # Campaigns
    assert isinstance(resp.campaigns, list)
    assert len(resp.campaigns) == 1
    c = resp.campaigns[0]
    assert c.campaignId == sample["campaigns"][0]["campaignId"]
    assert c.price == 25.0
    assert c.serviceFee == 2.62
    assert c.isOnSale is True
    assert c.isVisible is False

    # Venue and dates
    assert resp.venueName == "Broadway Comedy Club"
    assert resp.eventDate == "2025-08-30T17:30:00"
    # Convenience accessor parses ISO format
    assert resp.event_datetime is not None
    assert resp.event_datetime.year == 2025
    assert resp.event_datetime.month == 8
    assert resp.event_datetime.day == 30
    assert resp.event_datetime.hour == 17
    assert resp.event_datetime.minute == 30

    # Optionals normalize correctly
    assert resp.seatingChartUrl is None
    assert resp.headliners is None
    assert resp.supportingActs is None
    assert resp.category is None


def test_tessera_campaign_coercions_string_inputs():
    from laughtrack.core.clients.tessera.models.campaign import TesseraCampaign

    raw = {
        "campaignId": 123,  # coerced to str
        "productId": 456,
        "productTypeId": 789,
        "productTypeSortOrder": "2",
        "name": "GA",
        "description": " ",  # becomes None
        "usesSeatingChart": "true",
        "minimumPerOrder": "1",
        "maximumPerOrder": "",
        "sortOrder": "3",
        "serviceFee": "2.50",
        "price": "25",
        "doorPrice": "",
        "discount": None,
        "imageUrl": None,
        "isOnSale": "1",
        "isOnSaleType": None,
        "onSaleStartDate": "",
        "onSaleEndDate": None,
        "isLastCall": 0,
        "isSoldOut": "no",
        "isVisible": "false",
        "currentlyPasswordProtected": "yes",
        "seatingChartUrl": None,
    }

    c = TesseraCampaign.from_dict(raw)

    assert c.campaignId == "123"
    assert c.productId == "456"
    assert c.productTypeId == "789"
    assert c.productTypeSortOrder == 2
    assert c.name == "GA"
    assert c.description is None
    assert c.usesSeatingChart is True
    assert c.minimumPerOrder == 1
    assert c.maximumPerOrder is None
    assert c.sortOrder == 3
    assert c.serviceFee == 2.5
    assert c.price == 25.0
    assert c.doorPrice is None
    assert c.discount is None
    assert c.imageUrl == ""
    assert c.isOnSale is True
    assert c.isOnSaleType == ""
    assert c.onSaleStartDate is None
    assert c.onSaleEndDate is None
    assert c.isLastCall is False
    assert c.isSoldOut is False
    assert c.isVisible is False
    assert c.currentlyPasswordProtected is True
    assert c.seatingChartUrl == ""
