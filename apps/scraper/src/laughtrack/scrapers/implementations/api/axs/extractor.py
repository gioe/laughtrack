"""HTML extraction for AXS-skinned venue homepages.

AXS/AEG venue sites render their upcoming-events slider as a series of
``rsCaption`` cards. Each card carries:
  - the show name in ``<h3><a href="<venue>/events/detail/<id>">NAME</a></h3>``
  - the date in a following ``<h4>Tue, Jun 16, 2026</h4>`` (date only — no time)
  - an AXS ticket link ``<a class="tickets" href="axs.com/events/<id>/...?skin=<venue>">``

The ``axs.com`` detail pages are DataDome-protected, so only the homepage is
parsed. These are pure functions: HTML in, ``AXSEvent`` out.
"""

import re
from html import unescape
from typing import List, Optional

from bs4 import BeautifulSoup

from laughtrack.core.entities.event.axs import AXSEvent

# Date like "Tue, Jun 16, 2026".
_DATE_RE = re.compile(
    r"(?:Sun|Mon|Tue|Wed|Thu|Fri|Sat),\s+[A-Z][a-z]{2,}\s+\d{1,2},\s+\d{4}"
)
# AXS ticket links carry the venue skin marker.
_AXS_TICKET_RE = re.compile(r"https?://(?:www\.)?axs\.com/events/[^\"'<>\s]+")


def _clean(text: Optional[str]) -> str:
    return unescape((text or "").strip())


def extract_events(homepage_html: str) -> List[AXSEvent]:
    """Parse an AXS-skinned venue homepage into AXSEvents.

    Cards missing a name or a parseable date are skipped.
    """
    soup = BeautifulSoup(homepage_html or "", "html.parser")
    events: List[AXSEvent] = []

    for caption in soup.select("div.rsCaption"):
        title_el = caption.select_one("h3 a") or caption.select_one("h3")
        if not title_el:
            continue
        title = _clean(title_el.get_text())
        if not title:
            continue

        # The show date is the first <h4> whose text matches the date pattern
        # (skips the <h4 class="event_venue"> room label).
        date_str = ""
        for h4 in caption.select("h4"):
            m = _DATE_RE.search(_clean(h4.get_text()))
            if m:
                date_str = m.group(0)
                break
        if not date_str:
            continue

        # show_page_url: the venue's own detail page (from the title anchor),
        # falling back to any detail link in the card.
        show_page_url = ""
        href = title_el.get("href") if title_el.name == "a" else None
        if href and "/events/detail/" in href:
            show_page_url = href.strip()
        if not show_page_url:
            detail = caption.find("a", href=re.compile(r"/events/detail/\d+"))
            if detail:
                show_page_url = detail["href"].strip()

        ticket_url = None
        tix = caption.find("a", href=_AXS_TICKET_RE)
        if tix:
            ticket_url = tix["href"].strip()

        # Fall back to the ticket URL when the venue detail link is absent.
        if not show_page_url:
            show_page_url = ticket_url or ""
        if not show_page_url:
            continue

        events.append(
            AXSEvent(
                title=title,
                date_str=date_str,
                show_page_url=show_page_url,
                ticket_url=ticket_url,
            )
        )
    return events
