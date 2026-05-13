"""
Platform-specific event extractors for comedian websites.

Detects the hosting platform from the comedian's website URL and extracts
events using platform-specific APIs when available (Squarespace, Wix, komi.io).

Falls back to None (caller should try JSON-LD) when the platform is not
recognized or the platform API yields no events.
"""

import json
import re
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from urllib.parse import quote, urlencode, urljoin, urlparse

from bs4 import BeautifulSoup

from laughtrack.core.entities.club.handler import ClubHandler
from laughtrack.core.entities.comedian.model import Comedian
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.utilities.domain.club.timezone_lookup import timezone_from_address


# US state abbreviations used to filter events to US only
_US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC",
}


def detect_website_platform(url: str) -> Optional[str]:
    """Detect hosting platform from a comedian website URL.

    Returns "squarespace", "wix", "komi", or None if unrecognized.
    Only matches subdomain-based URLs (e.g. *.squarespace.com).
    Custom-domain sites that happen to run on these platforms are not detected.
    """
    if not url:
        return None
    try:
        hostname = urlparse(url).hostname or ""
    except Exception:
        return None

    hostname = hostname.lower()

    if hostname.endswith(".squarespace.com"):
        return "squarespace"
    if hostname.endswith(".wixsite.com"):
        return "wix"
    if hostname.endswith(".komi.io"):
        return "komi"
    if hostname.endswith("vividseats.com"):
        return "vividseats"
    if hostname.endswith("shubert.com"):
        return "shubert"
    return None


def detect_website_platform_from_html(html: str) -> Optional[str]:
    """Detect hosting platform by inspecting fetched HTML content.

    Fallback for custom-domain sites where URL-based detection returns None.
    Checks for platform-specific markers embedded in the page source:
    - Squarespace: Static.SQUARESPACE_CONTEXT JavaScript object
    - Wix: wix-one-events widget reference

    Returns "squarespace", "wix", or None if unrecognized.
    """
    if not html:
        return None

    if "Static.SQUARESPACE_CONTEXT" in html:
        return "squarespace"
    if WixExtractorForComedian._EVENTS_MARKER in html:
        return "wix"
    if 'class="date"' in html and 'data-date=' in html and "venue-name" in html:
        return "tour_listing"
    if "cdn/shopifycloud" in html and (
        "tour-date-article-container" in html or "fa_date_item" in html
    ):
        return "shopify_tour"
    return None


def _upsert_tour_date_venue(
    *,
    club_handler: ClubHandler,
    log_prefix: str,
    venue_name: str,
    location: str,
    event_dt: datetime,
    event_url: Optional[str],
    comedian: Optional[Comedian],
    sample_url: Optional[str],
    platform_hints: list[str],
) -> bool:
    """Upsert a venue found on a comedian tour-date page."""
    try:
        venue_name = venue_name.strip()
        location = re.sub(r"\s+", " ", location or "").strip()
        if not venue_name or not location:
            return False

        if event_dt.tzinfo is None:
            event_dt = event_dt.replace(tzinfo=timezone.utc)
        if event_dt < datetime.now(tz=timezone.utc):
            return False

        match = re.search(r"(.+?),\s*([A-Z]{2})\b", location)
        if not match:
            return False
        city = match.group(1).strip()
        region = match.group(2).strip().upper()
        if region not in _US_STATES:
            return False

        address = f"{city}, {region}"
        venue_dict = {
            "name": venue_name,
            "address": address,
            "zip_code": "",
            "timezone": timezone_from_address(address),
            "discovery_metadata": {
                "source": "comedian_websites",
                "sample_urls": [sample_url] if sample_url else [],
                "event_urls": [event_url] if event_url else [],
                "platform_hints": platform_hints,
            },
        }
        if comedian is not None:
            venue_dict["discovery_metadata"]["comedian_refs"] = [
                {"uuid": comedian.uuid, "name": comedian.name}
            ]

        club = club_handler.upsert_for_tour_date_venue(venue_dict)
        return club is not None
    except Exception as e:
        Logger.warn(f"{log_prefix}: tour-date venue extraction error: {e}")
        return False


