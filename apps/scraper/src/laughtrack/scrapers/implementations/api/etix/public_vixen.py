"""Fail-closed partial recovery from The Vixen's own event pages."""

import asyncio
import html as html_module
import json
import re
from datetime import datetime
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from laughtrack.core.entities.event.etix import EtixEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from .public_ticket_tailor import _events, _SHOW_TIME

HOME = "https://vixenmchenry.com/"
_COMEDY = re.compile(r"\b(?:comedy|comedian|stand[ -]?up)\b", re.I)
_DOORS = re.compile(r"doors\s+open\s+at\s+(\d{1,2})(?::(\d{2}))?\s*([ap]m)\b", re.I)
_MONTH_DAY = re.compile(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})(?:st|nd|rd|th)?\b", re.I)


def _text(value):
    return " ".join(html_module.unescape(str(value)).casefold().split())


def _owned(url):
    p = urlparse(url or "")
    return p.scheme == "https" and p.netloc == "vixenmchenry.com" and not p.query and not p.fragment and bool(
        re.fullmatch(r"/event/[a-z0-9-]+/", p.path))


def _time(match):
    h, m, ap = match
    if not 1 <= int(h) <= 12 or not 0 <= int(m or 0) <= 59:
        raise ValueError("invalid time")
    return int(h) % 12 + (12 if ap.lower() == "pm" else 0), int(m or 0)


def verify_detail(html, url):
    """Use explicit main-body show time only when JSON-LD identifies the doors."""
    try:
        if not _owned(url):
            return None
        soup = BeautifulSoup(html, "html.parser")
        events = []
        for script in soup.select('script[type="application/ld+json"]'):
            events.extend(e for e in _events(json.loads(script.string or script.get_text())) if e.get("url") == url)
        if len(events) != 1:
            return None
        event = events[0]
        title = html_module.unescape(event.get("name", "")).strip()
        headings = soup.select("h1")
        if not _COMEDY.search(title) or not headings or any(_text(h.get_text(" ", strip=True)) != _text(title) for h in headings):
            return None
        if event.get("eventStatus") != "https://schema.org/EventScheduled":
            return None
        start = datetime.fromisoformat(event["startDate"])
        local = start.astimezone(ZoneInfo("America/Chicago"))
        if start.tzinfo is None or start.utcoffset() != local.utcoffset():
            return None
        dates = soup.select(".ecs-eventDate .decm_date")
        if len(dates) != 1 or datetime.strptime(dates[0].get_text(strip=True), "%m/%d/%Y").date() != local.date():
            return None
        bodies = soup.select(".et_pb_post_content")
        if len(bodies) != 1:
            return None
        headers = bodies[0].select("h2")
        matching = [h for h in headers if _text(h.get_text(" ", strip=True)).startswith(_text(title))]
        if len(matching) != 1:
            return None
        body = " ".join(h.get_text(" ", strip=True) for h in headers)
        days = _MONTH_DAY.findall(body)
        shows, doors = _SHOW_TIME.findall(body), _DOORS.findall(body)
        if len(days) != 1 or len(shows) != 1 or len(doors) != 1:
            return None
        month, day = days[0]
        if datetime.strptime(f"{month} {day} {local.year}", "%B %d %Y").date() != local.date():
            return None
        if _time(doors[0]) != (local.hour, local.minute):
            return None
        hour, minute = _time(shows[0])
        show = local.replace(hour=hour, minute=minute)
        if show < local:
            return None
        return EtixEvent(title=title, start_date=show.isoformat(), time_str=show.strftime("Show at %I:%M %p"),
                         ticket_url=url, event_url=url, ticket_price=0 if re.match(r"^FREE\s", title, re.I) else None)
    except (ValueError, TypeError, KeyError, AttributeError):
        return None


async def fetch_highlights(fetch_html, club):
    """The official homepage is a partial inventory, even if every card validates."""
    if club.id != 9074 or club.timezone != "America/Chicago":
        return []
    home = await asyncio.wait_for(fetch_html(HOME), timeout=15)
    soup = BeautifulSoup(home or "", "html.parser")
    urls = sorted({a["href"] for a in soup.select("a[href]")
                   if _owned(a["href"]) and _COMEDY.search(a.get_text(" ", strip=True))})
    semaphore = asyncio.Semaphore(2)

    async def fetch(url):
        async with semaphore:
            try:
                html = await asyncio.wait_for(fetch_html(url), timeout=12)
                event = verify_detail(html or "", url)
                if event is None:
                    Logger.warn(f"Vixen partial fallback rejected unverified detail: {url}")
                return event
            except Exception as error:
                Logger.warn(f"Vixen partial fallback detail failed: {url}: {type(error).__name__}")
                return None

    results = await asyncio.gather(*(fetch(url) for url in urls[:12]))
    return [event for event in results if event is not None]
