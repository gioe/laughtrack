"""Verified Etix ticket cards on the Des Plaines Tribe comedy calendar."""

import json
import re
from datetime import datetime
from html import unescape
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from laughtrack.core.entities.event.etix import EtixEvent


def extract_tribe_events(html: str) -> list[EtixEvent]:
    """Require matching visible and structured times; leave comedy selection to caller.

    Explicit film/theatre evidence takes precedence over the site's broad comedy
    category. Missing evidence raises so a caller cannot reconcile partial data
    as a complete calendar. This deliberately supports the captured list format,
    not every configuration of The Events Calendar.
    """
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("article.tribe-events-calendar-list__event")
    if not cards:
        raise ValueError("No verified Tribe event cards")
    if soup.select_one("a.tribe-events-c-nav__next[href], .tribe-events-c-nav__next a[href]"):
        raise ValueError("Tribe calendar pagination requires another fetch")

    structured = {}
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            value = json.loads(script.get_text())
        except (ValueError, TypeError):
            continue
        nodes = value if isinstance(value, list) else [value]
        for node in nodes:
            if isinstance(node, dict) and node.get("@type") == "Event" and node.get("url"):
                key = node["url"].rstrip("/")
                if key in structured and structured[key] != node:
                    raise ValueError("Conflicting Tribe structured events")
                structured[key] = node

    events = []
    seen = set()
    for card in cards:
        title_link = card.select_one(".tribe-events-calendar-list__event-title-link[href]")
        if title_link is None:
            raise ValueError("Tribe card missing event identity")
        title = title_link.get_text(" ", strip=True)
        description = card.select_one(".tribe-events-calendar-list__event-description")
        evidence = title + " " + (description.get_text(" ", strip=True) if description else "")
        categories = set(card.get("class", []))
        if categories.intersection(
            {
                "tribe_events_cat-movies",
                "tribe_events_cat-movie",
                "tribe_events_cat-theater",
                "tribe_events_cat-theatre",
            }
        ) or re.search(r"\bscreening\b|\btheatrical experience\b|\bone[- ](?:woman|man) show\b", evidence, re.I):
            continue
        event_url = title_link["href"]
        node = structured.get(event_url.rstrip("/"))
        if not node or unescape(node.get("name", "")) != title:
            raise ValueError(f"Tribe card lacks matching structured identity: {title}")
        raw_start = node.get("startDate", "")
        if not isinstance(raw_start, str) or not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", raw_start):
            raise ValueError(f"Tribe event lacks exact showtime: {title}")
        start = datetime.fromisoformat(raw_start.replace("Z", "+00:00"))
        if start.utcoffset() is None:
            raise ValueError(f"Tribe event lacks timezone: {title}")
        visible = card.select_one("time[datetime]")
        clock = re.search(r"@\s*(\d{1,2}:\d{2}\s*[ap]m)\b", visible.get_text(" ", strip=True) if visible else "", re.I)
        if visible is None or not clock or visible["datetime"] != start.date().isoformat():
            raise ValueError(f"Tribe visible date/time missing or conflicting: {title}")
        wall_time = datetime.strptime(clock.group(1).upper(), "%I:%M %p").time()
        if wall_time != start.time():
            raise ValueError(f"Tribe visible and structured times disagree: {title}")
        ticket_urls = {
            anchor["href"]
            for anchor in card.select("a[href]")
            if urlparse(anchor["href"]).hostname in {"etix.com", "www.etix.com"}
            and urlparse(anchor["href"]).scheme == "https"
            and re.match(r"^/ticket/p/\d+(?:/|$)", urlparse(anchor["href"]).path)
        }
        if len(ticket_urls) != 1:
            raise ValueError(f"Tribe card lacks one individual Etix ticket: {title}")
        ticket_url = ticket_urls.pop()
        if ticket_url in seen:
            raise ValueError("Duplicate Tribe ticket identity")
        seen.add(ticket_url)
        events.append(
            EtixEvent(
                title=title,
                start_date=raw_start,
                time_str=visible.get_text(" ", strip=True),
                ticket_url=ticket_url,
                event_url=event_url,
            )
        )
    return events
