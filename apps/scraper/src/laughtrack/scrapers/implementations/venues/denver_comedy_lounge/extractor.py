"""Extractor for Denver Comedy Lounge's /shows ItemList page."""

import re
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo
from laughtrack.core.clients.rsc.extractor import extract_push_payloads, extract_balanced
from typing import Any, List, Optional
from urllib.parse import urlparse

from laughtrack.foundation.utilities.json.utils import JSONUtils
from laughtrack.utilities.infrastructure.html.scraper import HtmlScraper

from .data import DenverComedyLoungeShow

# Recurring show slugs encode weekday, start time, and date, e.g.
# ``friday-7pm-2026-06-26`` or ``saturday-10pm-2026-09-19``.
_SLUG_RE = re.compile(r"^[a-z]+-(\d{1,2})(am|pm)-(\d{4})-(\d{2})-(\d{2})$")


class DenverComedyLoungeExtractor:
    """Parse the venue's /shows page into DenverComedyLoungeShow objects.

    The page server-renders a schema.org ``ItemList`` whose ``itemListElement``
    entries each carry a ``name`` (the show title, with a human date suffix) and
    a detail ``url``. The per-show date/time is not in the JSON-LD body — it is
    encoded in recurring detail URL slugs. Named events instead require a matched
    detail Event with an explicit, timezone-aware startDate.
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
    def _show_identity(url: Any) -> Optional[str]:
        if not isinstance(url, str):
            return None
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.netloc not in (
                "denvercomedylounge.com", "www.denvercomedylounge.com"):
            return None
        path = parsed.path.rstrip("/")
        return path if path.startswith("/shows/") else None

    @staticmethod
    def _event_objects(html_content: str) -> List[dict]:
        """Read literal and streamed top-level Events without traversing related props."""
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
        return [obj for obj in objects if isinstance(obj, dict) and obj.get("@type") == "Event"]

    @staticmethod
    def extract_named_event_urls(html_content: str) -> List[str]:
        """Collect venue-owned listing URLs whose slugs do not provide a showtime."""
        urls = {}
        for obj in JSONUtils.parse_json_ld_contents(
                HtmlScraper.get_json_ld_script_contents(html_content)):
            for element in DenverComedyLoungeExtractor._item_list_elements(obj):
                item = element.get("item")
                if not isinstance(item, dict):
                    continue
                url = item.get("url")
                identity = DenverComedyLoungeExtractor._show_identity(url)
                if identity and not _SLUG_RE.fullmatch(identity.rsplit("/", 1)[-1]):
                    urls.setdefault(identity, url)
        return list(urls.values())

    @staticmethod
    def extract_named_show(html_content: str, url: str) -> Optional[DenverComedyLoungeShow]:
        """Resolve one unambiguous performance; a date-only slug is never evidence."""
        target = DenverComedyLoungeExtractor._show_identity(url)
        if not html_content or not target:
            return None
        performances = {}
        for event in DenverComedyLoungeExtractor._event_objects(html_content):
            if DenverComedyLoungeExtractor._show_identity(event.get("url")) != target:
                continue
            name = event.get("name")
            if (not isinstance(name, str) or not name.strip()
                    or event.get("eventStatus") != "https://schema.org/EventScheduled"):
                return None
            try:
                start = datetime.fromisoformat(event.get("startDate", "").replace("Z", "+00:00"))
            except (ValueError, TypeError, AttributeError):
                return None
            if start.tzinfo is None:
                return None
            performances[start.astimezone(timezone.utc)] = (name.strip(), start)
        if len(performances) != 1:
            return None
        name, start = next(iter(performances.values()))
        local = start.astimezone(ZoneInfo("America/Denver"))
        return DenverComedyLoungeShow(
            title=name, datetime_str=local.strftime("%Y-%m-%d %H:%M:%S"),
            show_page_url=url, start_datetime=local,
        )

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
            expected = show.start_datetime or datetime.strptime(show.datetime_str, "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=ZoneInfo("America/Denver"))
        except ValueError:
            return None
        if expected <= now:
            return None

        identity = DenverComedyLoungeExtractor._show_identity
        target = identity(show.show_page_url)
        if not target:
            return None
        objects = DenverComedyLoungeExtractor._event_objects(html_content)
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
            if start.tzinfo is None or start.astimezone(timezone.utc) != expected.astimezone(timezone.utc):
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
