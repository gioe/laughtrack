"""
HTML extraction for McCurdy's Comedy Theatre pages.

Two page types are handled:

- Listing page (/shows/): grid of show cards, each linking to a detail page
  via onclick="location.href='/shows/show.cfm?shoID=<id>'" with the show
  title in an ``<h2 class="summary">`` tag.

- Detail page (/shows/show.cfm?shoID=<id>): show title in ``<h1 class="summary">``,
  performance dates under ``<div class="upcoming-shows-sidebar">`` as ``<li>``
  items, each containing a ``<p>`` with "Day, Month DD at H:MM PM" and an
  ``<a>`` linking to ``/shows/buy.cfm?timTicketID=<id>`` (which 302-redirects
  to ``https://www.etix.com/ticket/p/<id>``).
"""

import re
from typing import List

from laughtrack.core.entities.event.mccurdys_comedy_theatre import McCurdysEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.number import parse_price_text
from laughtrack.utilities.infrastructure.html.scraper import HtmlScraper

_ETIX_TICKET_BASE = "https://www.etix.com/ticket/p/"

# ---------------------------------------------------------------------------
# Listing-page patterns
# ---------------------------------------------------------------------------

_SHOW_LINK_RE = re.compile(
    r"onclick=\"location\.href='(/shows/show\.cfm\?shoID=\d+)';\"",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Detail-page patterns
# ---------------------------------------------------------------------------

_DATE_RE = re.compile(
    r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)," r"\s+\w+\s+\d{1,2}\s+at\s+\d{1,2}:\d{2}\s+[AP]M",
    re.IGNORECASE,
)
_BUY_RE = re.compile(r"(?:^|/)buy\.cfm\?timTicketID=(\d+)(?:&|$)", re.I)
_SINGLE_PRICE_RE = re.compile(r"Tickets\s+(?:USD\s*)?\$\s*\d+(?:,\d{3})*(?:\.\d{1,2})?", re.I)


def _advertised_price(elements):
    texts = list(
        dict.fromkeys(
            el.get_text(" ", strip=True)
            for el in elements
            if re.match(r"^Tickets\b", el.get_text(" ", strip=True), re.I)
        )
    )
    text = " / ".join(texts)
    # Responsive copies must agree. Ranges, tiers and fees retain their wording
    # without being collapsed into an invented per-performance minimum.
    if len(texts) != 1 or not _SINGLE_PRICE_RE.fullmatch(text):
        return None, text
    value = parse_price_text(text, detect_free=False, dollar_only=True)
    return (value if value is not None and 0 < value <= 1000000 else None), text


class McCurdysExtractor:
    """Parses HTML from McCurdy's Comedy Theatre pages."""

    @staticmethod
    def extract_detail_page_urls(html: str, base_url: str) -> List[str]:
        """Extract unique show detail page URLs from the listing page."""
        if not html:
            return []
        paths = list(dict.fromkeys(_SHOW_LINK_RE.findall(html)))
        base = base_url.rstrip("/")
        # Ensure base is the site root, not the /shows/ subpath
        if "/shows" in base:
            base = base.rsplit("/shows", 1)[0]
        return [f"{base}{path}" for path in paths]

    @staticmethod
    def extract_events(html: str) -> List[McCurdysEvent]:
        """Extract all performances from a show detail page.

        Returns one McCurdysEvent per performance date/time listed on the page.
        A single show (e.g. "Jamie Lissow") typically has 3–5 performances
        across a weekend run.
        """
        if not html:
            return []

        soup = HtmlScraper._parse_html(html)
        title_el = soup.select_one("h1.summary")
        if title_el is None:
            Logger.debug("McCurdysExtractor: no <h1 class='summary'> found")
            return []
        title = title_el.get_text(" ", strip=True)
        if not title:
            return []

        container = title_el.find_parent(class_="vevent")
        scope = container if container is not None else soup
        rows = [
            row for row in scope.select(".upcoming-shows-sidebar li") if row.find_parent(class_="vevent") is container
        ]
        page_price = (None, "")
        if container is not None and len(rows) == 1:
            page_price = _advertised_price(
                el
                for el in container.select(".col-md-3.hidden-xs.pull-right.text-right > em, .col-md-3.visible-xs > em")
                if el.find_parent(class_="vevent") is container
            )

        events: List[McCurdysEvent] = []
        for row in rows:
            dates = [
                p.get_text(" ", strip=True) for p in row.select("p") if _DATE_RE.fullmatch(p.get_text(" ", strip=True))
            ]
            links = [m.group(1) for a in row.select("a[href]") if (m := _BUY_RE.search(str(a.get("href"))))]
            if len(dates) != 1 or len(set(links)) != 1:
                continue
            date_str, ticket_id = dates[0], links[0]
            row_price = _advertised_price(row.select("em"))
            price, price_text = row_price if row_price[1] else page_price
            ticket_url = f"{_ETIX_TICKET_BASE}{ticket_id}"
            events.append(
                McCurdysEvent(
                    title=title,
                    date_str=date_str,
                    ticket_url=ticket_url,
                    ticket_price=price,
                    price_text=price_text,
                )
            )

        return events
