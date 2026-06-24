"""Event extraction from a VBO Tickets ``showevents`` listing HTML response."""

import re
from dataclasses import dataclass
from datetime import date
from html import unescape
from typing import Iterable, List, Optional, Set, Union

from laughtrack.core.entities.event.vbo_tickets import _VBO_DATE_RE, VboEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger

# The loadplugin response posts the user session UUID back to the parent frame
# as an unquoted JS object value: ``value: "uuid"``.
_SESSION_RE = re.compile(
    r'value["\s:]+([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})',
    re.IGNORECASE,
)

# Each event in the listing is a wrapper div: <div id="EDID123" class="EventListWrapper ...
_EVENT_BLOCK_RE = re.compile(
    r'<div id="EDID\d+" class="EventListWrapper.*?(?=<div id="EDID\d+" class="EventListWrapper|<div[^>]*id="PastEvents|\Z)',
    re.IGNORECASE | re.DOTALL,
)
_NAME_RE = re.compile(r'data-event-name="([^"]*)"', re.IGNORECASE)
_CATEGORY_RE = re.compile(r'data-event-category="([^"]*)"', re.IGNORECASE)
_EDID_RE = re.compile(r'id="EDID(\d+)"', re.IGNORECASE)
_EID_RE = re.compile(r"event\.asp\?eid=(\d+)", re.IGNORECASE)
_DATE_RE = re.compile(r'class="TextEventDate[^"]*">\s*([^<]+?)\s*</div>', re.IGNORECASE)
_PRICE_RE = re.compile(r'class="EventListPrice">\s*([^<]+?)\s*</div>', re.IGNORECASE)
_PRICE_NUM_RE = re.compile(r"\$\s*([0-9]+(?:\.[0-9]{2})?)")
_DATE_SLIDER_BOX_RE = re.compile(
    r'id="edid(\d+)".*?'
    r'DateMonth[^>]*>([A-Za-z]+)<.*?'
    r'DateDay[^>]*>(\d+)<.*?'
    r'WeekDay">([^<]+)</span>'
    r'.*?WeekDayTime"> - ([^<]+)</span>',
    re.DOTALL,
)

# Free-form date parsing (venues whose admins enter date text by hand rather
# than using VBO's structured per-occurrence rows). A clock time like "7:00pm",
# "8pm", "9:30 PM"; a month/day, optionally with a 4-digit year: "6/19",
# "7/11/2026".
_TIME_RE = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*([ap]m)", re.IGNORECASE)
_DATE_PARTS_RE = re.compile(r"(\d{1,2})/(\d{1,2})(?:/(\d{4}))?")

# Stable per-event landing URL (session token deliberately omitted so the
# persisted show_page_url does not rot when the VBO session expires).
_EVENT_URL = "https://plugin.vbotickets.com/v5.0/event.asp?eid={eid}"

_MONTH_NUMBERS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


@dataclass(frozen=True)
class VboDetailExpansionTarget:
    """Listing row whose dates must come from the per-event VBO date slider."""

    eid: str
    edid: str
    name: str
    date_str: str
    url: str
    price_min: Optional[float] = None
    room: str = ""


def _normalize_category_filter(
    category_filter: Optional[Union[str, Iterable[str]]],
) -> Optional[Set[str]]:
    """Return a lowercased set of allowed categories, or None when unfiltered."""
    if not category_filter:
        return None
    if isinstance(category_filter, str):
        values = [category_filter]
    else:
        values = list(category_filter)
    allowed = {v.strip().lower() for v in values if v and v.strip()}
    return allowed or None


def _strip_tags(html_fragment: str) -> List[str]:
    """Convert an HTML fragment to a list of non-empty, stripped text lines."""
    text = re.sub(r"<script.*?</script>", "", html_fragment, flags=re.S)
    text = re.sub(r"<[^>]+>", "\n", text)
    text = unescape(text)
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def _parse_room(block: str, club_name: str) -> str:
    """Extract the sub-venue/stage from a '<club name> - <room>' line, if any."""
    if not club_name:
        return ""
    needle = f"{club_name} -"
    for ln in _strip_tags(block):
        if needle in ln:
            return ln.split(" - ", 1)[1].strip()
    return ""


