"""Extractor for the Grisly Pear calendar listing."""

from __future__ import annotations

import re
from datetime import date
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .data import GrislyPearEvent

_DATED_EVENT_RE = re.compile(r"(?P<date>\d{4}-\d{2}-\d{2})(?P<time>\d{6})$")


class GrislyPearExtractor:
    """Extract future event anchors from the Grisly Pear calendar."""

    @staticmethod
    def extract_events(
        html: str,
        *,
        base_url: str,
        club_name: str,
        today: date | None = None,
    ) -> list[GrislyPearEvent]:
        if today is None:
            today = date.today()

        soup = BeautifulSoup(html or "", "html.parser")
        events: list[GrislyPearEvent] = []
        seen_urls: set[str] = set()

        for anchor in soup.find_all("a", href=True):
            href = str(anchor["href"])
            if "/events/" not in href:
                continue

            url = urljoin(base_url, href)
            if url in seen_urls:
                continue

            parsed = GrislyPearExtractor._parse_dated_event_url(url)
            if parsed is None:
                continue
            event_date, event_time = parsed
            if event_date < today:
                continue

            name = GrislyPearExtractor._extract_title(anchor)
            if not name or not GrislyPearExtractor._belongs_to_club(name, club_name):
                continue

            seen_urls.add(url)
            events.append(
                GrislyPearEvent(
                    name=name,
                    url=url,
                    date=event_date.isoformat(),
                    time=event_time,
                )
            )

        return events

    @staticmethod
    def _parse_dated_event_url(url: str) -> tuple[date, str] | None:
        slug = url.rstrip("/").rsplit("/", 1)[-1]
        match = _DATED_EVENT_RE.search(slug)
        if not match:
            return None
        try:
            return date.fromisoformat(match.group("date")), match.group("time")
        except ValueError:
            return None

    @staticmethod
    def _extract_title(anchor) -> str:
        for value in (
            anchor.get("aria-label"),
            anchor.get("title"),
            anchor.get_text(" ", strip=True),
        ):
            title = GrislyPearExtractor._clean_title(value)
            if title:
                return title

        image = anchor.find("img")
        return GrislyPearExtractor._clean_title(image.get("alt") if image else None)

    @staticmethod
    def _clean_title(value: object) -> str:
        if not isinstance(value, str):
            return ""
        title = " ".join(value.split())
        if title.lower().startswith("view "):
            title = title[5:].strip()
        return title

    @staticmethod
    def _belongs_to_club(title: str, club_name: str) -> bool:
        title_lower = title.lower()
        club_lower = club_name.lower()
        if "midtown" in club_lower:
            return "midtown" in title_lower
        if "greenwich" in club_lower:
            return "greenwich village" in title_lower or "grisly pear classic" in title_lower
        return True

