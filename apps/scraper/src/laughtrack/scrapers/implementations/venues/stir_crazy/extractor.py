"""Strict matching of calendar performances to public detail-page offers."""

import calendar
import json
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from .data import StirCrazyEvent

TZ = ZoneInfo("America/Phoenix")
_NON_PERFORMANCE = re.compile(r"\b(private events?|gift (?:cards?|certificates?|tickets?)|workshops?|class(?:es)?)\b", re.I)
_SHOW_LABEL = re.compile(
    r"\b(comedy|comic|mic|show|showcase|class|night|funnies|funniest|universe|life of|tons of fun|presents|special|party)\b", re.I
)


def excluded_event(event):
    title = event.get("Title", "")
    return bool(
        event.get("PrivateEvent") or event.get("IsHiddenFromPublic")
        or title.strip().casefold() == "no show tonight"
        or (_NON_PERFORMANCE.search(title) and not re.search(r"\bshowcase\b", title, re.I))
    )


def calendar_items(payload, year, month, origin):
    wrapper = payload.get("d") if isinstance(payload, dict) else None
    if not isinstance(wrapper, dict) or wrapper.get("IsSuccess") is not True:
        raise ValueError(f"Stir Crazy calendar {year}-{month:02d} returned an unsuccessful or null envelope")
    result = wrapper.get("Result")
    if not isinstance(result, dict) or not isinstance(result.get("CalendarDays"), list):
        raise ValueError(f"Stir Crazy calendar {year}-{month:02d} days are missing")
    days = result["CalendarDays"]
    if {d.get("DayNumber") for d in days if isinstance(d, dict)} != set(range(1, calendar.monthrange(year, month)[1] + 1)):
        raise ValueError(f"Stir Crazy calendar month {year}-{month:02d} is incomplete")
    items = []
    for day in days:
        if not isinstance(day.get("CalendarItems"), list):
            raise ValueError("Stir Crazy calendar items are missing")
        for item in day["CalendarItems"]:
            event, show = item.get("Event"), item.get("Show")
            if not isinstance(event, dict) or not isinstance(show, dict):
                raise ValueError("Stir Crazy calendar performance is malformed")
            if item.get("IsTBA") or event.get("IsTBA") or excluded_event(event):
                continue
            title, slug = event.get("Title"), event.get("URL")
            if not title or not isinstance(slug, str) or not re.fullmatch(r"[a-zA-Z0-9-]+", slug):
                raise ValueError(f"Stir Crazy calendar {year}-{month:02d} performance {title!r} lacks title or local URL: {slug!r}")
            start = datetime.strptime(show["DateLabel"] + " " + show["MilitaryTime"], "%m/%d/%Y %H:%M").replace(tzinfo=TZ)
            if (start.year, start.month, start.day) != (year, month, day["DayNumber"]):
                raise ValueError("Stir Crazy calendar performance disagrees with requested month/day")
            items.append({"name": title.strip(), "start": start, "url": urljoin(origin + "/", slug),
                          "sold_out": show.get("IsSoldOut") is True})
    return items


def _person_name(name, description="", explicit=False):
    # Person is boilerplate in this site's JSON-LD, including for Open Mic.
    # Accept name-shaped values only with biography corroboration or an
    # explicitly labeled supporting-comedian link.
    return bool(isinstance(name, str) and not _SHOW_LABEL.search(name)
                and re.fullmatch(r"[\wÀ-ž.'’-]+(?: [\wÀ-ž.'’-]+){1,3}", name)
                and (explicit or name.casefold() in description.casefold()))


