"""Extractor for the Grisly Pear calendar listing."""

from __future__ import annotations

import re
import math
from datetime import date, datetime
from urllib.parse import urljoin, urlsplit
from zoneinfo import ZoneInfo
from dataclasses import replace

from bs4 import BeautifulSoup

from laughtrack.scrapers.implementations.json_ld.extractor import EventExtractor
from laughtrack.core.entities.club.model import Club

from .data import GrislyPearEvent

_CURRENT_EVENT_RE = re.compile(r"(?P<stamp>\d{2}-\d{2}-\d{2}-\d{2}-\d{2}-[ap]m)$", re.I)
_DATED_EVENT_RE = re.compile(r"(?P<date>\d{4}-\d{2}-\d{2})(?P<time>\d{6})$")


class GrislyPearExtractor:
    """Extract future event anchors from the Grisly Pear calendar."""

    @staticmethod
    def extract_events(
        html: str,
        *,
        base_url: str,
        club_name: str,
        today: date | None = None,
    ) -> list[GrislyPearEvent]:
        if today is None:
            today = date.today()

        soup = BeautifulSoup(html or "", "html.parser")
        events: list[GrislyPearEvent] = []
        seen_urls: set[str] = set()

        for anchor in soup.find_all("a", href=True):
            href = str(anchor["href"])
            if "/events/" not in href:
                continue

            url = urljoin(base_url, href)
            if urlsplit(url).hostname != urlsplit(base_url).hostname:
                continue
            if url in seen_urls:
                continue

            parsed = GrislyPearExtractor._parse_dated_event_url(url)
            if parsed is None:
                continue
            event_date, event_time = parsed
            if event_date < today:
                continue

            name = GrislyPearExtractor._extract_title(anchor)
            if not name or not GrislyPearExtractor._belongs_to_club(name, club_name):
                continue

            seen_urls.add(url)
            events.append(
                GrislyPearEvent(
                    name=name,
                    url=url,
                    date=event_date.isoformat(),
                    time=event_time,
                )
            )

        return events

    @staticmethod
    def _parse_dated_event_url(url: str) -> tuple[date, str] | None:
        slug = urlsplit(url).path.rstrip("/").rsplit("/", 1)[-1]
        current = _CURRENT_EVENT_RE.search(slug)
        if current:
            try:
                stamp = datetime.strptime(current.group("stamp"), "%m-%d-%y-%I-%M-%p")
                return stamp.date(), stamp.strftime("%H%M%S")
            except ValueError:
                return None
        match = _DATED_EVENT_RE.search(slug)
        if not match:
            return None
        try:
            stamp = datetime.strptime(match.group("date") + match.group("time"), "%Y-%m-%d%H%M%S")
            return stamp.date(), stamp.strftime("%H%M%S")
        except ValueError:
            return None

    @staticmethod
    def _extract_title(anchor) -> str:
        for value in (
            anchor.get("aria-label"),
            anchor.get("title"),
            anchor.get_text(" ", strip=True),
        ):
            title = GrislyPearExtractor._clean_title(value)
            if title:
                return title

        image = anchor.find("img")
        return GrislyPearExtractor._clean_title(image.get("alt") if image else None)

    @staticmethod
    def _clean_title(value: object) -> str:
        if not isinstance(value, str):
            return ""
        title = " ".join(value.split())
        if title.lower().startswith("view "):
            title = title[5:].strip()
        return title

    @staticmethod
    def _belongs_to_club(title: str, club_name: str) -> bool:
        title_lower = title.lower()
        club_lower = club_name.lower()
        if "midtown" in club_lower:
            return "midtown" in title_lower
        if "greenwich" in club_lower:
            return "greenwich village" in title_lower or "grisly pear classic" in title_lower
        return True



    @staticmethod
    def enrich_detail(candidate: GrislyPearEvent, html: str, club: Club) -> GrislyPearEvent:
        """Accept metadata only from the requested performance at this physical venue."""
        expected = datetime.strptime(candidate.date + candidate.time, "%Y-%m-%d%H%M%S").replace(
            tzinfo=ZoneInfo(club.timezone or "America/New_York")
        )
        events = EventExtractor.extract_events(html, base_url=candidate.url)
        # A page describing another event must not donate its Featuring section
        # or purchase controls to the requested event, even if it recommends it.
        if len(events) != 1:
            raise ValueError("detail must identify exactly one performance")
        detail = events[0]
        if detail.start_date.tzinfo is None or detail.start_date != expected:
            raise ValueError("detail start date does not match requested performance")
        address = detail.location.address
        if not GrislyPearExtractor._same_street(address.street_address, club.address):
            raise ValueError("detail physical venue does not match configured club")
        expected_zip = (club.zip_code or "").strip()[:5]
        if expected_zip and address.postal_code and address.postal_code[:5] != expected_zip:
            raise ValueError("detail venue postal code does not match configured club")
        canonical = urljoin(candidate.url, detail.url)
        if urlsplit(canonical).hostname != urlsplit(candidate.url).hostname:
            raise ValueError("detail URL changed venue host")
        canonical_time = GrislyPearExtractor._parse_dated_event_url(canonical)
        if canonical_time != (expected.date(), expected.strftime("%H%M%S")):
            raise ValueError("detail URL does not identify requested performance")

        soup = BeautifulSoup(html, "html.parser")
        names = [person.name for person in detail.performers or []]
        names.extend(node.get_text(" ", strip=True) for node in soup.select(
            ".event-comedians-container .comedian-name a[href*='/comedians/']"
        ))
        performers = []
        seen = set()
        for name in names:
            name = " ".join(name.split())
            key = name.casefold()
            if key and key not in seen and key not in {"special guest", "special guests"}:
                seen.add(key)
                performers.append(name)
        return replace(candidate, url=canonical, performers=performers,
                       price=GrislyPearExtractor._purchase_price(soup, detail))

    @staticmethod
    def _same_street(left: str, right: str) -> bool:
        def normalize(value: str) -> str:
            value = value.split(",", 1)[0].casefold()
            value = re.sub(r"[.]", "", value)
            value = re.sub(r"\bwest\b", "w", value)
            value = re.sub(r"\beast\b", "e", value)
            value = re.sub(r"\bstreet\b", "st", value)
            return " ".join(value.split())
        return bool(left and right) and normalize(left) == normalize(right)

    @staticmethod
    def _purchase_price(soup: BeautifulSoup, detail) -> float | None:
        """Return the GA base price only when current purchase inventory exists.

        JSON-LD can retain InStock/prices after sales end. The displayed total
        includes mandatory fees and must never substitute for the base price.
        """
        if "ticket sales have ended" in soup.get_text(" ", strip=True).casefold():
            return None
        def positive(value):
            try:
                number = float(str(value).strip().lstrip("$").replace(",", ""))
                return number if math.isfinite(number) and number > 0 else None
            except (ValueError, TypeError):
                return None

        offers = [offer for offer in detail.offers if offer.price_currency == "USD"
                  and offer.availability.rsplit("/", 1)[-1].casefold() == "instock"]
        offer_prices = {price for offer in offers if (price := positive(offer.price)) is not None}
        prices = []
        for container in soup.select(".ticket-type-container"):
            if "general admission" not in container.get_text(" ", strip=True).casefold():
                continue
            quantity = container.select_one("select.ticket-quantity:not([disabled])")
            if quantity is None or not any(positive(option.get("value")) for option in quantity.select("option:not([disabled])")):
                continue
            base = container.select_one(".breakdown-base-original")
            price = positive(base.get_text()) if base else (next(iter(offer_prices)) if len(offer_prices) == 1 else None)
            if price is not None:
                prices.append(price)
        return min(prices) if prices else None
