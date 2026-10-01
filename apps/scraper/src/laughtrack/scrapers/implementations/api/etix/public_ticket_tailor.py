"""Verified highlights linked by Laughing Tap; never a complete Etix calendar."""

import asyncio
import json
import re
from datetime import datetime
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from laughtrack.core.entities.event.etix import EtixEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.implementations.ticket_tailor.extractor import _parse_datetime, _parse_location

HOME = "https://laughingtap.com/"
MAX_DETAILS = 12
_SHOW_TIME = re.compile(r"show\s+(?:starts?\s+(?:at\s+)?|at\s+)(\d{1,2})(?::(\d{2}))?\s*([ap]m)\b", re.I)


def ticket_identity(url):
    parsed = urlparse(url or "")
    if parsed.scheme != "https" or parsed.netloc != "www.tickettailor.com" or parsed.query or parsed.fragment:
        return None
    match = re.fullmatch(r"/events/milwaukeecomedy/(\d+)/?", parsed.path)
    return match.group(1) if match else None


def _text(value):
    return " ".join(str(value).casefold().split())


def _events(value):
    if isinstance(value, list):
        for item in value:
            yield from _events(item)
    elif isinstance(value, dict):
        if value.get("@type") == "Event":
            yield value
        yield from _events(value.get("@graph", []))


def verify_detail(html, url, club):
    """Require matching structured and visible title, year, start time and venue."""
    try:
        identity = ticket_identity(url)
        if not identity or club.timezone != "America/Chicago":
            return None
        soup = BeautifulSoup(html, "html.parser")
        events = []
        for script in soup.select('script[type="application/ld+json"]'):
            events.extend(_events(json.loads(script.string or script.get_text())))
        if len(events) != 1:
            return None
        event = events[0]
        headings = soup.select("h1.hero__title")
        dates = soup.select(".hero__meta .event-meta__date")
        locations = soup.select(".hero__meta .event-meta__location")
        if len(headings) != 1 or len(dates) != 1 or len(locations) != 1:
            return None
        title = headings[0].get_text(" ", strip=True)
        if not title or _text(title) != _text(event.get("name", "")):
            return None
        if event.get("eventStatus") != "https://schema.org/EventScheduled":
            return None
        start = datetime.fromisoformat(event["startDate"])
        parsed = _parse_datetime(dates[0].get_text(" ", strip=True))
        if not parsed or start.tzinfo is None or parsed[1] != club.timezone:
            return None
        local = start.astimezone(ZoneInfo(club.timezone))
        if start.utcoffset() != local.utcoffset() or parsed[0] != local.replace(tzinfo=None):
            return None
        visible_name, visible_zip = _parse_location(locations[0].get_text(" ", strip=True))
        location = event.get("location", {})
        if (_text(visible_name) != "the laughing tap" or visible_zip != "53202"
                or _text(location.get("name", "")) != "the laughing tap"
                or str(location.get("address", {}).get("postalCode", "")) != "53202"):
            return None
        description = soup.select_one(".detail-content__description")
        times = _SHOW_TIME.findall(description.get_text(" ", strip=True) if description else "")
        if not times or any(not 1 <= int(h) <= 12 or not 0 <= int(m or 0) <= 59 for h, m, ap in times):
            return None
        if any((int(h) % 12 + (12 if ap.lower() == "pm" else 0), int(m or 0))
                            != (local.hour, local.minute) for h, m, ap in times):
            return None
        offers = event.get("offers", [])
        if isinstance(offers, dict):
            offers = [offers]
        if not offers or any(ticket_identity(offer.get("url")) != identity for offer in offers):
            return None
        # Unknown remains unknown; JSON-LD zero placeholders are never prices.
        return EtixEvent(title=title, start_date=start.isoformat(), time_str=local.strftime("Show at %I:%M %p"),
                         ticket_url=url, event_url=url, ticket_price=None)
    except (TypeError, ValueError, KeyError, AttributeError):
        return None


async def fetch_highlights(fetch_html, club):
    """Fetch at most twelve venue-owned links with two concurrent requests."""
    home = await asyncio.wait_for(fetch_html(HOME), timeout=15)
    soup = BeautifulSoup(home or "", "html.parser")
    urls = sorted({f"https://www.tickettailor.com/events/milwaukeecomedy/{identity}"
                   for link in soup.select("a[href]")
                   if (identity := ticket_identity(link.get("href")))})
    semaphore = asyncio.Semaphore(2)

    async def fetch(url):
        async with semaphore:
            try:
                html = await asyncio.wait_for(fetch_html(url), timeout=30)
                event = verify_detail(html or "", url, club)
                if event is None:
                    Logger.warn(f"Laughing Tap partial fallback rejected unverified TicketTailor detail: {url}")
                return event
            except Exception as error:
                Logger.warn(f"Laughing Tap partial fallback detail failed: {url}: {type(error).__name__}")
                return None

    results = await asyncio.gather(*(fetch(url) for url in urls[:MAX_DETAILS]))
    return [event for event in results if event is not None]
