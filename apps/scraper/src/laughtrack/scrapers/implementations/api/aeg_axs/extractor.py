"""HTML extraction for AEG/Goldenvoice Carbonhouse venue ``/events`` pages.

AEG Presents / Goldenvoice venues (The Warfield, …) run the stock Carbonhouse
venue-site template and ticket every show via AXS. The venue's ``/events`` page
renders each upcoming show as a ``div.entry`` card:

  - name: ``<h3 class="carousel_item_title_small"><a href="<venue>/events/detail/<id>">NAME</a></h3>``
  - date: ``<span class="date"> ... Wed, Jun 24, 2026</span>`` (the leading
    ``<span class="fa fa-calendar-o">`` icon is stripped)
  - time: ``<span class="time"> ... Show 8:00 PM</span>`` (the ``Show`` label
    and icon are stripped; door/no-time cards fall back to a default time)
  - show_page_url: the title anchor's ``/events/detail/<id>`` link
  - ticket url: ``<a ... href="axs.com/events/<id>/...?skin=<venue>">``

The ``axs.com`` detail pages are DataDome-protected, so only the venue page is
parsed. These are pure functions: HTML in, ``AEGAXSEvent`` out.
"""

import re
from html import unescape
from typing import List, Optional

from bs4 import BeautifulSoup

from laughtrack.core.entities.event.aeg_axs import AEGAXSEvent

# Date like "Wed, Jun 24, 2026".
_DATE_RE = re.compile(
    r"(?:Sun|Mon|Tue|Wed|Thu|Fri|Sat),\s+[A-Z][a-z]{2,}\s+\d{1,2},\s+\d{4}"
)
# Time like "8:00 PM" or "8 PM".
_TIME_RE = re.compile(r"\d{1,2}(?::\d{2})?\s*[AP]M", re.IGNORECASE)
# AXS ticket links carry the venue skin marker. The scheme is optional so
# protocol-relative ("//www.axs.com/...") hrefs that sibling Carbonhouse venues
# may emit are still matched, not silently dropped to the detail URL.
_AXS_TICKET_RE = re.compile(r"(?:https?:)?//(?:www\.)?axs\.com/events/[^\"'<>\s]+")


def _clean(text: Optional[str]) -> str:
    return unescape(re.sub(r"\s+", " ", (text or "")).strip())


def extract_events(page_html: str) -> List[AEGAXSEvent]:
    """Parse an AEG/Goldenvoice Carbonhouse ``/events`` page into AEGAXSEvents.

    Cards missing a name, a parseable date, or a detail/ticket URL are skipped.
    """
    soup = BeautifulSoup(page_html or "", "html.parser")
    events: List[AEGAXSEvent] = []

    for card in soup.select("div.entry"):
        title_el = card.select_one("h3.carousel_item_title_small a") or card.select_one(
            "h3.carousel_item_title_small"
        )
        if not title_el:
            continue
        title = _clean(title_el.get_text())
        if not title:
            continue

        date_el = card.select_one("span.date")
        if not date_el:
            continue
        date_m = _DATE_RE.search(_clean(date_el.get_text()))
        if not date_m:
            continue
        date_str = date_m.group(0)

        time_str = None
        time_el = card.select_one("span.time")
        if time_el:
            time_m = _TIME_RE.search(_clean(time_el.get_text()))
            if time_m:
                time_str = time_m.group(0).upper()

        # show_page_url: the venue's own detail page (drives traffic to venue).
        show_page_url = ""
        href = title_el.get("href") if title_el.name == "a" else None
        if href and "/events/detail/" in href:
            show_page_url = href.strip()
        if not show_page_url:
            detail = card.find("a", href=re.compile(r"/events/detail/\d+"))
            if detail:
                show_page_url = detail["href"].strip()

        ticket_url = None
        tix = card.find("a", href=_AXS_TICKET_RE)
        if tix:
            ticket_url = tix["href"].strip()

        if not show_page_url:
            show_page_url = ticket_url or ""
        if not show_page_url:
            continue

        events.append(
            AEGAXSEvent(
                title=title,
                date_str=date_str,
                show_page_url=show_page_url,
                time_str=time_str,
                ticket_url=ticket_url,
            )
        )
    return events
