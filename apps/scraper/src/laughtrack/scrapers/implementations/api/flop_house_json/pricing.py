"""Admission minima from the exact Eventbrite performance linked by the feed."""

import json
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit

from laughtrack.core.entities.event.flop_house_json import FlopHouseJsonEvent
from laughtrack.foundation.utilities.json import JSONUtils
from laughtrack.scrapers.implementations.json_ld.extractor import EventExtractor
from laughtrack.utilities.infrastructure.html.scraper import HtmlScraper

_PACKAGE = re.compile(r"\b(package|bundle|table|donation|parking|bogo|pair|group)\b|\b\d+\s+tickets\b|\b\d+\s*for\s*\d+\b", re.I)


def eventbrite_id(value: str) -> str | None:
    """Allow slug redirects while requiring a public HTTPS Eventbrite ticket ID."""
    if not isinstance(value, str):
        return None
    try:
        parsed = urlsplit(value)
        if parsed.scheme != "https" or parsed.netloc.lower() not in {"www.eventbrite.com", "eventbrite.com"}:
            return None
        match = re.fullmatch(r"/e/(?:[\w-]+-)?tickets-(\d+)/?", parsed.path)
        return match.group(1) if match else None
    except ValueError:
        return None


def _date(value):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo is not None else None
    except (ValueError, TypeError, AttributeError):
        return None


def _amount(value):
    try:
        parsed = Decimal(str(value))
        return parsed if parsed.is_finite() and 0 < parsed < 1_000_000 else None
    except InvalidOperation:
        return None


def extract_admission(html: str, event: FlopHouseJsonEvent, now: datetime | None = None) -> tuple[float, str] | None:
    """Return an advertised USD minimum, never a guessed tier or fee breakdown."""
    expected_id = eventbrite_id(event.show_page_url)
    if not html or not expected_id:
        return None
    now = now or datetime.now(timezone.utc)
    expected_start = datetime.fromtimestamp(event.start_ms / 1000, timezone.utc)
    if expected_start <= now:
        return None
    soup = HtmlScraper._parse_html(html)
    if any(eventbrite_id(tag.get("href")) != expected_id for tag in soup.select('link[rel="canonical"]')):
        return None
    # Eventbrite can advertise a donation minimum in its aggregate. Honor the
    # page's explicit donation/external-ticket flags when the context exists.
    context_script = soup.select_one("script#__NEXT_DATA__")
    if context_script:
        try:
            basic = json.loads(context_script.string or context_script.get_text())["props"]["pageProps"]["context"]["basicInfo"]
            if str(basic.get("id")) != expected_id or basic.get("hasDonationTicketsAvailable") or basic.get("hasExternalTickets"):
                return None
        except (ValueError, KeyError, TypeError, AttributeError):
            return None
    objects = JSONUtils.parse_json_ld_contents(HtmlScraper.get_json_ld_script_contents(html))
    matches = []
    for obj in objects:
        for candidate in EventExtractor._extract_objects_by_type(obj, "Event"):
            if eventbrite_id(candidate.get("url")) == expected_id and candidate not in matches:
                matches.append(candidate)
    if len(matches) != 1:
        return None
    matched = matches[0]
    if _date(matched.get("startDate")) != expected_start:
        return None
    if str(matched.get("eventStatus", "")).rsplit("/", 1)[-1] != "EventScheduled":
        return None
    if _PACKAGE.search(str(matched.get("name", ""))):
        return None
    offers = matched.get("offers")
    offers = [offers] if isinstance(offers, dict) else offers
    # Multiple aggregates or nested tiers need their own unit/availability
    # interpretation. Refuse ambiguity rather than take a global minimum.
    if not isinstance(offers, list) or len(offers) != 1 or not isinstance(offers[0], dict):
        return None
    offer = offers[0]
    if offer.get("@type") != "AggregateOffer" or eventbrite_id(offer.get("url")) != expected_id:
        return None
    if offer.get("priceCurrency") != "USD" or str(offer.get("availability", "")).rsplit("/", 1)[-1] != "InStock":
        return None
    if offer.get("offers") or offer.get("eligibleQuantity") or _PACKAGE.search(
        f"{offer.get('name', '')} {offer.get('description', '')}"
    ):
        return None
    starts, ends = _date(offer.get("availabilityStarts")), _date(offer.get("availabilityEnds"))
    if starts is None or ends is None or not starts <= now < ends:
        return None
    for key in ("validFrom", "validThrough"):
        if key in offer:
            date = _date(offer[key])
            if date is None or (key == "validFrom" and now < date) or (key == "validThrough" and now >= date):
                return None
    low, high = _amount(offer.get("lowPrice")), _amount(offer.get("highPrice"))
    if low is None or high is None or low > high:
        return None
    amount_text = f"USD {low}" if low == high else f"USD {low}–{high}"
    return float(low), f"Admission — advertised minimum ({amount_text})"
