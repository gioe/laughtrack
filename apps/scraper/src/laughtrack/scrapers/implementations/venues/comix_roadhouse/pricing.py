"""Match public Leap offers to one linked Comix performance."""

import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit

from laughtrack.core.entities.event.comix_roadhouse import ComixRoadhouseEvent
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.foundation.utilities.json import JSONUtils
from laughtrack.scrapers.implementations.json_ld.extractor import EventExtractor
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils
from laughtrack.utilities.infrastructure.html.scraper import HtmlScraper

_ADMISSION = re.compile(r"\b(admission|vip|reserved|front row)\b", re.I)
_PACKAGE = re.compile(r"\b(package|bundle|table|dinner|food|beverage|drink|parking|donation|bogo|pair)\b", re.I)


def checkout_url(value: str) -> str:
    """Only fetch public Leap event pages; strip tracking and trailing slashes."""
    if not isinstance(value, str):
        return ""
    try:
        p = urlsplit(value)
        if p.scheme != "https" or p.netloc.lower() != "events.leapevents.com":
            return ""
        if not re.fullmatch(r"/event/[A-Za-z0-9_-]+/?", p.path):
            return ""
        return "https://events.leapevents.com" + p.path.rstrip("/")
    except ValueError:
        return ""


def _date(value):
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt if dt.tzinfo is not None else None
    except (ValueError, TypeError, AttributeError):
        return None


def _amount(value):
    try:
        amount = Decimal(str(value))
        return amount if amount.is_finite() and 0 < amount <= 1000000 else None
    except InvalidOperation:
        return None


def extract_checkout(
    html: str, event: ComixRoadhouseEvent, venue_timezone: str, now: datetime | None = None
) -> tuple[list[Ticket], list[str]]:
    expected = checkout_url(event.ticket_url)
    if not expected or not html:
        return [], []
    soup = HtmlScraper._parse_html(html)
    canonicals = soup.select('link[rel="canonical"]')
    if any(checkout_url(tag.get("href")) != expected for tag in canonicals):
        return [], []
    objects = JSONUtils.parse_json_ld_contents(HtmlScraper.get_json_ld_script_contents(html))
    matches = []
    for obj in objects:
        for candidate in EventExtractor._extract_objects_by_type(obj, "Event"):
            if checkout_url(candidate.get("url")) == expected and candidate not in matches:
                matches.append(candidate)
    # A reused URL with conflicting Event blocks is not reliable identity evidence.
    if len(matches) != 1:
        return [], []
    matched = matches[0]
    try:
        expected_date = ShowFactoryUtils.parse_datetime_with_timezone_fallback(event.start_date, venue_timezone)
    except ValueError:
        return [], []
    if _date(matched.get("startDate")) != expected_date:
        return [], []
    status = matched.get("eventStatus", "EventScheduled")
    if not isinstance(status, str) or status.rsplit("/", 1)[-1] != "EventScheduled":
        return [], []
    policies = list(
        dict.fromkeys(
            tag.get_text(" ", strip=True)
            for tag in soup.select('.purchase_wrapper.fee_disclosure, .event-spec[data-label="Ages"]')
            if tag.get_text(" ", strip=True)
        )
    )
    offers = matched.get("offers", [])
    offers = [offers] if isinstance(offers, dict) else offers
    if not isinstance(offers, list):
        return [], policies
    now = now or datetime.now(timezone.utc)
    tickets = []
    for offer in offers:
        if not isinstance(offer, dict) or offer.get("@type") != "Offer":
            continue
        if checkout_url(offer.get("url")) != expected or offer.get("category") != "primary":
            continue
        name = offer.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        currency = offer.get("priceCurrency")
        amount = _amount(offer.get("price"))
        availability = str(offer.get("availability", "")).rsplit("/", 1)[-1]
        start, end = _date(offer.get("validFrom")), _date(offer.get("validThrough"))
        available = availability == "InStock" and start is not None and end is not None and start <= now < end
        individual = bool(_ADMISSION.search(name)) and not _PACKAGE.search(name)
        # Quantity restrictions and package text invalidate a per-person minimum.
        individual = (
            individual and not offer.get("eligibleQuantity") and not _PACKAGE.search(str(offer.get("description", "")))
        )
        price = amount if currency == "USD" and available and individual else None
        label = name
        if amount is not None:
            label += f" ({currency or 'currency unspecified'} {amount} base)"
        if not available:
            label += " [not currently purchasable]"
        tickets.append(
            ShowFactoryUtils.create_fallback_ticket(
                event.ticket_url,
                price=float(price) if price is not None else None,
                ticket_type=label,
                sold_out=availability == "SoldOut",
            )
        )
    return tickets, policies