def _parse_datetimes(date_line: str, today: date) -> List[str]:
    """Parse a free-form VBO date line into local 'YYYY-MM-DD HH:MM:00' strings.

    Handles single ("Wed 6/17 7:00pm") and recurring ("Fri 9:30pm 6/5, 6/12,
    6/19, ...") listings, emitting one datetime per upcoming date. Past dates
    are dropped; a single bare-year date that has already passed rolls to next
    year (it is next year's show), while past dates inside a recurring list are
    simply skipped.
    """
    if not date_line:
        return []
    tm = _TIME_RE.search(date_line)
    if not tm:
        return []
    hour = int(tm.group(1))
    minute = int(tm.group(2) or 0)
    meridiem = tm.group(3).lower()
    if meridiem == "pm" and hour != 12:
        hour += 12
    if meridiem == "am" and hour == 12:
        hour = 0

    matches = _DATE_PARTS_RE.findall(date_line)
    if not matches:
        return []
    multi = len(matches) > 1

    out: List[str] = []
    for month_s, day_s, year_s in matches:
        month, day = int(month_s), int(day_s)
        year = int(year_s) if year_s else today.year
        try:
            cand = date(year, month, day)
        except ValueError:
            continue
        if cand < today:
            if multi or year_s:
                continue  # past occurrence of a recurring show, or an explicit past year
            try:
                cand = date(year + 1, month, day)  # single bare-year date → next year's show
            except ValueError:
                continue
        out.append(f"{cand.isoformat()} {hour:02d}:{minute:02d}:00")
    return out


def _parse_price(block: str) -> Optional[float]:
    price_m = _PRICE_RE.search(block)
    if not price_m:
        return None
    nums = [float(n) for n in _PRICE_NUM_RE.findall(price_m.group(1))]
    return min(nums) if nums else None


def _slider_start_iso(month_name: str, day: int, time_str: str, today: date) -> Optional[str]:
    month = _MONTH_NUMBERS.get(month_name.strip().lower())
    if month is None:
        return None
    tm = _TIME_RE.search(time_str)
    if not tm:
        return None
    hour = int(tm.group(1))
    minute = int(tm.group(2) or 0)
    meridiem = tm.group(3).lower()
    if meridiem == "pm" and hour != 12:
        hour += 12
    if meridiem == "am" and hour == 12:
        hour = 0

    year = today.year if month >= today.month else today.year + 1
    try:
        cand = date(year, month, day)
    except ValueError:
        return None
    if cand < today:
        try:
            cand = date(year + 1, month, day)
        except ValueError:
            return None
    return f"{cand.isoformat()} {hour:02d}:{minute:02d}:00"


