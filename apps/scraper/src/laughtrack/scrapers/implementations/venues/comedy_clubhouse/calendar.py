"""Validate the public TicketSource promoter-list pagination contract."""

import html
import re
from urllib.parse import urlparse

from laughtrack.core.entities.event.comedy_clubhouse import ComedyClubhouseEvent, _parse_iso_local

ENDPOINT = "https://www.ticketsource.com/ticketshop/web/promoter-list-detailed_ajax.php"
ORGANIZER = "/thecomedyclubhouse"
PAGE_SIZE = 12
MAX_PAGES = 20


def is_organizer_url(url):
    parsed = urlparse(url)
    return (parsed.scheme == "https" and parsed.netloc in {"www.ticketsource.com", "www.ticketsource.us"}
            and parsed.path.rstrip("/") == ORGANIZER and not parsed.query and not parsed.fragment)


def _owned_path(value, pattern):
    if not isinstance(value, str):
        raise ValueError("missing TicketSource link")
    parsed = urlparse(value)
    if parsed.netloc and (parsed.scheme != "https" or parsed.netloc not in {"www.ticketsource.com", "www.ticketsource.us"}):
        raise ValueError("foreign TicketSource link")
    if parsed.scheme and not parsed.netloc or parsed.query or parsed.fragment or not re.fullmatch(pattern, parsed.path):
        raise ValueError("unexpected TicketSource link path")
    return parsed.path


def parse_page(payload):
    """Return (EOF, [(native identity, event)]) or reject the entire page."""
    # The real public endpoint omits `events` at a terminal offset beyond
    # the inventory. Only its exact observed EOF envelope proves emptiness.
    if isinstance(payload, dict) and set(payload) == {"eof"} and payload["eof"] is True:
        return True, []
    if (not isinstance(payload, dict) or set(payload) != {"eof", "events"}
            or type(payload.get("eof")) is not bool or not isinstance(payload.get("events"), list)):
        raise ValueError("invalid calendar envelope")
    rows = payload["events"]
    if len(rows) > PAGE_SIZE or (not payload["eof"] and len(rows) != PAGE_SIZE):
        raise ValueError("incomplete nonterminal calendar page")
    parsed = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("invalid performance record")
        identity = row.get("performanceId")
        if not isinstance(identity, str) or not re.fullmatch(r"[1-9]\d*", identity):
            raise ValueError("invalid performance identity")
        if row.get("venueName") != "The Comedy Clubhouse" or row.get("venueLocation") != "IL":
            raise ValueError("unexpected performance venue")
        title = row.get("eventTitle")
        if not isinstance(title, str) or not title.strip() or "<" in title or ">" in title:
            raise ValueError("invalid performance title")
        start = row.get("performanceDateTimeMeta")
        if not isinstance(start, str) or _parse_iso_local(start, "America/Chicago") is None:
            raise ValueError("invalid performance timestamp")
        info = _owned_path(row.get("infoLinkTime"), r"/thecomedyclubhouse/[a-z0-9-]+/\d{4}-\d{2}-\d{2}/\d{2}:\d{2}/t-[a-z]+")
        if f"/{start[:10]}/{start[11:]}/" not in info:
            raise ValueError("performance URL disagrees with timestamp")
        event_link = _owned_path(row.get("infoLinkEvent"), r"/thecomedyclubhouse/[a-z0-9-]+/e-[a-z]+")
        if info.split('/')[2] != event_link.split('/')[2]:
            raise ValueError("event and performance identity disagree")
        booking = _owned_path(row.get("buttonLink"), r"/booking/init/[A-Z]+")
        if row.get("buttonStatus") != "available":
            raise ValueError("unverified performance availability")
        parsed.append((identity, ComedyClubhouseEvent(
            title=html.unescape(title).strip(), start_iso=start,
            show_url="https://www.ticketsource.com" + info,
            ticket_url="https://www.ticketsource.com" + booking,
        )))
    return payload["eof"], parsed
