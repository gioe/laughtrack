"""HTML extraction for Pabst Theater Group venue pages.

Each pabsttheater.org venue page renders its upcoming shows as a series of
``div.eventItem`` cards. Each card carries:
  - the show name in the ``title`` attribute of the info/ticket links
    (``More Info for <NAME>`` / ``Buy Tickets for <NAME>``)
  - an AXS ticket link ``<a href="axs.com/events/<id>/<slug>-tickets?skin=pabst">``
  - the venue's own detail URL (the "More Info" link)
  - a dated thumbnail ``<img src=".../assets/img/YYYY.MM.DD-<...>.png">`` — the
    date lives in the filename (no separate date text node, no show time).

The ``axs.com`` detail pages are DataDome-protected, so only the venue page is
parsed. These are pure functions: HTML in, ``PabstAXSEvent`` out.
"""

import re
from html import unescape
from typing import List, Optional

from bs4 import BeautifulSoup

from laughtrack.core.entities.event.pabst_axs import PabstAXSEvent

# Date embedded in the thumbnail filename, e.g. ".../2026.10.16-R-Ben-Schwartz...".
_DATE_IMG_RE = re.compile(r"/(\d{4})\.(\d{2})\.(\d{2})-")
# AXS ticket links carry the venue skin marker.
_AXS_TICKET_RE = re.compile(r"https?://(?:www\.)?axs\.com/events/[^\"'<>\s]+")
# "Buy Tickets for X" / "More Info for X" title-attribute prefixes.
_TITLE_PREFIX_RE = re.compile(r"^\s*(?:Buy Tickets for|More Info for)\s+", re.IGNORECASE)


def _clean(text: Optional[str]) -> str:
    return unescape((text or "").strip())


def _title_from_link(link) -> str:
    """Pull a clean show name from a link's ``title`` attribute."""
    if not link:
        return ""
    return _clean(_TITLE_PREFIX_RE.sub("", link.get("title") or ""))


def _date_from_img(card) -> str:
    """Return the ISO ``YYYY-MM-DD`` date parsed from the card's thumbnail src."""
    img = card.find("img", src=_DATE_IMG_RE)
    if not img:
        return ""
    m = _DATE_IMG_RE.search(img.get("src") or "")
    if not m:
        return ""
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"


def extract_events(page_html: str) -> List[PabstAXSEvent]:
    """Parse a Pabst Theater Group venue page into PabstAXSEvents.

    Cards missing a name or a parseable thumbnail date are skipped.
    """
    soup = BeautifulSoup(page_html or "", "html.parser")
    events: List[PabstAXSEvent] = []

    for card in soup.select("div.eventItem"):
        info = card.find("a", title=re.compile(r"^\s*More Info for", re.IGNORECASE))
        buy = card.find("a", href=_AXS_TICKET_RE)

        # Title preference: the "More Info" link, falling back to the AXS link.
        title = _title_from_link(info) or _title_from_link(buy)
        if not title:
            continue

        date_str = _date_from_img(card)
        if not date_str:
            continue

        # show_page_url: the venue's own detail page (drives traffic to venue),
        # falling back to the AXS ticket link.
        show_page_url = ""
        if info and info.get("href"):
            show_page_url = info["href"].strip()

        ticket_url = buy["href"].strip() if buy else None

        if not show_page_url:
            show_page_url = ticket_url or ""
        if not show_page_url:
            continue

        events.append(
            PabstAXSEvent(
                title=title,
                date_str=date_str,
                show_page_url=show_page_url,
                ticket_url=ticket_url,
            )
        )
    return events