class VboTicketsExtractor:
    """Converts VBO Tickets ListEvents HTML into VboEvent objects."""

    @staticmethod
    def extract_session(loadplugin_html: str) -> Optional[str]:
        """Pull the user-session UUID from a loadplugin response, or None."""
        if not loadplugin_html:
            return None
        m = _SESSION_RE.search(loadplugin_html)
        return m.group(1) if m else None

    @staticmethod
    def extract_events(
        showevents_html: str,
        category_filter: Optional[Union[str, Iterable[str]]] = None,
        club_name: str = "",
        today: Optional[date] = None,
    ) -> List[VboEvent]:
        """Extract VboEvent rows from a ``showevents`` listing response.

        Args:
            showevents_html: the rendered listing HTML.
            category_filter: optional ``data-event-category`` allow-list (string
                or iterable, case-insensitive). When set, only matching events
                are kept — e.g. ``"Live Shows"`` excludes a venue's classes.
            club_name: the venue name, used to extract the sub-venue/stage from
                free-form listings (a "<club name> - <room>" line).
            today: reference date for dropping past occurrences (defaults to
                ``date.today()``); injectable for tests.
        """
        allowed = _normalize_category_filter(category_filter)
        ref_today = today or date.today()
        events: List[VboEvent] = []
        for block in _EVENT_BLOCK_RE.findall(showevents_html or ""):
            try:
                events.extend(
                    VboTicketsExtractor._parse_block(block, allowed, club_name, ref_today)
                )
            except Exception as e:
                Logger.warn(f"VboTicketsExtractor: skipping event due to error: {e}")
        return events

    @staticmethod
    def extract_detail_expansion_targets(
        showevents_html: str,
        category_filter: Optional[Union[str, Iterable[str]]] = None,
        club_name: str = "",
        today: Optional[date] = None,
    ) -> List[VboDetailExpansionTarget]:
        """Find listing rows that need authoritative per-event slider dates."""
        allowed = _normalize_category_filter(category_filter)
        ref_today = today or date.today()
        targets: List[VboDetailExpansionTarget] = []
        for block in _EVENT_BLOCK_RE.findall(showevents_html or ""):
            target = VboTicketsExtractor._parse_detail_expansion_target(
                block, allowed, club_name, ref_today
            )
            if target is not None:
                targets.append(target)
        return targets

    @staticmethod
    def extract_events_from_date_slider(
        slider_html: str,
        target: VboDetailExpansionTarget,
        today: Optional[date] = None,
    ) -> List[VboEvent]:
        """Expand one unresolved listing row using VBO's date-slider HTML."""
        ref_today = today or date.today()
        events: List[VboEvent] = []
        seen: Set[str] = set()
        for match in _DATE_SLIDER_BOX_RE.finditer(slider_html or ""):
            month = match.group(2).strip()
            day = int(match.group(3))
            time_str = match.group(5).strip()
            start_iso = _slider_start_iso(month, day, time_str, ref_today)
            if not start_iso or start_iso in seen:
                continue
            seen.add(start_iso)
            events.append(
                VboEvent(
                    eid=target.eid,
                    name=target.name,
                    date_str=target.date_str,
                    url=target.url,
                    price_min=target.price_min,
                    start_iso=start_iso,
                    room=target.room,
                )
            )
        return events

    @staticmethod
    def _parse_block(
        block: str,
        allowed_categories: Optional[Set[str]],
        club_name: str,
        today: date,
    ) -> List[VboEvent]:
        eid_m = _EID_RE.search(block)
        name_m = _NAME_RE.search(block)
        date_m = _DATE_RE.search(block)
        # An event row without an eid or a date is not a bookable show.
        if not eid_m or not date_m:
            return []

        # Optional category allow-list (e.g. keep only "Live Shows").
        if allowed_categories is not None:
            cat_m = _CATEGORY_RE.search(block)
            category = (cat_m.group(1).strip().lower() if cat_m else "")
            if category not in allowed_categories:
                return []

        price_min = _parse_price(block)

        eid = eid_m.group(1)
        name = unescape((name_m.group(1) if name_m else "").strip())
        date_str = unescape(date_m.group(1).strip())
        url = _EVENT_URL.format(eid=eid)

        # Structured per-occurrence row ("Tue, 6/16/2026 @ 7:00 PM"): one event,
        # date parsed downstream in VboEvent.to_show() (unchanged path).
        if _VBO_DATE_RE.search(date_str):
            return [
                VboEvent(
                    eid=eid,
                    name=name,
                    date_str=date_str,
                    url=url,
                    price_min=price_min,
                )
            ]

        # Free-form / recurring date text: expand into one event per upcoming
        # occurrence with the local datetime pre-computed.
        room = _parse_room(block, club_name)
        occurrences = _parse_datetimes(date_str, today)
        if not occurrences:
            if _EDID_RE.search(block):
                return []
            # A non-empty date string we could not parse — surface it rather
            # than dropping the show silently.
            Logger.warn(
                f"VboTicketsExtractor: unrecognized VBO date {date_str!r} for {name!r}"
            )
            return []
        return [
            VboEvent(
                eid=eid,
                name=name,
                date_str=date_str,
                url=url,
                price_min=price_min,
                start_iso=occ,
                room=room,
            )
            for occ in occurrences
        ]

    @staticmethod
    def _parse_detail_expansion_target(
        block: str,
        allowed_categories: Optional[Set[str]],
        club_name: str,
        today: date,
    ) -> Optional[VboDetailExpansionTarget]:
        eid_m = _EID_RE.search(block)
        edid_m = _EDID_RE.search(block)
        name_m = _NAME_RE.search(block)
        date_m = _DATE_RE.search(block)
        if not eid_m or not edid_m or not date_m:
            return None

        if allowed_categories is not None:
            cat_m = _CATEGORY_RE.search(block)
            category = (cat_m.group(1).strip().lower() if cat_m else "")
            if category not in allowed_categories:
                return None

        date_str = unescape(date_m.group(1).strip())
        if _VBO_DATE_RE.search(date_str) or _parse_datetimes(date_str, today):
            return None

        eid = eid_m.group(1)
        return VboDetailExpansionTarget(
            eid=eid,
            edid=edid_m.group(1),
            name=unescape((name_m.group(1) if name_m else "").strip()),
            date_str=date_str,
            url=_EVENT_URL.format(eid=eid),
            price_min=_parse_price(block),
            room=_parse_room(block, club_name),
        )
