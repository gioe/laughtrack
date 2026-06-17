"""HTML extraction for NeonCRM (Neon One) eventList.jsp pages.

Each event renders as ``<div class="neoncrm-event-list-event">`` containing:
  - ``<h2 class="neoncrm-event-name"><a href="...event.jsp?event={id}">NAME</a></h2>``
  - ``<div class="neoncrm-event-date">MM/DD/YYYY HH:MM PM - MM/DD/YYYY HH:MM PM ET</div>``

The page is static HTML (curl_cffi chrome impersonation suffices). These are pure
functions: HTML + base URL in, ``NeonCRMEvent`` out. The date range's START is
taken as the show datetime.
"""

import re
from html import unescape
from typing import List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from laughtrack.core.entities.event.neoncrm import NeonCRMEvent

# Range START datetime at the front of the neoncrm-event-date text, e.g.
# "07/16/2026 07:00 PM - 07/19/2026 05:00 PM ET" -> "07/16/2026 07:00 PM".
_START_DT_RE = re.compile(r"(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}\s*[AP]M)")


def _clean(text: Optional[str]) -> str:
    return unescape(" ".join((text or "").split()))


def extract_events(html: str, base_url: str) -> List[NeonCRMEvent]:
    """Parse a NeonCRM eventList.jsp page into NeonCRMEvents.

    ``base_url`` resolves the relative ``event.jsp`` hrefs to absolute URLs.
    Rows missing a name, detail link, or parseable start date are skipped.
    """
    soup = BeautifulSoup(html or "", "html.parser")
    events: List[NeonCRMEvent] = []

    for row in soup.select("div.neoncrm-event-list-event"):
        link = row.select_one("h2.neoncrm-event-name a") or row.select_one(".neoncrm-event-name a")
        if not link:
            continue
        title = _clean(link.get_text())
        href = (link.get("href") or "").strip()
        if not title or not href:
            continue
        show_page_url = urljoin(base_url, href)

        date_el = row.select_one(".neoncrm-event-date")
        if not date_el:
            continue
        m = _START_DT_RE.search(_clean(date_el.get_text()))
        if not m:
            continue

        events.append(
            NeonCRMEvent(
                title=title,
                start_date_str=m.group(1),
                show_page_url=show_page_url,
            )
        )
    return events
