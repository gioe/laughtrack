"""
HTML extractor for classic SeatEngine venue pages.

Classic SeatEngine (cdn.seatengine.com) renders events server-side.
Each event-list-item block has one of two layouts:

Layout 1 — multiple show times grouped under one event:
  <h3 class="el-header"><a href="/events/128084">EVENT_NAME</a></h3>
  <div class="event-times-group">
    <h6 class="event-date align-right">Sun, Mar 22, 2026</h6>
    <a class="event-btn-inline" href="/shows/363997"> 3:00 PM</a>   <!-- available -->
    <span class="event-btn-inline inactive"> 8:00 PM</span>         <!-- soldout -->
  </div>

Layout 2 — single show with a buy-tickets button:
  <h3 class="el-header"><a href="/events/130328">EVENT_NAME</a></h3>
  <h6 class="event-date">Thu Mar 26 2026,  7:30 PM</h6>
  <a class="btn btn-primary" href="/shows/356313">Buy Tickets</a>

Each extracted show is a dict with keys:
  name, date_str, show_url, sold_out
"""

import json
import re
from typing import List, Optional

from bs4 import BeautifulSoup, Tag

from laughtrack.foundation.models.types import JSONDict


class SeatEngineClassicExtractor:

    @staticmethod
    def extract_shows(html: str, base_url: str) -> List[JSONDict]:
        """
        Parse HTML and return a flat list of show dicts.

        Tries HTML extraction first (event-list-item divs).
        Falls back to JSON-LD extraction for *.seatengine.com/calendar pages
        that embed events only in a JSON-LD Place schema.

        Args:
            html: Raw HTML of the events page.
            base_url: Scheme + host (e.g. "https://newbrunswick.stressfactory.com").
        """
        soup = BeautifulSoup(html, "html.parser")
        items = soup.find_all("div", class_=re.compile(r"\bevent-list-item\b"))
        shows: List[JSONDict] = []

        for item in items:
            assert isinstance(item, Tag)
            event_name = SeatEngineClassicExtractor._event_name(item)
            if not event_name:
                continue

            times_group = item.find("div", class_="event-times-group")
            if times_group:
                shows.extend(
                    SeatEngineClassicExtractor._extract_layout1(
                        item, times_group, event_name, base_url
                    )
                )
            else:
                show = SeatEngineClassicExtractor._extract_layout2(
                    item, event_name, base_url
                )
                if show:
                    shows.append(show)

        if not shows:
            shows = SeatEngineClassicExtractor._extract_json_ld(soup)

        return shows

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _extract_json_ld(soup: BeautifulSoup) -> List[JSONDict]:
        """
        Extract shows from a JSON-LD Place schema embedded in the page.

        Used by *.seatengine.com/calendar pages which do not render
        event-list-item divs but do embed events in a JSON-LD script.
        """
        shows: List[JSONDict] = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
            except (json.JSONDecodeError, TypeError):
                continue
            if data.get("@type") != "Place":
                continue
            for event in data.get("Events", []):
                if event.get("@type") != "Event":
                    continue
                name = event.get("name") or ""
                date_str = event.get("startDate") or ""
                url = event.get("url") or None
                if name and date_str:
                    shows.append(
                        {
                            "name": name,
                            "date_str": date_str,
                            "show_url": url,
                            "sold_out": False,
                        }
                    )
            if shows:
                break
        return shows

    @staticmethod
    def _event_name(item: Tag) -> Optional[str]:
        header = item.find("h3", class_="el-header")
        if not header:
            return None
        a = header.find("a")
        if a:
            return a.get_text(strip=True) or None
        return header.get_text(strip=True) or None

    @staticmethod
    def _extract_layout1(
        item: Tag, times_group: Tag, event_name: str, base_url: str
    ) -> List[JSONDict]:
        """Multiple show-times grouped under one event date."""
        date_el = times_group.find("h6", class_=re.compile(r"\bevent-date\b"))
        date_str = date_el.get_text(strip=True) if date_el else None

        shows: List[JSONDict] = []

        # Available shows — <a class="event-btn-inline" href="/shows/...">
        for btn in times_group.find_all("a", class_="event-btn-inline"):
            assert isinstance(btn, Tag)
            href = btn.get("href", "")
            time_text = btn.get_text(strip=True)
            shows.append(
                {
                    "name": event_name,
                    "date_str": f"{date_str} {time_text}" if date_str else time_text,
                    "show_url": f"{base_url}{href}" if href.startswith("/") else href,
                    "sold_out": False,
                }
            )

        # Soldout shows — <span class="event-btns"> containing event-btn-soldout
        for btns_span in times_group.find_all("span", class_="event-btns"):
            assert isinstance(btns_span, Tag)
            if not btns_span.find("span", class_="event-btn-soldout"):
                continue
            inactive = btns_span.find("span", class_=re.compile(r"\bevent-btn-inline\b"))
            if not inactive:
                continue
            time_text = inactive.get_text(strip=True)
            shows.append(
                {
                    "name": event_name,
                    "date_str": f"{date_str} {time_text}" if date_str else time_text,
                    "show_url": None,
                    "sold_out": True,
                }
            )

        return shows

    @staticmethod
    def _extract_layout2(
        item: Tag, event_name: str, base_url: str
    ) -> Optional[JSONDict]:
        """Single show with date+time in one element and a buy-tickets button."""
        # "event-date" without "align-right" — contains full datetime
        date_el = item.find("h6", class_=re.compile(r"\bevent-date\b"))
        if not date_el:
            return None
        date_str = date_el.get_text(strip=True)

        btn = item.find("a", class_=re.compile(r"\bbtn-primary\b"))
        if not btn:
            return None
        assert isinstance(btn, Tag)
        href = btn.get("href", "")
        return {
            "name": event_name,
            "date_str": date_str,
            "show_url": f"{base_url}{href}" if href.startswith("/") else href,
            "sold_out": False,
        }
