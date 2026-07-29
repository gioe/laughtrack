"""Data model for a Wix/Velo _functions/shows response item."""

from dataclasses import dataclass
from datetime import datetime
from html import unescape
import re
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


_LINEUP_LABEL_RE = re.compile(r"^\s*Featuring\b\s*:?\s*(?P<body>.+?)\s*$", re.IGNORECASE)
_LINEUP_MORE_SUFFIX_RE = re.compile(r"\s*,?\s*(?:&|and)\s+More!?\s*$", re.IGNORECASE)
_LINEUP_ENTRY_RE = re.compile(r"(?P<name>[^(),]+?)\s*(?:\([^()]+\))?")


@dataclass
class WixFunctionsShowEvent(ShowConvertible):
    """A single show from a custom Wix/Velo _functions/shows endpoint."""

    title: str
    start: datetime
    ticket_url: str
    price_from: Optional[float] = None
    lineup_text: Optional[str] = None

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        """Convert the endpoint event to a Show domain object."""
        if self.start is None:
            return None

        show_page_url = url or self.ticket_url
        tickets = []
        if self.ticket_url:
            ticket = ShowFactoryUtils.create_fallback_ticket(self.ticket_url)
            ticket.price = self.price_from
            tickets.append(ticket)

        lineup = ShowFactoryUtils.create_lineup_from_performers(
            self._parse_lineup_names(self.lineup_text)
        )

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title or "Comedy Show",
            club=club,
            date=self.start,
            show_page_url=show_page_url,
            lineup=lineup,
            tickets=tickets,
            description=self.lineup_text,
            room=None,
            supplied_tags=["event"],
            enhanced=enhanced,
        )

    @staticmethod
    def _parse_lineup_names(lineup_text: Optional[str]) -> List[str]:
        """Parse only explicitly labeled, structurally valid performer lists."""
        if not isinstance(lineup_text, str):
            return []

        label_match = _LINEUP_LABEL_RE.fullmatch(unescape(lineup_text))
        if label_match is None:
            return []

        body = _LINEUP_MORE_SUFFIX_RE.sub("", label_match.group("body"), count=1).strip()
        if not body:
            return []

        entries = [entry.strip() for entry in body.split(",")]
        if not entries or any(not entry for entry in entries):
            return []

        names: List[str] = []
        seen_names: set[str] = set()
        for entry in entries:
            entry_match = _LINEUP_ENTRY_RE.fullmatch(entry)
            if entry_match is None:
                return []

            name = " ".join(entry_match.group("name").split()).strip()
            normalized_name = name.casefold()
            if not normalized_name:
                return []
            if normalized_name in seen_names:
                continue

            seen_names.add(normalized_name)
            names.append(name)

        return names
