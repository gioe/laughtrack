"""HTML extraction for a Multipass venue box-office listing page."""

from datetime import datetime, timedelta
from typing import List, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from laughtrack.core.entities.event.multipass import (
    MultipassEvent,
    parse_multipass_datetime,
)
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.number import parse_price_text

# A Multipass venue page renders ALL events (past + future) in static HTML and
# relies on a client-side "Show Past Events" toggle to hide past ones. The
# framework does NOT drop past-dated shows, so the extractor filters them here.
# A 1-day grace absorbs venue-vs-system timezone skew on same-day shows.
_PAST_GRACE = timedelta(days=1)


def _origin(url: str) -> str:
    """Return the scheme://host origin for resolving relative card hrefs."""
    parsed = urlparse(url)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return url.rstrip("/")


class MultipassExtractor:
    """
    Parses a Multipass venue listing page (e.g. ``denvercomedy.multipass.com``).

    Each upcoming show is a ``div.eventCard2026`` card with:
    - ``div.title > a``                  — show title + relative event path
    - ``div.eventline.datetime``         — "Fri Jul 3 • 8 PM" (year omitted)
    - ``span.eventPrice``                — "$18.06" (optional)
    - ``a.actionButton[href]``           — relative event/ticket path
    """

    @staticmethod
    def extract_events(
        html: str, source_url: str, now: Optional[datetime] = None
    ) -> List[MultipassEvent]:
        if not html:
            return []

        now = now or datetime.now()
        cutoff = now - _PAST_GRACE
        base = _origin(source_url)
        soup = BeautifulSoup(html, "html.parser")
        events: List[MultipassEvent] = []

        for card in soup.find_all("div", class_="eventCard2026"):
            event = MultipassExtractor._parse_card(card, base, now)
            if event is None:
                continue
            try:
                start = datetime.strptime(event.start_iso, "%Y-%m-%dT%H:%M")
            except ValueError:
                continue
            if start < cutoff:
                Logger.debug(
                    f"MultipassExtractor: skipping past event '{event.title}' "
                    f"({event.start_iso})"
                )
                continue
            events.append(event)

        return events

    @staticmethod
    def _parse_card(card, base: str, now: Optional[datetime] = None) -> Optional[MultipassEvent]:
        # Title + event path
        title_div = card.find("div", class_="title")
        title_a = title_div.find("a") if title_div else None
        if not title_a:
            Logger.debug("MultipassExtractor: skipping card — no title link")
            return None
        title = title_a.get_text(strip=True)
        href = (title_a.get("href") or "").strip()
        if not href:
            # Fall back to the "Get Tickets" action button href.
            action = card.find("a", class_="actionButton")
            href = (action.get("href") or "").strip() if action else ""
        if not title or not href:
            Logger.debug("MultipassExtractor: skipping card — missing title or href")
            return None
        show_url = urljoin(base + "/", href.lstrip("/"))

        # Date / time (year inferred downstream)
        dt_div = card.find("div", class_="datetime")
        if not dt_div:
            Logger.debug(f"MultipassExtractor: skipping '{title}' — no datetime div")
            return None
        start_iso = parse_multipass_datetime(dt_div.get_text(" ", strip=True), now=now)
        if not start_iso:
            Logger.debug(
                f"MultipassExtractor: skipping '{title}' — unparseable date "
                f"'{dt_div.get_text(' ', strip=True)}'"
            )
            return None

        # Price (optional)
        price = None
        price_span = card.find("span", class_="eventPrice")
        if price_span:
            price = parse_price_text(price_span.get_text(strip=True))

        return MultipassEvent(
            title=title,
            start_iso=start_iso,
            show_url=show_url,
            price=price,
        )
