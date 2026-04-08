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
from urllib.parse import quote, urlencode, urlparse

from laughtrack.core.entities.club.handler import ClubHandler
from laughtrack.core.entities.comedian.model import Comedian
from laughtrack.core.entities.show.model import Show
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
    return None


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
    async def extract_shows(
        scraping_url: str,
        html: str,
        comedian: Comedian,
        club_handler: ClubHandler,
        fetch_json_fn,
        log_prefix: str,
    ) -> Optional[List[Show]]:
        """Try to detect events from a Squarespace comedian website.

        Returns None if this isn't an events-capable Squarespace site
        (caller should fall back to JSON-LD). Returns an empty list
        always — Squarespace personal sites don't include venue/location
        data in the API response, so we can't create proper Show records.

        The return value signals platform detection success so the caller
        can update the strategy to "squarespace" for future runs.
        The event count is logged for observability.
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
                f"(no venue data available for Show creation)"
            )

        # Return empty list (not None) to confirm this IS a Squarespace events site
        return []


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
    async def extract_shows(
        scraping_url: str,
        html: str,
        comedian: Comedian,
        club_handler: ClubHandler,
        fetch_json_fn,
        log_prefix: str,
    ) -> Optional[List[Show]]:
        """Try to detect events from a Wix comedian website.

        Returns None if the site doesn't have a Wix Events widget
        (caller should fall back to JSON-LD). Returns an empty list
        always — Wix comedian sites don't include venue/location data
        in the events API, so we can't create proper Show records.

        The return value signals platform detection success so the caller
        can update the strategy to "wix" for future runs.
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
                f"(no venue data available for Show creation)"
            )

        # Return empty list (not None) to confirm this IS a Wix Events site
        return []


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
    async def extract_shows(
        scraping_url: str,
        comedian: Comedian,
        club_handler: ClubHandler,
        fetch_json_list_fn,
        log_prefix: str,
    ) -> Optional[List[Show]]:
        """Fetch events from Bandsintown for a komi.io comedian.

        Returns None if the artist slug can't be extracted.
        Returns an empty list if Bandsintown returns no events.
        """
        slug = KomiExtractorForComedian.extract_artist_slug(scraping_url)
        if not slug:
            return None

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
            return []

        if not data:
            return []

        shows: List[Show] = []
        for event in data:
            show = _bandsintown_event_to_show(
                event, comedian, club_handler, log_prefix
            )
            if show:
                shows.append(show)

        return shows


def _bandsintown_event_to_show(
    event: dict,
    comedian: Comedian,
    club_handler: ClubHandler,
    log_prefix: str,
) -> Optional[Show]:
    """Convert a Bandsintown event to a Show (mirrors TourDatesScraper logic)."""
    try:
        venue = event.get("venue", {}) or {}
        country = (venue.get("country") or "").strip()
        if country not in ("United States", "US"):
            return None

        venue_name = (venue.get("name") or "").strip()
        if not venue_name:
            return None

        date_str = event.get("datetime") or event.get("starts_at")
        if not date_str:
            return None

        try:
            event_dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None

        if event_dt.tzinfo is None:
            event_dt = event_dt.replace(tzinfo=timezone.utc)

        if event_dt < datetime.now(tz=timezone.utc):
            return None

        city = (venue.get("city") or "").strip()
        region = (venue.get("region") or "").strip()
        if region and region not in _US_STATES:
            return None

        address = f"{city}, {region}" if region else city
        zip_code = (venue.get("postal_code") or "").strip()

        venue_dict = {
            "name": venue_name,
            "address": address,
            "zip_code": zip_code,
            "timezone": timezone_from_address(address),
        }

        club = club_handler.upsert_for_tour_date_venue(venue_dict)
        if not club:
            return None

        show_url = event.get("url") or f"https://www.bandsintown.com/e/{event.get('id', '')}"

        return Show(
            name=f"{comedian.name} at {venue_name}",
            club_id=club.id,
            date=event_dt,
            show_page_url=show_url,
            description=event.get("description") or event.get("title"),
            timezone=club.timezone,
            lineup=[comedian],
        )

    except Exception as e:
        Logger.warn(f"{log_prefix}: Bandsintown event conversion error: {e}")
        return None
