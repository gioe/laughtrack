"""Extractor for Go Bananas Comedy Club's custom WordPress show markup."""

import re
from datetime import date
from typing import List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from laughtrack.core.entities.event.go_bananas import GoBananasEvent


_SHOWTIME_DATE_RE = re.compile(r"\(([A-Za-z]+)\s+(\d{1,2})\)")
_SHOWTIME_RE = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*([ap]\.?m\.?)", re.IGNORECASE)
_PRICE_RE = re.compile(r"\$([0-9]+(?:\.[0-9]{1,2})?)")
_LOCATION_RE = re.compile(r"location\.href\s*=\s*['\"]([^'\"]+)['\"]", re.IGNORECASE)


class GoBananasExtractor:
    """Parse visible Go Bananas show articles into ticketed showtime events."""

    @staticmethod
    def extract_events(
        html: str,
        *,
        source_url: str,
        today: Optional[date] = None,
    ) -> List[GoBananasEvent]:
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        current_date = today or date.today()
        events: List[GoBananasEvent] = []
        for article in soup.select("article.category-shows"):
            title = GoBananasExtractor._extract_title(article)
            show_url = GoBananasExtractor._extract_show_url(article, source_url)
            if not title or not show_url:
                continue

            for row in article.select("tr.goba-showtimes__row"):
                event = GoBananasExtractor._extract_row_event(
                    row,
                    title=title,
                    show_url=show_url,
                    source_url=source_url,
                    today=current_date,
                )
                if event:
                    events.append(event)

        return sorted(events, key=lambda event: (event.date, event.time, event.title, event.ticket_url))

    @staticmethod
    def _extract_row_event(
        row: Tag,
        *,
        title: str,
        show_url: str,
        source_url: str,
        today: date,
    ) -> Optional[GoBananasEvent]:
        button = row.select_one("button.goba-reservation-button")
        if not button:
            return None

        showtime_el = row.select_one(".goba-showtimes__showtime")
        showtime_text = showtime_el.get_text(" ", strip=True) if showtime_el else ""
        parsed_date = GoBananasExtractor._parse_showtime_date(showtime_text, today)
        parsed_time = GoBananasExtractor._parse_showtime_time(showtime_text)
        if not parsed_date or not parsed_time:
            return None
        if parsed_date < today:
            return None

        ticket_url = GoBananasExtractor._extract_ticket_url(button, source_url, show_url)
        if not ticket_url:
            return None

        return GoBananasEvent(
            title=title,
            date=parsed_date.isoformat(),
            time=parsed_time,
            source_url=show_url,
            ticket_url=ticket_url,
            price=GoBananasExtractor._extract_price(row),
        )

    @staticmethod
    def _extract_title(article: Tag) -> str:
        title_el = article.select_one(".goba-title-card__title td")
        return title_el.get_text(" ", strip=True) if title_el else ""

    @staticmethod
    def _extract_show_url(article: Tag, source_url: str) -> str:
        link = article.select_one(".goba-title-card a[href]")
        href = link.get("href") if link else ""
        return urljoin(source_url.rstrip("/") + "/", str(href)) if href else ""

    @staticmethod
    def _parse_showtime_date(showtime_text: str, today: date) -> Optional[date]:
        match = _SHOWTIME_DATE_RE.search(showtime_text)
        if not match:
            return None
        try:
            month_name = match.group(1)
            day = int(match.group(2))
            parsed = datetime_from_month_day(month_name, day, today.year)
            if parsed < today:
                parsed = parsed.replace(year=today.year + 1)
            return parsed
        except Exception:
            return None

    @staticmethod
    def _parse_showtime_time(showtime_text: str) -> Optional[str]:
        match = _SHOWTIME_RE.search(showtime_text)
        if not match:
            return None
        hour = int(match.group(1))
        minute = int(match.group(2) or "0")
        meridiem = match.group(3).replace(".", "").upper()
        return f"{hour}:{minute:02d} {meridiem}"

    @staticmethod
    def _extract_price(row: Tag) -> float:
        price_el = row.select_one(".goba-showtimes__price")
        price_text = price_el.get_text(" ", strip=True) if price_el else row.get_text(" ", strip=True)
        match = _PRICE_RE.search(price_text)
        return float(match.group(1)) if match else 0.0

    @staticmethod
    def _extract_ticket_url(button: Tag, source_url: str, show_url: str) -> str:
        onclick = str(button.get("onclick") or "")
        match = _LOCATION_RE.search(onclick)
        if not match:
            return ""
        href = match.group(1).replace("&amp;", "&")
        if href.startswith("http://") or href.startswith("https://"):
            return href

        if href.startswith("make-reservations") and "/main/show/" in show_url:
            base = show_url.split("/main/show/", 1)[0] + "/main/"
            return urljoin(base, href)

        return urljoin(source_url.rstrip("/") + "/", href)


def datetime_from_month_day(month_name: str, day: int, year: int) -> date:
    from datetime import datetime

    parsed = datetime.strptime(f"{month_name} {day} {year}", "%B %d %Y")
    return parsed.date()
