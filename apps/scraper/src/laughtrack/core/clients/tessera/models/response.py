"""
Tessera API type definitions.

This module contains dataclasses and type definitions specifically for
Tessera ticketing system API responses and data structures.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional

from laughtrack.foundation.models.types import JSONDict
from laughtrack.foundation.utilities.coercion import CoercionUtils as C

from .campaign import TesseraCampaign


@dataclass
class TesseraAPIResponse:
    """Tessera API response structure for event ticket data."""

    productId: str
    inventorySold: int
    inventoryWillCall: int
    inventoryTotal: int
    quantityRefunded: int
    frontendId: str
    productName: str
    productCategory: str
    isLastCall: bool
    isSoldOut: bool
    campaigns: List[TesseraCampaign]
    venueName: str
    eventDate: str
    seatingChartUrl: Optional[str]
    headliners: Optional[str]
    supportingActs: Optional[str]
    category: Optional[str]

    # ------------------------------
    # Factories / Parsing
    # ------------------------------
    @staticmethod
    def from_dict(data: JSONDict) -> "TesseraAPIResponse":
        """Create a TesseraAPIResponse from a raw API dict with safe coercions.

        Notes:
        - Coerces ints/floats/bools when backend sends numbers as strings
        - Normalizes empty strings for optional fields to None
        - Ensures campaigns is always a list
        """

        raw_campaigns = data.get("campaigns") or []
        campaigns: List[TesseraCampaign] = []
        if isinstance(raw_campaigns, list):
            for c in raw_campaigns:
                if isinstance(c, dict):
                    campaigns.append(TesseraCampaign.from_dict(c))

        return TesseraAPIResponse(
            productId=C.str_or_default(data.get("productId")),
            inventorySold=C.to_int(data.get("inventorySold")),
            inventoryWillCall=C.to_int(data.get("inventoryWillCall")),
            inventoryTotal=C.to_int(data.get("inventoryTotal")),
            quantityRefunded=C.to_int(data.get("quantityRefunded")),
            frontendId=C.str_or_default(data.get("frontendId")),
            productName=C.str_or_default(data.get("productName")),
            productCategory=C.str_or_default(data.get("productCategory")),
            isLastCall=C.to_bool(data.get("isLastCall"), False),
            isSoldOut=C.to_bool(data.get("isSoldOut"), False),
            campaigns=campaigns,
            venueName=C.str_or_default(data.get("venueName")),
            eventDate=C.str_or_default(data.get("eventDate")),
            seatingChartUrl=C.str_or_none(data.get("seatingChartUrl")),
            headliners=C.str_or_none(data.get("headliners")),
            supportingActs=C.str_or_none(data.get("supportingActs")),
            category=C.str_or_none(data.get("category")),
        )

    # ------------------------------
    # Convenience accessors
    # ------------------------------
    @property
    def event_datetime(self) -> Optional[datetime]:
        """Return parsed eventDate as naive datetime if available and valid.

        The Tessera payload provides ISO-like datetime strings without timezone,
        e.g., "2025-08-30T17:30:00". This returns a naive datetime or None on failure.
        """
        if not self.eventDate:
            return None
        try:
            return datetime.fromisoformat(self.eventDate)
        except Exception:
            return None
