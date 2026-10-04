"""Match native Ticket Tailor detail offers to one listing performance."""

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from laughtrack.core.entities.event.ticket_tailor import TicketTailorEvent, TicketTailorOffer
from laughtrack.foundation.utilities.json.utils import JSONUtils
from laughtrack.scrapers.implementations.json_ld.extractor import EventExtractor
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils
from laughtrack.utilities.infrastructure.html.scraper import HtmlScraper

_EVENT_PATH = re.compile(r"/events/[^/]+/\d+/?$")
_PACKAGE = re.compile(r"\b(table|package|bundle|group|couple|pair)\b|\bfor\s+\d+", re.I)
_EXTRA = re.compile(r"\b(donation|parking|merchandise|t-shirt|drink|meal|add-on)\b", re.I)


def _identity(url: str):
    try:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname or not _EVENT_PATH.fullmatch(parsed.path):
            return None
        return parsed.netloc.lower(), parsed.path.rstrip("/")
    except (ValueError, TypeError, AttributeError):
        return None


def extract_offers(html: str, event: TicketTailorEvent) -> list[TicketTailorOffer]:
    """Require URL identity and exact aware startDate; never infer a currency."""
    identity = _identity(event.event_url)
    if identity is None or not event.timezone:
        return []
    start = ShowFactoryUtils.parse_datetime_with_timezone_fallback(
        event.start.strftime("%Y-%m-%d %H:%M:%S"), event.timezone
    )
    if start is None or start.tzinfo is None:
        return []
    identities = {identity}
    # Native accounts can redirect to a custom box-office host. Accept only
    # the canonical alias actually declared by this fetched detail document.
    canonical = BeautifulSoup(html, "html.parser").select_one('link[rel="canonical"]')
    alias = _identity(canonical.get("href", "")) if canonical else None
    if alias and alias[1] == identity[1]:
        identities.add(alias)
    results = []
    objects = JSONUtils.parse_json_ld_contents(HtmlScraper.get_json_ld_script_contents(html))
    for obj in objects:
        for source in EventExtractor._extract_objects_by_type(obj, "Event"):
            try:
                source_start = datetime.fromisoformat(source.get("startDate", "").replace("Z", "+00:00"))
            except (ValueError, TypeError, AttributeError):
                continue
            if source_start.tzinfo is None or source_start != start:
                continue
            if source.get("url") and _identity(source["url"]) not in identities:
                continue
            status = str(source.get("eventStatus", "")).rsplit("/", 1)[-1]
            if status and status != "EventScheduled":
                continue
            offers = source.get("offers", [])
            if isinstance(offers, dict):
                offers = [offers]
            if not isinstance(offers, list):
                continue
            for offer in offers:
                if not isinstance(offer, dict) or offer.get("@type") != "Offer":
                    continue
                name = offer.get("name")
                if not isinstance(name, str) or not name.strip() or _EXTRA.search(name):
                    continue
                if _identity(offer.get("url")) not in identities:
                    continue
                try:
                    amount = Decimal(str(offer.get("price")))
                    if not amount.is_finite() or amount <= 0 or amount > Decimal("1000000"):
                        amount = None
                except InvalidOperation:
                    amount = None
                currency = offer.get("priceCurrency")
                currency = currency.strip().upper() if isinstance(currency, str) else ""
                availability = str(offer.get("availability") or "").rsplit("/", 1)[-1]
                result = TicketTailorOffer(
                    name.strip(), amount, currency, availability, offer["url"], bool(_PACKAGE.search(name))
                )
                if result not in results:
                    results.append(result)
    # Conflicting definitions of the same named tier cannot be persisted
    # reliably (tickets are unique by show/type); leave those tiers unknown.
    names = [offer.name for offer in results]
    return [offer for offer in results if names.count(offer.name) == 1]
