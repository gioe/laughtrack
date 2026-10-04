"""Extract physical UCB admissions only after matching the dated event identity."""

import math
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.ucb import UCBAdmission, UCBEvent
from laughtrack.foundation.utilities.json import JSONUtils
from laughtrack.foundation.utilities.number import parse_price_text
from laughtrack.utilities.infrastructure.html.scraper import HtmlScraper

_REMOTE = re.compile(r"live\s*stream|online|virtual|on[ -]demand|/watch(?:/|$)", re.I)
_ADMISSION = re.compile(
    r"(?:general|free) admission|in[ -]person(?: tickets?)?|advance|(?:at the )?door|day.of.show", re.I
)
_AMOUNT = r"\$\d+(?:\.\d{1,2})?"


def _url_key(value: str) -> tuple:
    parsed = urlparse(value)
    return parsed.hostname, parsed.path.rstrip("/")


def _amount(value) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or amount < 0:
            return None
        result = float(amount)
        return result if math.isfinite(result) else None
    except (InvalidOperation, ValueError, OverflowError):
        return None


def extract_admissions(html: str, event: UCBEvent, club: Club) -> list[UCBAdmission]:
    """Never select an unrelated Event or the cheaper livestream minimum."""
    if _url_key(event.show_page_url)[0] != "ucbcomedy.com":
        return []
    objects = JSONUtils.parse_json_ld_contents(HtmlScraper.get_json_ld_script_contents(html))
    matches = []
    for obj in objects:
        if not isinstance(obj, dict) or obj.get("@type") not in ("Event", "ComedyEvent"):
            continue
        if not isinstance(obj.get("url"), str) or _url_key(obj["url"]) != _url_key(event.show_page_url):
            continue
        try:
            start = datetime.fromisoformat(obj.get("startDate", "").replace("Z", "+00:00"))
            if start.tzinfo is None or start != event.start_datetime(club):
                continue
        except (ValueError, TypeError, AttributeError):
            continue
        locations = obj.get("location", [])
        if isinstance(locations, dict):
            locations = [locations]
        if not isinstance(locations, list) or not any(
            isinstance(place, dict)
            and place.get("@type") == "Place"
            and str(place.get("name", "")).casefold() == event.location_name.casefold()
            and isinstance(place.get("address"), dict)
            and place["address"].get("addressCountry") == "US"
            for place in locations
        ):
            continue
        if str(obj.get("eventAttendanceMode", "")).endswith("OnlineEventAttendanceMode"):
            continue
        if str(obj.get("eventStatus", "")).rsplit("/", 1)[-1] != "EventScheduled":
            continue
        matches.append(obj)
    if len(matches) != 1:
        return []

    obj = matches[0]
    soup = BeautifulSoup(html, "html.parser")
    offers = obj.get("offers", [])
    if isinstance(offers, dict):
        offers = [offers]
    if not isinstance(offers, list):
        return []
    physical = [
        offer
        for offer in offers
        if isinstance(offer, dict) and not _REMOTE.search(str(offer.get("name", "")) + " " + str(offer.get("url", "")))
    ]
    if physical:
        admissions = []
        names = set()
        for offer in physical:
            name = str(offer.get("name") or "")
            if not _ADMISSION.fullmatch(name) or name.casefold() in names:
                return []  # packages and conflicting duplicate tiers remain unknown
            names.add(name.casefold())
            if not isinstance(offer.get("url"), str) or _url_key(offer["url"]) != _url_key(event.show_page_url):
                return []
            currency = offer.get("priceCurrency")
            availability = str(offer.get("availability", "")).rsplit("/", 1)[-1]
            price = _amount(offer.get("price")) if currency == "USD" and availability == "InStock" else None
            if price == 0 and not (name.casefold() == "free admission" or obj.get("isAccessibleForFree") is True):
                price = None
            fee_policy = "unspecified"
            for tier in soup.select(".ucb-event-ticket-picker .ucb-pass-tier"):
                label = tier.select_one(".ucb-pass-tier__name")
                control = tier.select_one("input[data-price]")
                if label and control and label.get_text(strip=True) == name:
                    if control.get("data-livestream") == "1" or control.has_attr("disabled"):
                        price = None
                    elif _amount(control.get("data-price")) == price:
                        note = tier.select_one(".ucb-pass-tier__allin-note")
                        if note and note.get_text(strip=True).casefold() == "incl. fees":
                            fee_policy = "included"
                    else:
                        price = None
            admissions.append(UCBAdmission(name, price, str(currency or ""), fee_policy, availability == "SoldOut"))
        return admissions

    # Restrict text fallback to exact admission sentences in the description.
    # Generic marketing mentions of "sold out audiences" must not mark stock.
    ticket_area = soup.select_one(".ucb-tickera-tickets")
    if ticket_area and re.search(r"\bsold[ -]out\b", ticket_area.get_text(" ", strip=True), re.I):
        return [UCBAdmission("General Admission", None, sold_out=True)]
    candidates = []
    for paragraph in soup.select(".ucb-event-description p"):
        text = paragraph.get_text(" ", strip=True)
        if _REMOTE.search(text):
            continue
        single = re.fullmatch(rf"In-person tickets are ({_AMOUNT})( plus fees)?\.?", text, re.I)
        tiers = re.fullmatch(rf"Tickets:\s*({_AMOUNT}) in advance,\s*({_AMOUNT}) on the day of the show\.?", text, re.I)
        if single:
            candidates.append(
                [
                    UCBAdmission(
                        "General Admission",
                        parse_price_text(single[1]),
                        fee_policy="additional" if single[2] else "unspecified",
                    )
                ]
            )
        elif tiers:
            candidates.append(
                [
                    UCBAdmission("Advance", parse_price_text(tiers[1])),
                    UCBAdmission("Door", parse_price_text(tiers[2])),
                ]
            )
    return candidates[0] if len(candidates) == 1 else []
