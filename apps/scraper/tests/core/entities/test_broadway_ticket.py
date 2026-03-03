import sys
import types
import pytest

from laughtrack.core.entities.ticket.local.broadway import BroadwayTicket


class FakeCampaign:
    def __init__(self, **overrides):
        self.campaignId = overrides.get("campaignId", "c1")
        self.productId = overrides.get("productId", "p1")
        self.productTypeId = overrides.get("productTypeId", "pt1")
        self.productTypeSortOrder = overrides.get("productTypeSortOrder", 1)
        self.name = overrides.get("name", "General Admission")
        self.description = overrides.get("description", None)
        self.usesSeatingChart = overrides.get("usesSeatingChart", False)
        self.minimumPerOrder = overrides.get("minimumPerOrder", None)
        self.maximumPerOrder = overrides.get("maximumPerOrder", None)
        self.sortOrder = overrides.get("sortOrder", 1)
        self.serviceFee = overrides.get("serviceFee", 2.5)
        self.price = overrides.get("price", 25.0)
        self.doorPrice = overrides.get("doorPrice", None)
        self.discount = overrides.get("discount", None)
        self.imageUrl = overrides.get("imageUrl", "https://cdn.example/img.jpg")
        self.isOnSale = overrides.get("isOnSale", True)
        self.isOnSaleType = overrides.get("isOnSaleType", "public")
        self.onSaleStartDate = overrides.get("onSaleStartDate", None)
        self.onSaleEndDate = overrides.get("onSaleEndDate", None)
        self.isLastCall = overrides.get("isLastCall", False)
        self.isSoldOut = overrides.get("isSoldOut", False)
        self.isVisible = overrides.get("isVisible", True)
        self.currentlyPasswordProtected = overrides.get("currentlyPasswordProtected", False)
        self.seatingChartUrl = overrides.get("seatingChartUrl", "")


def make_campaign(**overrides) -> FakeCampaign:
    return FakeCampaign(**overrides)


@pytest.fixture(autouse=True)
def stub_ticket_module(monkeypatch):
    """Stub Ticket used by BroadwayTicket.to_ticket to avoid heavy imports."""
    mod_name = "laughtrack.core.entities.ticket.model"
    dummy = types.ModuleType(mod_name)

    class DummyTicket:
        def __init__(self, price: float, purchase_url: str, sold_out: bool, type: str):
            self.price = price
            self.purchase_url = purchase_url
            self.sold_out = sold_out
            self.type = type

    dummy.Ticket = DummyTicket  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, mod_name, dummy)
    yield


def test_from_tessera_campaign_builds_purchase_url_from_seating_chart():
    campaign = make_campaign(seatingChartUrl="https://tickets.broadwaycomedyclub.com/event/18155")

    adapter = BroadwayTicket.from_tessera_campaign(
        campaign, event_id="18155", base_domain="broadwaycomedyclub.com"
    )

    assert adapter.purchase_url == "https://tickets.broadwaycomedyclub.com/event/18155"
    assert adapter.campaign_id == campaign.campaignId
    assert adapter.product_id == campaign.productId
    assert adapter.price == campaign.price
    assert adapter.is_sold_out is False


def test_from_tessera_campaign_falls_back_to_conventional_url():
    campaign = make_campaign(seatingChartUrl="")

    adapter = BroadwayTicket.from_tessera_campaign(
        campaign, event_id="18156", base_domain="broadwaycomedyclub.com"
    )

    assert adapter.purchase_url == "https://tickets.broadwaycomedyclub.com/event/18156"


def test_to_ticket_converts_fields_correctly():
    campaign = make_campaign(name="VIP", price=40.0, isSoldOut=True)
    adapter = BroadwayTicket.from_tessera_campaign(
        campaign, event_id="18157", base_domain="broadwaycomedyclub.com"
    )

    ticket = adapter.to_ticket()
    assert ticket.price == 40.0
    assert ticket.type == "VIP"
    assert ticket.sold_out is True
    assert ticket.purchase_url.startswith("https://tickets.broadwaycomedyclub.com/event/")
