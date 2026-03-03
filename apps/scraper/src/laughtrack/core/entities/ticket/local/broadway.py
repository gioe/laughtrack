"""Broadway ticket adapter for Tessera → Ticket conversion.

This model acts as an intermediate adapter between TesseraCampaign (raw venue API)
and our internal Ticket entity. Keep TesseraCampaign as a pure wire model and use
this adapter to shape and convert the relevant fields.
"""

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING, Protocol

class CampaignLike(Protocol):
   campaignId: str
   productId: str
   productTypeId: str
   name: str
   imageUrl: str
   price: float
   serviceFee: float
   doorPrice: Optional[float]
   discount: Optional[float]
   isOnSale: bool
   isSoldOut: bool
   isVisible: bool
   minimumPerOrder: Optional[int]
   maximumPerOrder: Optional[int]
   usesSeatingChart: bool
   seatingChartUrl: str

   # Optional/extra fields we don't rely on but exist in Tessera payload
   productTypeSortOrder: int
   sortOrder: int
   description: Optional[str]
   isOnSaleType: str
   onSaleStartDate: Optional[str]
   onSaleEndDate: Optional[str]
   isLastCall: bool
   currentlyPasswordProtected: bool


if TYPE_CHECKING:
   # Only import for type checking to avoid heavy runtime imports
   from laughtrack.core.clients.tessera.models.campaign import TesseraCampaign
   from laughtrack.core.entities.ticket.model import Ticket


@dataclass
class BroadwayTicket:
   """Intermediate model holding Tessera campaign info for Broadway.

   Stores the key fields we care about and provides a to_ticket() converter.
   """

   # Identification
   campaign_id: str
   product_id: str
   product_type_id: str

   # Presentation
   name: str
   image_url: Optional[str]

   # Pricing / state
   price: float
   service_fee: float
   door_price: Optional[float]
   discount: Optional[float]
   is_on_sale: bool
   is_sold_out: bool
   is_visible: bool

   # Limits / seating
   minimum_per_order: Optional[int]
   maximum_per_order: Optional[int]
   uses_seating_chart: bool
   seating_chart_url: Optional[str]

   # Computed
   purchase_url: str

   @staticmethod
   def _build_purchase_url(
      *, base_domain: str, event_id: str, seating_chart_url: Optional[str]
   ) -> str:
      """Best-effort construction of a usable purchase URL.

      Preference order:
      1) seating_chart_url from campaign/response if provided
      2) tickets.{base_domain}/event/{event_id} as a sane Tessera default
      """
      if seating_chart_url and seating_chart_url.strip():
         return seating_chart_url.strip()
      # Fallback to a conventional Tessera event URL pattern
      return f"https://tickets.{base_domain}/event/{event_id}"

   @classmethod
   def from_tessera_campaign(
      cls,
      campaign: CampaignLike,
      *,
      event_id: str,
      base_domain: str,
      fallback_seating_chart_url: Optional[str] = None,
   ) -> "BroadwayTicket":
      """Create a BroadwayTicket from a TesseraCampaign plus context.

      Args:
         campaign: Raw Tessera campaign object
         event_id: Event identifier used by Tessera frontend
         base_domain: Venue base domain (e.g., "broadwaycomedyclub.com")
         fallback_seating_chart_url: Optional event-level seating chart URL
      """
      purchase_url = cls._build_purchase_url(
         base_domain=base_domain,
         event_id=event_id,
         seating_chart_url=campaign.seatingChartUrl or fallback_seating_chart_url,
      )

      return cls(
         # IDs
            campaign_id=str(campaign.campaignId),
            product_id=str(campaign.productId),
            product_type_id=str(campaign.productTypeId),
         # Presentation
            name=(campaign.name or "General Admission"),
            image_url=(campaign.imageUrl or None),
         # Pricing/state
            price=float(campaign.price or 0.0),
            service_fee=float(campaign.serviceFee or 0.0),
         door_price=float(campaign.doorPrice) if campaign.doorPrice is not None else None,
         discount=float(campaign.discount) if campaign.discount is not None else None,
         is_on_sale=bool(campaign.isOnSale),
         is_sold_out=bool(campaign.isSoldOut),
         is_visible=bool(campaign.isVisible),
         # Limits/seating
         minimum_per_order=campaign.minimumPerOrder,
         maximum_per_order=campaign.maximumPerOrder,
         uses_seating_chart=bool(campaign.usesSeatingChart),
         seating_chart_url=(campaign.seatingChartUrl or fallback_seating_chart_url or None),
         # Computed
         purchase_url=purchase_url,
      )

   # Conversion
   def to_ticket(self) -> "Ticket":
      """Convert this adapter into a standardized Ticket entity."""
      # Local import to avoid importing foundation-heavy modules during test collection
      from laughtrack.core.entities.ticket.model import Ticket
      return Ticket(
         price=float(self.price or 0.0),
         purchase_url=self.purchase_url,
         sold_out=bool(self.is_sold_out),
         # Use campaign name as the ticket type label; fallback to GA
         type=self.name or "General Admission",
      )