def extract_details(html, url, expected, performer_overrides=None):
    if performer_overrides is not None and (
        not isinstance(performer_overrides, dict) or any(
            not isinstance(names, list) or not names or any(not isinstance(name, str) or not name.strip() for name in names)
            for names in performer_overrides.values()
        )
    ):
        raise ValueError("Stir Crazy performer overrides must map dated event paths to name lists")
    soup = BeautifulSoup(html or "", "html.parser")
    nodes = []
    for script in soup.select('script[type="application/ld+json"]'):
        parsed = json.loads(script.string or script.get_text())
        nodes.extend(parsed if isinstance(parsed, list) else parsed.get("@graph", [parsed]))
    events = {}
    for node in nodes:
        if not isinstance(node, dict) or node.get("@type") != "ComedyEvent":
            continue
        start = datetime.fromisoformat(node["startDate"])
        start = start.replace(tzinfo=TZ) if start.tzinfo is None else start.astimezone(TZ)
        existing = events.setdefault(start, [])
        if existing and {k: v for k, v in node.items() if k != "offers"} != {
            k: v for k, v in existing[0].items() if k != "offers"
        }:
            raise ValueError(f"Stir Crazy detail {url} has conflicting performance timestamp {start.isoformat()}")
        if node not in existing:
            existing.append(node)
    description = soup.select_one("#divDesc")
    description = description.get_text(" ", strip=True) if description else ""
    label = soup.select_one("#divAlsoFeaturingLabel")
    supporting = []
    if label:
        for link in label.parent.select('a[href*="/Comedians/"]'):
            name = link.get_text(" ", strip=True)
            if _person_name(name, explicit=True):
                supporting.append(name)
    extracted = []
    for item in expected:
        variants = events.get(item["start"])
        node = variants[0] if variants else None
        if node is None or node.get("name", "").strip() != item["name"]:
            raise ValueError(f"Stir Crazy detail {url} is missing calendar performance {item['name']!r} at {item['start'].isoformat()}")
        ticket_options = []
        ticket_url = None
        for variant in variants:
            offer = variant.get("offers")
            if not isinstance(offer, dict):
                raise ValueError(f"Stir Crazy detail {url} has no verified ticket offer at {item['start'].isoformat()}")
            purchase_url = offer.get("url")
            if not isinstance(purchase_url, str) or urlparse(purchase_url).scheme != "https" or urlparse(purchase_url).hostname not in {"stircrazycomedyclub.com", "www.stircrazycomedyclub.com"}:
                raise ValueError(f"Stir Crazy detail {url} has no official ticket URL at {item['start'].isoformat()}")
            if ticket_url and purchase_url != ticket_url:
                raise ValueError(f"Stir Crazy detail {url} has conflicting offer URLs")
            ticket_url = purchase_url
            price = offer.get("price", offer.get("lowPrice"))
            price = float(price) if price is not None else None
            if price is not None and (price < 0 or not price < float("inf")):
                raise ValueError(f"Stir Crazy detail {url} has invalid price")
            tier = "General Admission"
            if len(variants) > 1:
                tier = _ticket_tier(soup, item["start"], price, url)
            ticket_options.append({"price": price, "ticket_type": tier, "sold_out": item["sold_out"] or
                str(offer.get("availability", "")).rsplit("/", 1)[-1] == "SoldOut"})
        people = node.get("performer", [])
        people = people if isinstance(people, list) else [people]
        names = [p["name"] for p in people if isinstance(p, dict) and _person_name(p.get("name"), description)]
        # Some custom programs name acts only in prose, while the Person schema
        # incorrectly repeats the program title. Exact dated event-path overrides are
        # verified from that event's official description, not inferred names.
        override_key = f"{urlparse(url).path}#{item['start'].date().isoformat()}"
        names = (performer_overrides or {}).get(override_key, names)
        names = list(dict.fromkeys(names + supporting))
        extracted.append(StirCrazyEvent(item["name"], item["start"], ticket_url,
            all(t["sold_out"] for t in ticket_options), ticket_options[0]["price"], names, ticket_options))
    return extracted


def _ticket_tier(soup, start, price, url):
    """Native duplicate JSON-LD timestamps can describe distinct ticket tiers."""
    matches = set()
    for option in soup.select("#lstShows option[value]"):
        match = re.fullmatch(r"\w+, (\w+ \d+) @ (\d+:\d+[ap]m)(?: - (.+?) -)?\s*\$(\d+(?:\.\d+)?)(?:\s*\*\* Only a few seats left \*\*)?", option.get_text(" ", strip=True), re.I)
        if not match:
            continue
        date = datetime.strptime(f"{match[1]} {start.year} {match[2]}", "%b %d %Y %I:%M%p").replace(tzinfo=TZ)
        if date == start and float(match[4]) == price:
            matches.add(match[3].strip() if match[3] else "General Admission")
    if len(matches) != 1:
        raise ValueError(f"Stir Crazy detail {url} cannot verify distinct ticket tier at {start.isoformat()} price {price}")
    return matches.pop()
