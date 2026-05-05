"""Extraction helpers for Palm Beach Improv's Kravis calendar feed."""

import html
import json
import re
from typing import Any, Iterable, List

from bs4 import BeautifulSoup

from laughtrack.core.entities.event.palm_beach_improv import PalmBeachImprovEvent


_PRE_RE = re.compile(r"<pre[^>]*>(.*?)</pre>", re.IGNORECASE | re.DOTALL)
_PALM_BEACH_IMPROV_RE = re.compile(r"palm\s+beach\s+improv", re.IGNORECASE)
_COMEDY_HINT_RE = re.compile(
    r"\b(comedy|comedian|stand[-\s]?up|improv|laugh)\b",
    re.IGNORECASE,
)


class PalmBeachImprovExtractor:
    """Parse Kravis AJAX calendar responses and detail pages."""

    @staticmethod
    def parse_ajax_response(raw: str) -> list[dict[str, Any]]:
        """Return performance dictionaries from a Kravis AJAX response."""
        if not raw:
            return []

        payload = raw.strip()
        match = _PRE_RE.search(payload)
        if match:
            payload = html.unescape(match.group(1)).strip()

        try:
            decoded = json.loads(payload)
        except json.JSONDecodeError:
            return []

        performances = decoded.get("data", {}).get("performances", [])
        if isinstance(performances, dict):
            performances = list(performances.values())
        return [p for p in performances if isinstance(p, dict)]

    @staticmethod
    def detail_page_is_improv(html_text: str) -> bool:
        """Return whether a detail page belongs to Palm Beach Improv."""
        if not html_text:
            return False
        soup = BeautifulSoup(html_text, "html.parser")
        content = (
            soup.select_one("main")
            or soup.select_one(".entry-content")
            or soup.select_one("article")
        )
        if content is None:
            return False
        text = content.get_text(" ", strip=True)
        return bool(_PALM_BEACH_IMPROV_RE.search(text))

    @staticmethod
    def has_comedy_hint(performance: dict[str, Any]) -> bool:
        """Cheap pre-filter for likely comedy performances."""
        blob = json.dumps(performance, default=str)
        return bool(_COMEDY_HINT_RE.search(blob))

    @staticmethod
    def looks_like_improv_candidate(performance: dict[str, Any]) -> bool:
        """Cheap pre-filter for performances worth a detail-page fetch.

        Returns True when the AJAX metadata carries a comedy keyword OR the
        location names the Kravis Improv room (Helen K. Persson Hall). The
        room check covers touring comedians whose blob contains nothing but
        a name (e.g. "KEVIN NEALON" → "/events/kevin-nealon/") — a real
        false-negative for `has_comedy_hint` alone, since "Persson" is the
        only stable Improv-series signal in their AJAX entries.
        """
        if PalmBeachImprovExtractor.has_comedy_hint(performance):
            return True
        location = str(performance.get("location") or "")
        return "persson" in location.lower()

    @staticmethod
    def events_from_performances(
        performances: Iterable[dict[str, Any]],
    ) -> List[PalmBeachImprovEvent]:
        """Expand Kravis performances into one event per listed date."""
        events: List[PalmBeachImprovEvent] = []
        for performance in performances:
            title = BeautifulSoup(
                html.unescape(str(performance.get("title") or "")),
                "html.parser",
            ).get_text(" ", strip=True)
            event_url = str(performance.get("link") or "").strip()
            location = BeautifulSoup(
                html.unescape(str(performance.get("location") or "")),
                "html.parser",
            ).get_text(" ", strip=True)
            thumbnail = str(performance.get("thumbnail") or "").strip()

            if not title or not event_url:
                continue

            for date_info in performance.get("dates") or []:
                if not isinstance(date_info, dict):
                    continue
                date_str = str(date_info.get("date") or "").strip()
                if not date_str:
                    continue
                events.append(
                    PalmBeachImprovEvent(
                        title=title,
                        date_str=date_str,
                        event_url=event_url,
                        location=location,
                        thumbnail=thumbnail,
                    )
                )
        return events
