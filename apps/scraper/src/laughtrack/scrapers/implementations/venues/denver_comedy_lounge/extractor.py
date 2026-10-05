"""Extractor for Denver Comedy Lounge's /shows ItemList page."""

import re
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo
from laughtrack.core.clients.rsc.extractor import extract_push_payloads, extract_balanced
from typing import Any, List, Optional
from urllib.parse import urlparse

from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.json.utils import JSONUtils
from laughtrack.utilities.infrastructure.html.scraper import HtmlScraper

from .data import DenverComedyLoungeShow

# Each show detail slug encodes weekday, start time, and date, e.g.
# ``friday-7pm-2026-06-26`` or ``saturday-10pm-2026-09-19``.
_SLUG_RE = re.compile(r"^[a-z]+-(\d{1,2})(am|pm)-(\d{4})-(\d{2})-(\d{2})$")


class DenverComedyLoungeExtractor:
    """Parse the venue's /shows page into DenverComedyLoungeShow objects.

    The page server-renders a schema.org ``ItemList`` whose ``itemListElement``
    entries each carry a ``name`` (the show title, with a human date suffix) and
    a detail ``url``. The per-show date/time is not in the JSON-LD body — it is
    encoded in the detail URL slug — so the extractor derives the datetime from
    the slug and keeps the title (minus its trailing date suffix).
    """

    @staticmethod
    def extract_shows(html_content: str) -> List[DenverComedyLoungeShow]:
        """Extract show rows from the /shows page HTML.

        Returns an empty list when the page is missing, carries no ItemList, or
        no item slug parses — letting the scraper surface an empty extraction
        rather than raising.
        """
        if not html_content:
            return []

        script_contents = HtmlScraper.get_json_ld_script_contents(html_content)
        if not script_contents:
            return []

        json_objects = JSONUtils.parse_json_ld_contents(script_contents)
        if not json_objects:
            return []

        shows: List[DenverComedyLoungeShow] = []
        seen: set = set()
        for obj in json_objects:
            for item in DenverComedyLoungeExtractor._item_list_elements(obj):
                show = DenverComedyLoungeExtractor._build_show(item)
                if show and show.show_page_url not in seen:
                    seen.add(show.show_page_url)
                    shows.append(show)

        return shows

    @staticmethod
    def _item_list_elements(obj: Any) -> List[dict]:
        """Return itemListElement entries from any ItemList in a JSON-LD object."""
        if not isinstance(obj, dict):
            return []
        type_value = obj.get("@type")
        types = type_value if isinstance(type_value, list) else [type_value]
        if "ItemList" not in types:
            return []
        elements = obj.get("itemListElement")
        return [e for e in elements if isinstance(e, dict)] if isinstance(elements, list) else []

    @staticmethod
    def _build_show(element: dict) -> Optional[DenverComedyLoungeShow]:
        """Build a show from one ListItem, or None when its slug doesn't parse."""
        item = element.get("item")
        if not isinstance(item, dict):
            return None

        url = (item.get("url") or "").strip()
        name = (item.get("name") or "").strip()
        if not url or not name:
            return None

        slug = urlparse(url).path.rstrip("/").rsplit("/", 1)[-1]
        match = _SLUG_RE.match(slug)
        if not match:
            Logger.warn(
                f"DenverComedyLoungeExtractor: unparseable show slug {slug!r} ({url})"
            )
            return None

        hour_12, meridiem, year, month, day = match.groups()
        hour = DenverComedyLoungeExtractor._to_24h(int(hour_12), meridiem)
        datetime_str = f"{year}-{month}-{day} {hour:02d}:00:00"

        # Item names carry a human date suffix ("Friday Night Comedy — Jun 26");
        # keep only the recurring title before the em dash.
        title = name.split("—", 1)[0].strip() or name

        return DenverComedyLoungeShow(
            title=title,
            datetime_str=datetime_str,
            show_page_url=url,
        )

    @staticmethod
    def _to_24h(hour_12: int, meridiem: str) -> int:
        """Convert a 12-hour clock hour + am/pm into a 24-hour hour."""
        hour = hour_12 % 12
        if meridiem == "pm":
            hour += 12
        return hour

    @staticmethod
    def extract_offer_price(html_content: str, show: Optional[DenverComedyLoungeShow] = None,
                            *, now: Optional[datetime] = None) -> Optional[float]:
        """Read matched, currently available USD General Admission; never VIP packages.

        Streamed text chunks can split objects, so decode and concatenate the flight
        before balanced extraction. Only top-level Event objects are candidates.
        """
        if not html_content or show is None:
            return None
        now = now or datetime.now(timezone.utc)
        try:
            expected = datetime.strptime(show.datetime_str, "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=ZoneInfo("America/Denver"))
        except ValueError:
            return None
        if expected <= now:
            return None

        def identity(url):
            if not isinstance(url, str):
                return None
            parsed = urlparse(url)
            if parsed.scheme != "https" or parsed.netloc not in (
                    "denvercomedylounge.com", "www.denvercomedylounge.com"):
                return None
            path = parsed.path.rstrip("/")
            return path if path.startswith("/shows/") else None

        target = identity(show.show_page_url)
        if not target:
            return None
        objects = JSONUtils.parse_json_ld_contents(
            HtmlScraper.get_json_ld_script_contents(html_content))
        flight = "".join(extract_push_payloads(html_content))
        # Walk complete outer objects, avoiding nested related-show props.
        cursor = 0
        while (start := flight.find("{", cursor)) >= 0:
            block = extract_balanced(flight, start, "{", "}")
            if not block:
                break
            cursor = start + len(block)
            try:
                objects.append(json.loads(block))
            except ValueError:
                continue
        matched = []
        for obj in objects:
            if not isinstance(obj, dict) or obj.get("@type") != "Event":
                continue
            if identity(obj.get("url")) != target:
                continue
            try:
                start = datetime.fromisoformat(obj.get("startDate", "").replace("Z", "+00:00"))
            except (ValueError, TypeError, AttributeError):
                continue
            if start.tzinfo is None or start != expected:
                continue
            matched.append(obj)
        prices = set()
        for event in matched:
            if event.get("eventStatus") != "https://schema.org/EventScheduled":
                return None
            offers = event.get("offers")
            if not isinstance(offers, list):
                offers = [offers]
            admission = []
            for offer in offers:
                if not isinstance(offer, dict) or offer.get("name") != "General Admission":
                    continue
                if (offer.get("@type") != "Offer" or offer.get("priceCurrency") != "USD"
                        or offer.get("availability") != "https://schema.org/InStock"
                        or identity(offer.get("url")) != target
                        or offer.get("eligibleQuantity") or offer.get("description")):
                    return None
                for key, lower in (("validFrom", True), ("validThrough", False),
                                   ("availabilityStarts", True), ("availabilityEnds", False)):
                    if key not in offer:
                        continue
                    try:
                        boundary = datetime.fromisoformat(offer[key].replace("Z", "+00:00"))
                        if boundary.tzinfo is None or (now < boundary if lower else now >= boundary):
                            return None
                    except (ValueError, TypeError, AttributeError):
                        return None
                try:
                    price = Decimal(str(offer.get("price")))
                except InvalidOperation:
                    return None
                if not price.is_finite() or not 0 < price < 1000000:
                    return None
                admission.append(float(price))
            if len(admission) != 1:
                return None
            prices.add(admission[0])
        return prices.pop() if len(prices) == 1 else None


__all__ = ["DenverComedyLoungeExtractor"]
