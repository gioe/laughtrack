"""Explicitly timed featured performances from Ann Arbor's partial homepage."""

import asyncio
import re
from datetime import datetime
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from laughtrack.core.entities.event.etix import EtixEvent

HOME = "https://www.aacomedy.com/"
_MONTH = r"January|February|March|April|May|June|July|August|September|October|November|December"
_ROW = re.compile(rf"({_MONTH})\s+(\d{{1,2}})(?:st|nd|rd|th)?\s*[-–—]\s*(.+)", re.I)
_CLOCK = re.compile(r"(\d{1,2}):(\d{2})\s*([ap]m)", re.I)
_NON_SHOW = re.compile(r"\b(?:gift|workshop|class|happy hour|calendar)\b", re.I)


def _text(node):
    return " ".join(node.get_text(" ", strip=True).split())


def _series(url):
    parsed = urlparse(url or "")
    if parsed.scheme != "https" or parsed.hostname != "www.etix.com":
        return None
    # The venue's observed series slugs end in a two-digit booking year.
    match = re.fullmatch(r"/ticket/e/(\d+)/([a-z-]+)(\d{2})(?:-ann-arbor-ann-arbor-comedy-showcase)?/?", parsed.path)
    if not match:
        return None
    return match[1], 2000 + int(match[3])


def extract_highlights(html):
    """Require featured heading, exact times, and matching dated Etix card."""
    soup = BeautifulSoup(html or "", "html.parser")
    card_titles = {_text(node) for node in soup.select(".eventSlide .eventTitle")}
    headings = [node for node in soup.select("h1") if _text(node) in card_titles]
    if len(headings) != 1:
        return []
    heading = headings[0]
    title = _text(heading)
    if not title or _NON_SHOW.search(title):
        return []
    section = heading.find_parent(class_="dmRespCol")
    if section is None:
        return []
    # The feature's own biography must explicitly describe its named subject as
    # a comedian. Neither a title alone nor an unrelated act's biography suffices.
    overview = any(_text(node) == "Comedian Overview" for node in section.select("h3"))
    biography = " ".join(_text(node) for node in section.select("p"))
    named_comedian = re.search(
        rf"\b{re.escape(title)}\s+(?:is|has become)\s+[^.!?]{{0,160}}\bcomedians?\b",
        biography, re.I,
    )
    performers = [title] if overview and named_comedian else []
    cards = [card for card in soup.select(".eventSlide")
             if card.select_one(".eventTitle") is not None and _text(card.select_one(".eventTitle")) == title]
    if len(cards) != 1:
        return []
    card = cards[0]
    tickets = {_series(a.get("href")) for a in card.select(".eventLinkWrapper a[href]")}
    if len(tickets) != 1 or None in tickets:
        return []
    identity = tickets.pop()
    if identity not in {_series(a.get("href")) for a in section.select("a[href]")}:
        return []
    date_node = card.select_one(".eventTime")
    card_date = _text(date_node) if date_node else ""
    dated = re.fullmatch(rf"({_MONTH})\s+((?:\d{{1,2}}(?:st|nd|rd|th)?(?:\s*(?:&|,)\s*|\s+)?)+)", card_date, re.I)
    if dated is None:
        return []
    expected_days = {int(day) for day in re.findall(r"\d+", dated[2])}
    month = datetime.strptime(dated[1].title(), "%B").month
    ticket_id, year = identity
    ticket_url = f"https://www.etix.com/ticket/e/{ticket_id}"
    events, seen, actual_days = [], set(), set()
    rows = section.select("h4")
    if not rows:
        return []
    for row in rows:
        match = _ROW.fullmatch(_text(row))
        if match is None or datetime.strptime(match[1].title(), "%B").month != month:
            return []
        day = int(match[2])
        clocks = re.split(r"\s*&\s*", match[3])
        for raw_clock in clocks:
            clock = _CLOCK.fullmatch(raw_clock)
            if clock is None or not 1 <= int(clock[1]) <= 12:
                return []
            hour = int(clock[1]) % 12 + (12 if clock[3].lower() == "pm" else 0)
            try:
                start = datetime(year, month, day, hour, int(clock[2])).isoformat()
            except ValueError:
                return []
            if start in seen:
                return []
            seen.add(start)
            actual_days.add(day)
            events.append(EtixEvent(title=title, start_date=start, time_str=raw_clock,
                                   ticket_url=ticket_url, event_url=ticket_url, performer_names=performers))
    return events if actual_days == expected_days else []


async def fetch_highlights(fetch_html, club):
    if club.id != 16122 or club.timezone != "America/Detroit":
        return []
    html = await asyncio.wait_for(fetch_html(HOME), timeout=15)
    return extract_highlights(html)
