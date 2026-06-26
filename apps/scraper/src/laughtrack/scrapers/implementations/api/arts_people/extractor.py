"""HTML extraction for Arts-People (Neon One) ticketing pages.

Two phases, both static HTML (curl_cffi chrome impersonation suffices):

1. The ticketing list page
   ``index.php?ticketing={shortName}`` renders each current production as a row
   in ``<table class="htable_front_page">`` carrying a title ``<h1>`` and a
   "Buy tickets" link ``<a href="/?show={id}">``. ``extract_show_links`` returns
   one ``(title, detail_url)`` per row.

2. The per-show page ``index.php?show={id}`` renders bookable performances inside
   ``<table id="TBLperformances">`` as anchor links whose text is the performance
   date, e.g. ``Sat, Jul 11th, 2026 at 7:30 pm``. ``extract_performances`` reads
   the production title from the ``#show_text`` heading and returns one
   ``ArtsPeopleEvent`` per dated performance link.

These are pure functions: HTML + base URL in, structured data out.
"""

import re
from html import unescape
from typing import List, Tuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from laughtrack.core.entities.event.arts_people import ArtsPeopleEvent

# A performance anchor's text looks like "Sat, Jul 11th, 2026 at 7:30 pm".
_PERFORMANCE_TEXT_RE = re.compile(
    r"[A-Za-z]{3,}\s+\d{1,2}(?:st|nd|rd|th)?,\s*\d{4}\s+at\s+\d{1,2}:\d{2}\s*[APap][Mm]"
)
# Buy/detail links carry the show id, e.g. "/?show=39668" or "index.php?show=39668".
_SHOW_HREF_RE = re.compile(r"[?&]show=\d+")


def _clean(text: str) -> str:
    return unescape(" ".join((text or "").split()))


def extract_show_links(html: str, base_url: str) -> List[Tuple[str, str]]:
    """Parse the ticketing list page into ``(title, detail_url)`` pairs.

    ``base_url`` resolves the relative ``/?show={id}`` hrefs to absolute URLs.
    Rows without a title or a show link are skipped, and duplicate detail URLs
    are de-duplicated (some pages repeat a buy link in multiple cells).
    """
    soup = BeautifulSoup(html or "", "html.parser")
    seen: set = set()
    pairs: List[Tuple[str, str]] = []

    table = soup.select_one("table.htable_front_page")
    scope = table if table is not None else soup

    for link in scope.find_all("a", href=_SHOW_HREF_RE):
        href = (link.get("href") or "").strip()
        if not href:
            continue
        detail_url = urljoin(base_url, href)
        if detail_url in seen:
            continue

        # The production title is the row's <h1>; walk up to the enclosing row.
        row = link.find_parent("tr")
        title = ""
        if row is not None:
            heading = row.find("h1")
            if heading is not None:
                title = _clean(heading.get_text())
        if not title:
            continue

        seen.add(detail_url)
        pairs.append((title, detail_url))

    return pairs


def extract_performances(html: str, show_page_url: str) -> List[ArtsPeopleEvent]:
    """Parse a per-show page into one ArtsPeopleEvent per dated performance.

    The production title comes from the ``#show_text`` heading; the performance
    dates come from the anchor text inside ``#TBLperformances``. ``show_page_url``
    is carried verbatim as the stable booking URL for every performance.
    """
    soup = BeautifulSoup(html or "", "html.parser")

    title = ""
    show_text = soup.find(id="show_text")
    if show_text is not None:
        heading = show_text.find("h1")
        if heading is not None:
            title = _clean(heading.get_text())
    if not title:
        heading = soup.find("h1")
        title = _clean(heading.get_text()) if heading is not None else ""
    if not title:
        return []

    perf_table = soup.find(id="TBLperformances")
    if perf_table is None:
        return []

    events: List[ArtsPeopleEvent] = []
    seen_dates: set = set()
    for link in perf_table.find_all("a"):
        text = _clean(link.get_text())
        if not _PERFORMANCE_TEXT_RE.search(text):
            continue
        if text in seen_dates:
            continue
        seen_dates.add(text)
        events.append(
            ArtsPeopleEvent(title=title, date_str=text, show_page_url=show_page_url)
        )
    return events
