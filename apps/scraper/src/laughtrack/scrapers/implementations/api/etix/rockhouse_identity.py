"""Verify conflicted Rockhouse series tickets against their individual WordPress posts."""

import asyncio
import json
import re
from datetime import datetime
from html import unescape
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from laughtrack.core.entities.event.etix import EtixEvent
from laughtrack.foundation.utilities.number import parse_price_text
from .rockhouse import _CARD_CLASSES, _iso_datetime, _owned_elements, _ticket_identity


def _text(value):
    return " ".join(unescape(str(value or "")).replace("’", "'").casefold().split())


def _origin(url):
    parsed = urlsplit(url or "")
    return (parsed.scheme, parsed.netloc.lower())


def _structured(soup):
    def nodes(value):
        if isinstance(value, list):
            for item in value:
                yield from nodes(item)
        elif isinstance(value, dict):
            yield value
            if "@graph" in value:
                yield from nodes(value["@graph"])

    for script in soup.select('script[type="application/ld+json"]'):
        try:
            yield from nodes(json.loads(script.get_text()))
        except (ValueError, TypeError):
            continue


def _calendar_address(soup, source_url, club):
    """Use the calendar's independent Place address, with matching club city/state.

    The old database street can name a different entrance; never infer that two
    different streets are equivalent. Detail and calendar must agree exactly.
    """
    addresses = set()
    if not club.city or not club.state:
        return None
    for node in _structured(soup):
        address = node.get("address")
        if (
            node.get("@type") != "Place"
            or _origin(node.get("@id")) != _origin(source_url)
            or not isinstance(address, dict)
        ):
            continue
        if (
            _text(address.get("addressLocality")) != _text(club.city)
            or _text(address.get("addressRegion")) != _text(club.state)
            or str(address.get("postalCode", "")) != str(club.zip_code)
        ):
            continue
        street = _text(address.get("streetAddress"))
        if street:
            addresses.add((street, _text(address["addressLocality"])))
    return next(iter(addresses)) if len(addresses) == 1 else None


def _post_ids(soup, identity):
    """Require every owned ticket reference to point to one explicit CTA post ID."""
    posts = set()
    for wrapper in soup.select(".rhp-event__single-event--list, .rhp-event__single-series--list"):
        for link in _owned_elements(wrapper, 'a[href*="etix.com/ticket/p/"]'):
            if _ticket_identity(link.get("href", "")) != identity:
                continue
            cta = None
            for parent in link.parents:
                if parent is wrapper:
                    break
                match = re.fullmatch(r"ctaspan-([1-9][0-9]*)", parent.get("id", ""))
                if match:
                    cta = match.group(1)
                    break
                if _CARD_CLASSES.intersection(parent.get("class") or []):
                    break
            if cta is None:
                return set()
            posts.add(cta)
    return posts


def _ticket_url(value, identity):
    if not isinstance(value, str):
        return False
    parsed = urlsplit(value)
    return (
        parsed.scheme == "https"
        and parsed.hostname in {"www.etix.com", "etix.com"}
        and _ticket_identity(value) == identity
    )


def verify_individual_post(html, post_id, identity, candidates, source_url, club, address):
    """Return a performance only when visible and structured primary evidence agree."""
    soup = BeautifulSoup(html or "", "html.parser")
    main = soup.select(".singleEventDetails")
    if len(main) != 1 or address is None:
        return None
    main = main[0]
    headings = main.select("h1")
    dates = main.select(".eventStDate")
    clocks = main.select(".eventDoorStartDate")
    venues = main.select(".eventVenue .venueLink")
    if any(len(values) != 1 for values in (headings, dates, clocks, venues)):
        return None
    title = headings[0].get_text(" ", strip=True)
    if not title or _text(venues[0].get_text(" ", strip=True)) != _text(club.name):
        return None
    primary_links = main.select(f'[id="ctaspan-{post_id}"] a[href]')
    if not primary_links or any(not _ticket_url(link["href"], identity) for link in primary_links):
        return None
    events = [node for node in _structured(soup) if node.get("@type") == "Event"]
    if len(events) != 1:
        return None
    event = events[0]
    event_url = event.get("url", "")
    location = event.get("location") or {}
    if not isinstance(location, dict) or _text(location.get("name")) != _text(club.name):
        return None
    # Detail JSON-LD gives only street/city; calendar Place also establishes state/ZIP.
    actual_address = location.get("address")
    if not isinstance(actual_address, str) or _text(actual_address).strip(" ,") != ", ".join(address):
        return None
    if _origin(event_url) != _origin(source_url) or not urlsplit(event_url).path.startswith("/event/"):
        return None
    if _text(event.get("name")) != _text(title):
        return None
    offers = event.get("offers")
    offers = offers if isinstance(offers, list) else [offers]
    if not offers or any(
        not isinstance(offer, dict) or not _ticket_url(offer.get("url"), identity) for offer in offers
    ):
        return None
    try:
        start = datetime.fromisoformat(event.get("startDate", "").replace("Z", "+00:00"))
        if start.utcoffset() is None:
            return None
        local = start.astimezone(ZoneInfo(club.timezone))
        if start.replace(tzinfo=None) != local.replace(tzinfo=None):
            return None
        wall = local.replace(tzinfo=None).isoformat()
        # A different time is not permission to rewrite an existing performance.
        if {row["start_date"] for row in candidates} != {wall}:
            return None
        visible = _iso_datetime(dates[0].get_text(" ", strip=True), clocks[0].get_text(" ", strip=True), local.year)
        if visible != wall:
            return None
    except (ValueError, TypeError, KeyError):
        return None
    cost = main.select(".eventCost")
    price = (
        parse_price_text(cost[0].get_text(" ", strip=True), dollar_only=True, detect_free=False)
        if len(cost) == 1
        else None
    )
    return EtixEvent(
        title=title,
        start_date=wall,
        time_str=clocks[0].get_text(" ", strip=True),
        ticket_url=offers[0]["url"],
        event_url=event_url,
        ticket_price=price if price and price > 0 else None,
    )


async def resolve_rockhouse_conflicts(html, source_url, club, conflicts, fetch):
    """Bound detail requests to explicit numeric conflicts and owned same-origin CTA IDs."""
    soup = BeautifulSoup(html, "html.parser")
    address = _calendar_address(soup, source_url, club)
    if address is None or _origin(source_url)[0] != "https":
        return [], conflicts
    pending = []
    for identity, candidates in conflicts.items():
        if not identity.isdigit():
            continue
        posts = _post_ids(soup, identity)
        if len(posts) == 1:
            pending.append((identity, posts.pop(), candidates))
    semaphore = asyncio.Semaphore(2)

    async def resolve(identity, post, candidates):
        parsed = urlsplit(source_url)
        url = f"{parsed.scheme}://{parsed.netloc}/?p={post}"
        try:
            async with semaphore:
                detail = await asyncio.wait_for(fetch(url), timeout=8)
            return identity, verify_individual_post(detail, post, identity, candidates, source_url, club, address)
        except Exception:
            # Caller retains the original conflict and records incomplete diagnostics.
            return identity, None

    resolved, remaining = [], dict(conflicts)
    for identity, event in await asyncio.gather(*(resolve(*entry) for entry in pending[:8])):
        if event is not None:
            resolved.append(event)
            remaining.pop(identity)
    return resolved, remaining