def _parse_iso_datetime(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _infer_future_date(month_text: str, day_text: str) -> Optional[datetime]:
    month_text = (month_text or "").strip()[:3].title()
    try:
        month = datetime.strptime(month_text, "%b").month
        day = int(re.sub(r"\D", "", day_text or ""))
    except (ValueError, TypeError):
        return None

    now = datetime.now(tz=timezone.utc)
    candidate = datetime(now.year, month, day, tzinfo=timezone.utc)
    if candidate.date() < now.date():
        candidate = candidate.replace(year=now.year + 1)
    return candidate


def _first_href(element) -> Optional[str]:
    link = element.find("a", href=True)
    if not link:
        return None
    href = (link.get("href") or "").strip()
    return href or None


class StructuredTourListExtractorForComedian:
    """Extract venues from generated tour-date pages with ``div.date`` rows."""

    @staticmethod
    def has_rows(html: str) -> bool:
        return bool(html) and 'class="date"' in html and "venue-name" in html

    @staticmethod
    async def extract_venues(
        scraping_url: str,
        html: str,
        comedian: Comedian,
        club_handler: ClubHandler,
        log_prefix: str,
    ) -> Optional[int]:
        if not StructuredTourListExtractorForComedian.has_rows(html):
            return None

        soup = BeautifulSoup(html, "html.parser")
        count = 0
        for row in soup.select("div.date"):
            if (row.get("data-country") or "").strip().upper() not in {"USA", "US", "UNITED STATES"}:
                continue
            event_dt = _parse_iso_datetime(row.get("data-date") or "")
            if event_dt is None:
                continue
            venue_node = row.select_one(".venue-name")
            location_node = row.select_one(".venue-location")
            if not venue_node or not location_node:
                continue
            if _upsert_tour_date_venue(
                club_handler=club_handler,
                log_prefix=log_prefix,
                venue_name=venue_node.get_text(" ", strip=True),
                location=location_node.get_text(" ", strip=True),
                event_dt=event_dt,
                event_url=_first_href(row),
                comedian=comedian,
                sample_url=scraping_url,
                platform_hints=["tour_listing"],
            ):
                count += 1

        return count


class ShopifyTourListExtractorForComedian:
    """Extract venues from custom Shopify tour-list sections."""

    @staticmethod
    def has_rows(html: str) -> bool:
        return bool(html) and (
            "tour-date-article-container" in html or "fa_date_item" in html
        )

    @staticmethod
    async def extract_venues(
        scraping_url: str,
        html: str,
        comedian: Comedian,
        club_handler: ClubHandler,
        log_prefix: str,
    ) -> Optional[int]:
        if not ShopifyTourListExtractorForComedian.has_rows(html):
            return None

        soup = BeautifulSoup(html, "html.parser")
        count = 0
        for row in soup.select(".tour-date-article-container"):
            if ShopifyTourListExtractorForComedian._upsert_steveo_row(
                row, scraping_url, comedian, club_handler, log_prefix
            ):
                count += 1
        for row in soup.select(".fa_date_item"):
            if ShopifyTourListExtractorForComedian._upsert_schulz_row(
                row, scraping_url, comedian, club_handler, log_prefix
            ):
                count += 1

        return count

    @staticmethod
    def _upsert_steveo_row(row, scraping_url: str, comedian: Comedian, club_handler: ClubHandler, log_prefix: str) -> bool:
        date_node = row.select_one(".td-but1")
        location_node = row.select_one(".td-but2 h3")
        venue_node = row.select_one(".td-but2 h4")
        if not date_node or not location_node or not venue_node:
            return False
        parts = [p for p in date_node.get_text(" ", strip=True).split() if p]
        if len(parts) < 2:
            return False
        event_dt = _infer_future_date(parts[0], parts[1])
        if event_dt is None:
            return False
        location = re.sub(r"\s*\([^)]*\)", "", location_node.get_text(" ", strip=True)).strip()
        return _upsert_tour_date_venue(
            club_handler=club_handler,
            log_prefix=log_prefix,
            venue_name=venue_node.get_text(" ", strip=True),
            location=location,
            event_dt=event_dt,
            event_url=_first_href(row),
            comedian=comedian,
            sample_url=scraping_url,
            platform_hints=["shopify_tour"],
        )

    @staticmethod
    def _upsert_schulz_row(row, scraping_url: str, comedian: Comedian, club_handler: ClubHandler, log_prefix: str) -> bool:
        date_node = row.find("h3")
        location_node = row.select_one(".location__container")
        venue_node = row.select_one(".venue__container")
        if not date_node or not location_node or not venue_node:
            return False
        match = re.search(r"([A-Za-z]+)\s+(\d{1,2})", date_node.get_text(" ", strip=True))
        if not match:
            return False
        event_dt = _infer_future_date(match.group(1), match.group(2))
        if event_dt is None:
            return False
        return _upsert_tour_date_venue(
            club_handler=club_handler,
            log_prefix=log_prefix,
            venue_name=venue_node.get_text(" ", strip=True),
            location=location_node.get_text(" ", strip=True),
            event_dt=event_dt,
            event_url=_first_href(row),
            comedian=comedian,
            sample_url=scraping_url,
            platform_hints=["shopify_tour"],
        )


class ShubertSingleEventExtractorForComedian:
    """Extract a single venue from Shubert event detail pages."""

    @staticmethod
    async def extract_venues(
        scraping_url: str,
        html: str,
        comedian: Comedian,
        club_handler: ClubHandler,
        log_prefix: str,
    ) -> Optional[int]:
        hostname = (urlparse(scraping_url).hostname or "").lower()
        if not hostname.endswith("shubert.com"):
            return None

        soup = BeautifulSoup(html or "", "html.parser")
        date_node = soup.select_one(".m-date__singleDate")
        if not date_node:
            return 0
        try:
            event_dt = datetime.strptime(
                re.sub(r"\s+", " ", date_node.get_text(" ", strip=True)).replace(" ,", ","),
                "%A, %B %d, %Y",
            ).replace(tzinfo=timezone.utc)
        except ValueError:
            return 0

        venue_name = "Shubert Theatre New Haven"
        location = "New Haven, CT"
        return 1 if _upsert_tour_date_venue(
            club_handler=club_handler,
            log_prefix=log_prefix,
            venue_name=venue_name,
            location=location,
            event_dt=event_dt,
            event_url=scraping_url,
            comedian=comedian,
            sample_url=scraping_url,
            platform_hints=["shubert"],
        ) else 0


class VividSeatsExtractorForComedian:
    """Extract venue rows from Vivid Seats performer pages when rendered HTML contains listings."""

    @staticmethod
    async def extract_venues(
        scraping_url: str,
        html: str,
        comedian: Comedian,
        club_handler: ClubHandler,
        log_prefix: str,
    ) -> Optional[int]:
        hostname = (urlparse(scraping_url).hostname or "").lower()
        if not hostname.endswith("vividseats.com"):
            return None

        soup = BeautifulSoup(html or "", "html.parser")
        count = 0
        for row in soup.find_all("a", href=True):
            text = row.get_text(" ", strip=True)
            if comedian.name.lower() not in text.lower() or "•" not in text:
                continue
            match = re.match(r"^[A-Za-z]{3}\s+([A-Za-z]{3})\s+(\d{1,2})\s+", text)
            if not match:
                continue
            event_dt = _infer_future_date(match.group(1), match.group(2))
            venue_match = re.search(
                rf"{re.escape(comedian.name)}(?:\s*\([^)]*\))*\s+(.+?)\s+•\s+([^•]+?,\s*[A-Z]{{2}})\b",
                text,
                flags=re.IGNORECASE,
            )
            if not venue_match or event_dt is None:
                continue
            if _upsert_tour_date_venue(
                club_handler=club_handler,
                log_prefix=log_prefix,
                venue_name=venue_match.group(1).strip(),
                location=venue_match.group(2).strip(),
                event_dt=event_dt,
                event_url=urljoin(scraping_url, row.get("href") or ""),
                comedian=comedian,
                sample_url=scraping_url,
                platform_hints=["vividseats"],
            ):
                count += 1

        return count


class SeatedTourListExtractorForComedian:
    """Extract venues from Seated event widgets embedded on artist sites."""

    @staticmethod
    def has_rows(html: str) -> bool:
        return bool(html) and "seated-event-row" in html

    @staticmethod
    def has_widget(html: str) -> bool:
        return bool(html) and "widget.seated.com" in html and "data-artist-id=" in html

    @staticmethod
    def _artist_id(html: str) -> Optional[str]:
        match = re.search(r'data-artist-id=["\']([^"\']+)["\']', html or "")
        return match.group(1).strip() if match else None

    @staticmethod
    async def extract_venues(
        scraping_url: str,
        html: str,
        comedian: Comedian,
        club_handler: ClubHandler,
        log_prefix: str,
        fetch_json_fn=None,
    ) -> Optional[int]:
        if fetch_json_fn and SeatedTourListExtractorForComedian.has_widget(html):
            return await SeatedTourListExtractorForComedian._extract_from_api(
                scraping_url=scraping_url,
                html=html,
                comedian=comedian,
                club_handler=club_handler,
                fetch_json_fn=fetch_json_fn,
                log_prefix=log_prefix,
            )

        if not SeatedTourListExtractorForComedian.has_rows(html):
            return None

        soup = BeautifulSoup(html or "", "html.parser")
        count = 0
        for row in soup.select(".seated-event-row"):
            text = row.get_text(" ", strip=True)
            date_match = re.search(
                r"\b([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})\b",
                text,
            )
            venue_node = row.select_one(".seated-event-venue-name")
            location_node = row.select_one(".seated-event-venue-location")
            if not date_match or not venue_node or not location_node:
                continue
            try:
                event_dt = datetime.strptime(
                    " ".join(date_match.groups()),
                    "%B %d %Y",
                ).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
            if _upsert_tour_date_venue(
                club_handler=club_handler,
                log_prefix=log_prefix,
                venue_name=venue_node.get_text(" ", strip=True),
                location=location_node.get_text(" ", strip=True),
                event_dt=event_dt,
                event_url=_first_href(row),
                comedian=comedian,
                sample_url=scraping_url,
                platform_hints=["seated"],
            ):
                count += 1

        return count

    @staticmethod
    async def _extract_from_api(
        *,
        scraping_url: str,
        html: str,
        comedian: Comedian,
        club_handler: ClubHandler,
        fetch_json_fn,
        log_prefix: str,
    ) -> Optional[int]:
        artist_id = SeatedTourListExtractorForComedian._artist_id(html)
        if not artist_id:
            return None

        api_url = f"https://cdn.seated.com/api/tour/{quote(artist_id)}?include=tour-events"
        try:
            data = await fetch_json_fn(api_url, headers={"X-Client-Version": "HEAD"}, timeout=20)
        except Exception as e:
            Logger.warn(f"{log_prefix}: Seated API error for {comedian.name}: {e}")
            return 0

        included = data.get("included") if isinstance(data, dict) else None
        if not isinstance(included, list):
            return 0

        count = 0
        for event in included:
            if not isinstance(event, dict) or event.get("type") != "tour-events":
                continue
            attrs = event.get("attributes") or {}
            event_dt = _parse_iso_datetime(attrs.get("starts-at") or attrs.get("starts-at-date-local") or "")
            venue_name = (attrs.get("venue-name") or "").strip()
            location = (attrs.get("formatted-address") or "").strip()
            if event_dt is None or not venue_name or not location:
                continue
            if _upsert_tour_date_venue(
                club_handler=club_handler,
                log_prefix=log_prefix,
                venue_name=venue_name,
                location=location,
                event_dt=event_dt,
                event_url=f"https://link.seated.com/{event.get('id')}" if event.get("id") else None,
                comedian=comedian,
                sample_url=scraping_url,
                platform_hints=["seated"],
            ):
                count += 1

        return count


class TicketNetworkTourListExtractorForComedian:
    """Extract venues from TicketNetwork catalog widgets embedded on tour pages."""

    _CONSUMER_KEY = "fuTwxN_M6RKMaobcsfJ5qSvcVAUa"
    _WEBSITE_CONFIG_ID = "12498"

    @staticmethod
    def has_widget(html: str) -> bool:
        return bool(html) and "csctnCall(params)" in html and "tn-apis.com/catalog" not in html

    @staticmethod
    def _performer_name(html: str, comedian: Comedian) -> str:
        match = re.search(r"performerFilter=text/name eq '([^']+)'", html or "")
        return (match.group(1).strip() if match else comedian.name)

    @staticmethod
    async def extract_venues(
        scraping_url: str,
        html: str,
        comedian: Comedian,
        club_handler: ClubHandler,
        fetch_json_fn,
        log_prefix: str,
    ) -> Optional[int]:
        if not TicketNetworkTourListExtractorForComedian.has_widget(html):
            return None

        now = datetime.now(tz=timezone.utc)
        performer_name = TicketNetworkTourListExtractorForComedian._performer_name(html, comedian)
        query = urlencode(
            {
                "q": "*",
                "filter": (
                    "_metadata/hasTickets eq true and "
                    f"date/date le {now.replace(year=now.year + 1).date().isoformat()}"
                ),
                "performerFilter": f"text/name eq '{performer_name}'",
                "includeFacets": "true",
                "consumerKey": TicketNetworkTourListExtractorForComedian._CONSUMER_KEY,
                "websiteConfigId": TicketNetworkTourListExtractorForComedian._WEBSITE_CONFIG_ID,
                "perPage": "100",
                "page": "1",
            }
        )
        api_url = f"https://www.tn-apis.com/catalog/v2/events/search?{query}"
        try:
            data = await fetch_json_fn(api_url, timeout=20)
        except Exception as e:
            Logger.warn(f"{log_prefix}: TicketNetwork API error for {performer_name}: {e}")
            return 0

        results = data.get("results") if isinstance(data, dict) else None
        if not isinstance(results, list):
            return 0

        count = 0
        for event in results:
            if not isinstance(event, dict):
                continue
            if ((event.get("country") or {}).get("alphaCode") or "").upper() != "US":
                continue
            event_dt = _parse_iso_datetime(((event.get("date") or {}).get("datetimeOffset") or ""))
            venue_name = (((event.get("venue") or {}).get("text") or {}).get("name") or "").strip()
            city = (((event.get("city") or {}).get("text") or {}).get("name") or "").strip()
            state = ((((event.get("stateProvince") or {}).get("text") or {}).get("abbr") or "").strip())
            if event_dt is None or not venue_name or not city or not state:
                continue
            event_url = None
            for link in event.get("_links") or []:
                if isinstance(link, dict) and link.get("rel") == "self":
                    event_url = link.get("href")
                    break
            if _upsert_tour_date_venue(
                club_handler=club_handler,
                log_prefix=log_prefix,
                venue_name=venue_name,
                location=f"{city}, {state}",
                event_dt=event_dt,
                event_url=event_url,
                comedian=comedian,
                sample_url=scraping_url,
                platform_hints=["ticketnetwork"],
            ):
                count += 1

        return count


class TextTourListExtractorForComedian:
    """Extract venues from plain text tour rows with date, venue, and city/state."""

    _MONTHS = (
        "jan", "feb", "mar", "apr", "may", "jun",
        "jul", "aug", "sep", "oct", "nov", "dec",
        "january", "february", "march", "april", "june", "july",
        "august", "september", "october", "november", "december",
    )
    _MONTH_RE = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    _STATE_RE = re.compile(r",\s*([A-Z]{2})(?:\s+\d{5})?\b")

    @staticmethod
    def has_rows(html: str) -> bool:
        if not html:
            return False
        lowered = html.lower()
        return any(month in lowered for month in TextTourListExtractorForComedian._MONTHS) and bool(
            re.search(r",\s*[A-Z]{2}\b", html)
        )

    @staticmethod
    async def extract_venues(
        scraping_url: str,
        html: str,
        comedian: Comedian,
        club_handler: ClubHandler,
        log_prefix: str,
    ) -> Optional[int]:
        if not TextTourListExtractorForComedian.has_rows(html):
            return None

        soup = BeautifulSoup(html or "", "html.parser")
        seen: set[tuple[str, str, str]] = set()
        count = 0
        for row in soup.find_all(["div", "section", "article", "li", "a", "p"]):
            parsed = TextTourListExtractorForComedian._parse_row(row.get_text(" ", strip=True), comedian.name)
            if not parsed:
                continue
            event_dt, venue_name, location = parsed
            key = (event_dt.date().isoformat(), venue_name.lower(), location.lower())
            if key in seen:
                continue
            seen.add(key)
            if _upsert_tour_date_venue(
                club_handler=club_handler,
                log_prefix=log_prefix,
                venue_name=venue_name,
                location=location,
                event_dt=event_dt,
                event_url=_first_href(row),
                comedian=comedian,
                sample_url=scraping_url,
                platform_hints=["text_tour_list"],
            ):
                count += 1

        return count

    @staticmethod
    def _parse_row(text: str, comedian_name: str) -> Optional[tuple[datetime, str, str]]:
        text = re.sub(r"\s+", " ", text or "").strip()
        if len(text) < 15 or len(text) > 350:
            return None

        date_match = TextTourListExtractorForComedian._find_date(text)
        if not date_match:
            return None
        event_dt, remainder = date_match
        remainder = TextTourListExtractorForComedian._clean_remainder(remainder, comedian_name)
        parsed_location = TextTourListExtractorForComedian._split_location_and_venue(remainder)
        if not parsed_location:
            return None

        venue_name, location = parsed_location
        if not venue_name or len(venue_name.split()) > 10:
            return None
        return event_dt, venue_name, location

    @staticmethod
    def _split_location_and_venue(text: str) -> Optional[tuple[str, str]]:
        state_match = TextTourListExtractorForComedian._STATE_RE.search(text)
        if not state_match:
            return None

        prefix = TextTourListExtractorForComedian._clean_venue_text(text[:state_match.start()])
        state = state_match.group(1)
        suffix = TextTourListExtractorForComedian._clean_venue_text(text[state_match.end():])
        if suffix:
            return suffix, f"{prefix}, {state}"

        words = prefix.split()
        if len(words) < 2:
            return None
        city_word_count = 1
        multi_city_leaders = {
            "Atlantic", "Baton", "Boca", "Fort", "Kansas", "Las", "Long",
            "Los", "New", "Oklahoma", "Palm", "Saint", "Salt", "San",
            "Santa", "St.", "Virginia", "West",
        }
        if len(words) >= 2 and words[-2] in multi_city_leaders:
            city_word_count = 2
        if len(words) >= 3 and " ".join(words[-3:]).lower() in {"king of prussia"}:
            city_word_count = 3

        city = " ".join(words[-city_word_count:])
        venue = " ".join(words[:-city_word_count])
        return (venue, f"{city}, {state}") if venue and city else None

    @staticmethod
    def _find_date(text: str) -> Optional[tuple[datetime, str]]:
        prefix_month = re.search(
            rf"\b(?P<month>{TextTourListExtractorForComedian._MONTH_RE})\s+"
            r"(?P<day>\d{1,2})(?:\s*[-–]\s*\d{1,2})?(?:,\s*)?\s*"
            r"(?P<year>\d{4}|['’]\d{2})?",
            text,
            flags=re.IGNORECASE,
        )
        if prefix_month:
            event_dt = TextTourListExtractorForComedian._date_from_parts(
                prefix_month.group("month"), prefix_month.group("day"), prefix_month.group("year")
            )
            if event_dt:
                return event_dt, text[prefix_month.end():]

        day_month = re.search(
            rf"\b(?P<day>\d{{1,2}})\s+(?:[A-Z]{{3}}\s+)?(?P<month>{TextTourListExtractorForComedian._MONTH_RE})\b",
            text,
            flags=re.IGNORECASE,
        )
        if day_month:
            event_dt = TextTourListExtractorForComedian._date_from_parts(
                day_month.group("month"), day_month.group("day"), None
            )
            if event_dt:
                return event_dt, text[day_month.end():]

        return None

    @staticmethod
    def _date_from_parts(month_text: str, day_text: str, year_text: Optional[str]) -> Optional[datetime]:
        if year_text:
            year_text = year_text.replace("’", "'")
            year = 2000 + int(year_text[1:]) if year_text.startswith("'") else int(year_text)
            try:
                month = datetime.strptime(month_text.strip()[:3].title(), "%b").month
                return datetime(year, month, int(day_text), tzinfo=timezone.utc)
            except ValueError:
                return None
        return _infer_future_date(month_text, day_text)

    @staticmethod
    def _clean_remainder(text: str, comedian_name: str) -> str:
        text = re.sub(r"\b(?:Buy\s+Tickets|Tickets|TICKETS|TOKENS|TIX/TBA|calendar_today|Google Calendar|Apple / ICS)\b", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"\b\d{1,2}:\d{2}\s*(?:AM|PM)?(?:\s*&\s*\d{1,2}:\d{2}\s*(?:AM|PM)?)?\b", " ", text, flags=re.IGNORECASE)
        text = re.sub(rf"\b{re.escape(comedian_name)}\b", " ", text, flags=re.IGNORECASE)
        return re.sub(r"\s+", " ", text).strip(" -|")

    @staticmethod
    def _clean_venue_text(text: str) -> str:
        text = re.sub(r"\b(?:Bad Friends|The Pete Here Now Tour)\b", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"\s+", " ", text).strip(" -|,")
        return text


class SquarespaceExtractorForComedian:
    """Extracts events from a comedian's Squarespace website.

    Discovers the collectionId from the page's SQUARESPACE_CONTEXT JSON,
    then calls the GetItemsByMonth API for the current and next 2 months.
    Only works for sites that have an events collection (type=10).
    """

    _EVENTS_COLLECTION_TYPE = 10

    @staticmethod
    def discover_collection_id(html: str) -> Optional[str]:
        """Extract the events collectionId from Squarespace page HTML.

        Squarespace embeds a SQUARESPACE_CONTEXT object in every page.
        If the current page is an events collection (type=10), we can
        extract its ID and use it with the GetItemsByMonth API.
        """
        match = re.search(
            r"Static\.SQUARESPACE_CONTEXT\s*=\s*({.*?});", html, re.DOTALL
        )
        if not match:
            return None

        try:
            ctx = json.loads(match.group(1))
        except (json.JSONDecodeError, ValueError):
            return None

        collection = ctx.get("collection", {})
        if collection.get("type") != SquarespaceExtractorForComedian._EVENTS_COLLECTION_TYPE:
            return None

        collection_id = collection.get("id", "").strip()
        return collection_id or None

    @staticmethod
    async def extract_event_count(
        scraping_url: str,
        html: str,
        comedian: Comedian,
        fetch_json_fn,
        log_prefix: str,
    ) -> Optional[int]:
        """Count events on a Squarespace comedian website.

        Returns None if this isn't an events-capable Squarespace site
        (caller should fall back to JSON-LD). Returns 0+ to confirm
        platform detection — Squarespace personal sites don't include
        venue/location data, so no venue upserts are possible.
        """
        collection_id = SquarespaceExtractorForComedian.discover_collection_id(html)
        if not collection_id:
            return None

        parsed = urlparse(scraping_url)
        base_domain = f"{parsed.scheme}://{parsed.netloc}"

        from datetime import date

        today = date.today()
        event_count = 0

        for i in range(3):
            month = (today.month + i - 1) % 12 + 1
            year = today.year + (today.month + i - 1) // 12
            month_str = f"{month:02d}-{year}"
            api_url = (
                f"{base_domain}/api/open/GetItemsByMonth"
                f"?month={month_str}&collectionId={collection_id}"
            )

            try:
                data = await fetch_json_fn(api_url, timeout=15)
            except Exception as e:
                Logger.warn(
                    f"{log_prefix}: Squarespace API error for {base_domain} month={month_str}: {e}"
                )
                continue

            if not isinstance(data, list):
                continue

            for raw in data:
                if _is_valid_squarespace_event(raw):
                    event_count += 1

        if event_count > 0:
            Logger.info(
                f"{log_prefix}: {comedian.name} — Squarespace site has {event_count} upcoming events "
                f"(no venue data available for upsert)"
            )

        return event_count


def _is_valid_squarespace_event(raw: dict) -> bool:
    """Check if a raw Squarespace event dict has valid required fields."""
    title = (raw.get("title") or "").strip()
    if not title:
        return False

    start_date_ms = raw.get("startDate")
    if not isinstance(start_date_ms, (int, float)):
        return False

    event_dt = datetime.fromtimestamp(int(start_date_ms) / 1000, tz=timezone.utc)
    return event_dt >= datetime.now(tz=timezone.utc)


class WixExtractorForComedian:
    """Extracts events from a comedian's Wix website.

    Checks if the page has a Wix Events widget by looking for the
    wix-one-events-server reference in the HTML. If found, discovers
    the compId and fetches events via the Wix Events API.
    """

    _EVENTS_MARKER = "wix-one-events"
    _CLIENT_BINDING = "e2814456-fed7-4d1b-a36c-ded753a23ca3"

    @staticmethod
    def has_events_widget(html: str) -> bool:
        """Check if the Wix page has an events widget."""
        return WixExtractorForComedian._EVENTS_MARKER in html

    @staticmethod
    def discover_comp_id(html: str) -> Optional[str]:
        """Try to discover a Wix Events compId from page HTML.

        The compId appears in Wix controller configs or data attributes.
        """
        # Look for compId in Wix controller/widget config JSON
        matches = re.findall(r'"compId"\s*:\s*"(comp-[a-z0-9]+)"', html)
        if not matches:
            return None

        # Prefer compIds that appear near events-related context
        for m in matches:
            # Check if this compId is near an events reference
            idx = html.find(f'"compId":"{m}"')
            if idx >= 0:
                context = html[max(0, idx - 500):idx + 500]
                if "event" in context.lower():
                    return m

        # Fall back to first compId found
        return matches[0] if matches else None

    @staticmethod
    async def extract_event_count(
        scraping_url: str,
        html: str,
        comedian: Comedian,
        fetch_json_fn,
        log_prefix: str,
    ) -> Optional[int]:
        """Count events on a Wix comedian website.

        Returns None if the site doesn't have a Wix Events widget
        (caller should fall back to JSON-LD). Returns 0+ to confirm
        platform detection — Wix comedian sites don't include venue/location
        data, so no venue upserts are possible.
        """
        if not WixExtractorForComedian.has_events_widget(html):
            return None

        comp_id = WixExtractorForComedian.discover_comp_id(html)
        if not comp_id:
            Logger.info(
                f"{log_prefix}: Wix Events widget detected but compId not found"
            )
            return None

        parsed = urlparse(scraping_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        # Fetch access token
        token = await _wix_fetch_token(base_url, fetch_json_fn, log_prefix)
        if not token:
            return None

        # Fetch events to count them (for logging/observability)
        events = await _wix_fetch_events(
            base_url, token, comp_id, fetch_json_fn, log_prefix
        )

        if events:
            Logger.info(
                f"{log_prefix}: {comedian.name} — Wix site has {len(events)} upcoming events "
                f"(no venue data available for upsert)"
            )

        return len(events)


async def _wix_fetch_token(
    base_url: str, fetch_json_fn, log_prefix: str
) -> Optional[str]:
    """Fetch a Wix access token for the site."""
    token_url = f"{base_url}/_api/v1/access-tokens"
    headers = {
        "client-binding": WixExtractorForComedian._CLIENT_BINDING,
        "User-Agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
            "Mobile/15E148 Safari/604.1"
        ),
    }

    try:
        data = await fetch_json_fn(token_url, headers=headers, timeout=15)
    except Exception as e:
        Logger.warn(f"{log_prefix}: Wix token fetch failed: {e}")
        return None

    if not data:
        return None

    apps = data.get("apps", {})
    for app_data in apps.values():
        if app_data.get("intId") == 24:
            return app_data.get("instance")
    return None


async def _wix_fetch_events(
    base_url: str,
    token: str,
    comp_id: str,
    fetch_json_fn,
    log_prefix: str,
) -> List[dict]:
    """Fetch all events from the Wix Events paginated API."""
    events_url = f"{base_url}/_api/wix-one-events-server/web/paginated-events/viewer"
    all_events: List[dict] = []
    offset = 0
    limit = 50
    max_pages = 20

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    for _ in range(max_pages):
        params = {
            "offset": offset,
            "limit": limit,
            "filter": 1,
            "byEventId": "false",
            "members": "false",
            "paidPlans": "false",
            "locale": "en",
            "filterType": 2,
            "sortOrder": 0,
            "draft": "false",
            "compId": comp_id,
        }
        url = f"{events_url}?{urlencode(params)}"

        try:
            data = await fetch_json_fn(url, headers=headers, timeout=15)
        except Exception as e:
            Logger.warn(f"{log_prefix}: Wix events fetch error at offset {offset}: {e}")
            break

        if not data:
            break

        page_events = data.get("events", [])
        all_events.extend(page_events)

        if not data.get("hasMore", False):
            break
        offset += limit

    return all_events


class KomiExtractorForComedian:
    """Extracts events from a comedian's komi.io page.

    komi.io is an SPA that delegates event data to the Bandsintown REST API.
    Rather than rendering the SPA, we extract the artist slug from the URL
    and query Bandsintown directly.
    """

    _BANDSINTOWN_BASE_URL = "https://rest.bandsintown.com"
    _BANDSINTOWN_APP_ID = "komi_0000000000"

    @staticmethod
    def extract_artist_slug(url: str) -> Optional[str]:
        """Extract the artist slug from a komi.io URL.

        e.g. "https://chriskattan.komi.io/" → "chriskattan"
        """
        try:
            hostname = urlparse(url).hostname or ""
        except Exception:
            return None

        if not hostname.endswith(".komi.io"):
            return None

        slug = hostname.removesuffix(".komi.io").strip()
        return slug if slug else None

    @staticmethod
    async def extract_venues(
        scraping_url: str,
        comedian: Comedian,
        club_handler: ClubHandler,
        fetch_json_list_fn,
        log_prefix: str,
    ) -> int:
        """Fetch events from Bandsintown for a komi.io comedian and upsert venues.

        Returns 0 if the artist slug can't be extracted or no events found.
        """
        slug = KomiExtractorForComedian.extract_artist_slug(scraping_url)
        if not slug:
            return 0

        # Use comedian name for the Bandsintown lookup (more reliable than slug)
        artist_name = comedian.name

        now = datetime.now(tz=timezone.utc)
        date_from = now.strftime("%Y-%m-%d")
        date_to = (now + timedelta(days=365)).strftime("%Y-%m-%d")

        params = {
            "app_id": KomiExtractorForComedian._BANDSINTOWN_APP_ID,
            "date": f"{date_from},{date_to}",
        }
        url = (
            f"{KomiExtractorForComedian._BANDSINTOWN_BASE_URL}"
            f"/artists/{quote(artist_name, safe='')}/events?{urlencode(params)}"
        )

        try:
            data = await fetch_json_list_fn(url, timeout=15)
        except Exception as e:
            Logger.warn(f"{log_prefix}: Bandsintown fetch failed for {artist_name}: {e}")
            return 0

        if not data:
            return 0

        count = 0
        for event in data:
            if _bandsintown_event_to_venue(
                event,
                club_handler,
                log_prefix,
                comedian=comedian,
                sample_url=scraping_url,
                platform_hints=["komi", "bandsintown"],
            ):
                count += 1

        return count


def _bandsintown_event_to_venue(
    event: dict,
    club_handler: ClubHandler,
    log_prefix: str,
    comedian: Optional[Comedian] = None,
    sample_url: Optional[str] = None,
    platform_hints: Optional[list[str]] = None,
) -> bool:
    """Extract and upsert a venue from a Bandsintown event. Returns True on success."""
    try:
        venue = event.get("venue", {}) or {}
        country = (venue.get("country") or "").strip()
        if country not in ("United States", "US"):
            return False

        venue_name = (venue.get("name") or "").strip()
        if not venue_name:
            return False

        date_str = event.get("datetime") or event.get("starts_at")
        if not date_str:
            return False

        try:
            event_dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return False

        if event_dt.tzinfo is None:
            event_dt = event_dt.replace(tzinfo=timezone.utc)

        if event_dt < datetime.now(tz=timezone.utc):
            return False

        city = (venue.get("city") or "").strip()
        region = (venue.get("region") or "").strip()
        if region and region not in _US_STATES:
            return False

        address = f"{city}, {region}" if region else city
        zip_code = (venue.get("postal_code") or "").strip()

        venue_dict = {
            "name": venue_name,
            "address": address,
            "zip_code": zip_code,
            "timezone": timezone_from_address(address),
            "discovery_metadata": {
                "source": "comedian_websites",
                "event_urls": [event.get("url") or f"https://www.bandsintown.com/e/{event.get('id', '')}"],
                "platform_hints": platform_hints or ["bandsintown"],
            },
        }
        if comedian is not None:
            venue_dict["discovery_metadata"]["comedian_refs"] = [
                {"uuid": comedian.uuid, "name": comedian.name}
            ]
        if sample_url:
            venue_dict["discovery_metadata"]["sample_urls"] = [sample_url]

        club = club_handler.upsert_for_tour_date_venue(venue_dict)
        return club is not None

    except Exception as e:
        Logger.warn(f"{log_prefix}: Bandsintown venue extraction error: {e}")
        return False
