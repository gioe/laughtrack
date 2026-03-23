"""
Data model for a single event from Rodney's Comedy Club.

This model represents event data parsed from HTML pages with JSON-LD.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from laughtrack.core.entities.event.event import JsonLdEvent


@dataclass
class RodneyEvent:
    """Data model representing a single event from Rodney's Comedy Club."""

    # Core required fields
    id: str
    title: str
    date_time: datetime
    source_url: str
    source_type: str  # "html"

    # Optional fields
    description: Optional[str] = None
    performers: Optional[List[str]] = None
    ticket_info: Optional[Dict[str, Any]] = None
    location: Optional[str] = None
    image_url: Optional[str] = None

    # Raw data preservation for debugging
    _raw_data: Optional[Dict[str, Any]] = None

    @classmethod
    def from_html_event(cls, event: JsonLdEvent, source_url: str) -> "RodneyEvent":
        """Create a RodneyEvent from an HTML JSON-LD Event object."""
        return cls(
            id=cls._generate_id_from_url(source_url),
            title=event.name,
            date_time=event.start_date,
            source_url=source_url,
            source_type="html",
            description=event.description,
            performers=[p.name for p in event.performers] if event.performers else None,
            ticket_info=cls._extract_ticket_info_from_offers(event.offers),
            location=event.location.name if event.location else None,
            image_url=event.image,
            _raw_data=event.__dict__,
        )

    @classmethod
    def from_22rams_data(cls, data: Dict[str, Any], source_url: str) -> "RodneyEvent":
        """Create a RodneyEvent from 22Rams API data."""
        return cls(
            id=str(data.get("id", cls._generate_id_from_url(source_url))),
            title=data.get("title", "Unknown Event"),
            date_time=datetime.fromisoformat(data.get("datetime", "").replace("Z", "+00:00")),
            source_url=source_url,
            source_type="22rams",
            description=data.get("description"),
            performers=data.get("performers", []),
            ticket_info=cls._extract_22rams_ticket_info(data),
            location=data.get("venue"),
            image_url=data.get("image"),
            _raw_data=data,
        )

    @staticmethod
    def _generate_id_from_url(url: str) -> str:
        """Generate a unique ID from URL when no ID is available."""
        segments = [s for s in url.rstrip("/").split("/") if s]
        if not segments:
            raise ValueError(f"Cannot generate ID: no path segments in URL '{url}'")
        return segments[-1]

    @staticmethod
    def _extract_ticket_info_from_offers(offers: List[Any]) -> Optional[Dict[str, Any]]:
        """Extract ticket information from JSON-LD offers."""
        if not offers:
            return None

        ticket_info = {}
        for offer in offers:
            if hasattr(offer, "price") and offer.price:
                ticket_info["price"] = offer.price
            if hasattr(offer, "price_currency") and offer.price_currency:
                ticket_info["currency"] = offer.price_currency
            if hasattr(offer, "url") and offer.url:
                ticket_info["purchase_url"] = offer.url
            if hasattr(offer, "availability") and offer.availability:
                ticket_info["availability"] = offer.availability

        return ticket_info if ticket_info else None

    @staticmethod
    def _extract_22rams_ticket_info(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract ticket information from 22Rams data."""
        pricing = data.get("pricing", {})
        if not pricing:
            return None

        return {
            "min_price": pricing.get("min_price"),
            "max_price": pricing.get("max_price"),
            "currency": pricing.get("currency", "USD"),
            "purchase_url": data.get("ticket_url"),
        }
