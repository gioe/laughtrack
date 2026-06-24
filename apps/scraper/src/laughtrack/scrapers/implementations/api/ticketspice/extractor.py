"""Parser for a TicketSpice (Webconnex) ticketing-form page.

A TicketSpice form (``<account>.ticketspice.com/<slug>``) embeds its full
configuration in a ``window.__BOOTSTRAP__`` JavaScript object literal at the top
of the page HTML. Two of its members are themselves JSON *strings* (escaped):

- ``appSettings`` — ``formName`` (show title), ``eventStart`` (ISO timestamp of
  the *first* date, e.g. ``2026-06-28T02:30:00Z``), ``timeZone``, ``status``
  (1 == active/published).
- ``formData`` — the rendered form tree. The ``ticketBlock`` element holds the
  date-selection inventory: a ``categories`` list where each category is a
  selectable show date (``label`` like ``"June 27"``, ``description`` the
  lineup) plus its priced ``levels``.

MULTI-DATE: a single form can sell several dates. ``appSettings.eventStart``
names only the *first* one; the rest live in ``formData.ticketBlock.categories``.
:func:`extract_events` parses ONE :class:`TicketSpiceEvent` per upcoming dated
category (``show_page_url`` = the form URL), and falls back to the single
``eventStart`` date when the form has no dated categories (single-date forms like
The Stage at Burke, validated 2026-06-23 against
thestage.ticketspice.com/barley-me-comedy). :func:`extract_event` remains as a
single-result convenience wrapper.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, time, timezone
from typing import Any, List, Optional

from laughtrack.core.entities.event.ticketspice import TicketSpiceEvent

# `key: "<escaped-json-string>"` inside the window.__BOOTSTRAP__ object literal.
# The value is a double-quoted string whose body may contain escaped quotes
# (\") and other backslash escapes; match a run of (non-quote-non-backslash | \.)
# so we stop at the real closing quote, then unescape.
_JS_STRING_RE_TMPL = r'{key}:\s*"((?:[^"\\]|\\.)*)"'

# Month names -> month number, for parsing category labels like "June 27" /
# "Aug 22" that carry no year (the year is inferred from eventStart/minDate).
_MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

# "June 27", "Aug 22", "September 5" — a month word followed by a day-of-month.
# Anchored at the start of the label so unrelated labels ("Donation to ...") miss.
_MONTH_DAY_RE = re.compile(r"^\s*([A-Za-z]{3,9})\.?\s+(\d{1,2})\b")


def _extract_js_json_string(html: str, key: str) -> Optional[Any]:
    """Pull a JSON-string-valued member out of the bootstrap object and parse it."""
    m = re.search(_JS_STRING_RE_TMPL.format(key=re.escape(key)), html, re.S)
    if not m:
        return None
    # m.group(1) is the raw body of a JS double-quoted string whose value is
    # itself JSON. Unescape it by re-quoting the captured body and JSON-decoding
    # it once (which resolves \", \\, \/, and \uXXXX while preserving raw UTF-8
    # bytes), then JSON-decode the resulting inner JSON text. Using
    # decode("unicode_escape") instead would mojibake any literal (non-\u-escaped)
    # UTF-8 in the body — e.g. a non-Latin formName.
    try:
        inner = json.loads('"' + m.group(1) + '"')
        return json.loads(inner)
    except (json.JSONDecodeError, ValueError):
        return None


def _find_ticket_blocks(form_data: Any) -> List[dict]:
    """Collect every ``type == "ticketBlock"`` node in the form tree."""
    blocks: List[dict] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if node.get("type") == "ticketBlock":
                blocks.append(node)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(form_data)
    return blocks


def _level_price(level: Any) -> Optional[float]:
    """Numeric price of one ticket level, or None when absent/non-numeric."""
    if not isinstance(level, dict):
        return None
    raw = level.get("price")
    try:
        if raw is not None and str(raw).strip() != "":
            return float(raw)
    except (TypeError, ValueError):
        return None
    return None


def _lowest_price(form_data: Any) -> Optional[float]:
    """Lowest numeric ticket-level price across the whole form tree, or None."""
    prices: List[float] = []
    for block in _find_ticket_blocks(form_data):
        for level in block.get("levels", []) or []:
            p = _level_price(level)
            if p is not None:
                prices.append(p)
    return min(prices) if prices else None


def _lowest_price_for_category(form_data: Any, category_id: str) -> Optional[float]:
    """Lowest price among *visible* levels tied to ``category_id``, or None.

    Falls back to None so the caller can use the form-wide lowest price.
    """
    prices: List[float] = []
    for block in _find_ticket_blocks(form_data):
        for level in block.get("levels", []) or []:
            if not isinstance(level, dict):
                continue
            if level.get("category") != category_id:
                continue
            # Skip hidden/back-office levels so an admin-only $1 row can't
            # masquerade as the public price.
            if level.get("visible") is False:
                continue
            p = _level_price(level)
            if p is not None:
                prices.append(p)
    return min(prices) if prices else None


def _reference_date(app_settings: dict, form_data: Any) -> date:
    """A reference date used to assign a year to year-less category labels.

    Prefers ``appSettings.eventStart`` (the first show date); falls back to the
    ticketBlock ``minDate`` (sale-window start), then to today. Year-rollover is
    handled relative to this date so a "January" label after a December
    eventStart lands in the next year.
    """
    ev = _parse_date(app_settings.get("eventStart"))
    if ev is not None:
        return ev
    for block in _find_ticket_blocks(form_data):
        md = _parse_date(block.get("minDate"))
        if md is not None:
            return md
    return datetime.now(timezone.utc).date()


def _parse_date(raw: Any) -> Optional[date]:
    """Leading ``YYYY-MM-DD`` of an ISO date/datetime string, else None."""
    if not isinstance(raw, str):
        return None
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", raw)
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def _parse_event_time(app_settings: dict) -> Optional[time]:
    """Wall-clock show time from ``eventStart`` localized to the form timezone.

    ``eventStart`` is a UTC timestamp (e.g. ``2026-06-28T02:30:00Z`` == the local
    show start). We convert it into the form's ``timeZone`` so the same
    wall-clock time can be reused for every dated category. Returns None when the
    timestamp is date-only (UTC midnight, no real time) or unparseable.
    """
    import pytz

    raw = app_settings.get("eventStart")
    if not isinstance(raw, str):
        return None
    m = re.match(
        r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})Z", raw
    )
    if not m:
        return None
    y, mo, d, hh, mm, ss = (int(g) for g in m.groups())
    if (hh, mm, ss) == (0, 0, 0):
        # Date-only marker (UTC midnight) — no reliable wall-clock time.
        return None
    tz_name = app_settings.get("timeZone") or "America/Los_Angeles"
    try:
        utc_dt = datetime(y, mo, d, hh, mm, ss, tzinfo=timezone.utc)
        local_dt = utc_dt.astimezone(pytz.timezone(tz_name))
        return local_dt.timetz().replace(tzinfo=None)
    except (ValueError, pytz.UnknownTimeZoneError):
        return None


def _parse_category_date(label: str, reference: date) -> Optional[date]:
    """Parse a year-less ``"June 27"`` category label into a full date.

    The year is taken from ``reference``; if the resulting date is more than ~60
    days before the reference (i.e. the series has rolled into the next year),
    bump it forward a year so e.g. a "January" label after a December reference
    resolves to next January rather than this past one.
    """
    m = _MONTH_DAY_RE.match(label or "")
    if not m:
        return None
    month = _MONTHS.get(m.group(1).lower())
    if month is None:
        return None
    day = int(m.group(2))
    try:
        candidate = date(reference.year, month, day)
    except ValueError:
        return None
    if (reference - candidate).days > 60:
        try:
            candidate = date(reference.year + 1, month, day)
        except ValueError:
            return None
    return candidate


def _build_event(
    title: str,
    event_date: date,
    form_url: str,
    price: Optional[float],
    sold_out: bool,
    event_time: Optional[time],
    description: Optional[str],
) -> TicketSpiceEvent:
    return TicketSpiceEvent(
        title=title,
        event_date=event_date,
        form_url=form_url,
        price=price,
        sold_out=sold_out,
        event_time=event_time,
        description=(description or None),
    )


def extract_events(html: str, form_url: str) -> List[TicketSpiceEvent]:
    """Parse a TicketSpice form page into one or more :class:`TicketSpiceEvent`.

    Multi-date forms (a date-selection ``categories`` inventory) yield one event
    per dated category. Single-date forms (no dated categories) yield a single
    event from ``appSettings.eventStart``. Returns ``[]`` when the bootstrap is
    missing, the form is unpublished (``status != 1``), or no date can be read.
    """
    if not html:
        return []

    app_settings = _extract_js_json_string(html, "appSettings")
    if not isinstance(app_settings, dict):
        return []

    # status 1 == active/published. Skip drafts/disabled forms (no live show).
    if app_settings.get("status") not in (1, "1"):
        return []

    title = (app_settings.get("formName") or "").strip()
    if not title:
        return []

    form_data = _extract_js_json_string(html, "formData")
    has_form = isinstance(form_data, (dict, list))
    form_sold_out = bool(form_data.get("soldOut")) if isinstance(form_data, dict) else False
    event_time = _parse_event_time(app_settings)

    # --- Multi-date path: one event per dated date-selection category. ---
    events: List[TicketSpiceEvent] = []
    if has_form:
        reference = _reference_date(app_settings, form_data)
        seen_dates: set = set()
        for block in _find_ticket_blocks(form_data):
            for cat in block.get("categories", []) or []:
                if not isinstance(cat, dict):
                    continue
                cat_date = _parse_category_date(cat.get("label") or "", reference)
                if cat_date is None or cat_date in seen_dates:
                    continue  # non-date category (e.g. a donation) or duplicate
                seen_dates.add(cat_date)
                cat_price = _lowest_price_for_category(form_data, cat.get("id"))
                events.append(
                    _build_event(
                        title=title,
                        event_date=cat_date,
                        form_url=form_url,
                        price=cat_price if cat_price is not None else _lowest_price(form_data),
                        sold_out=form_sold_out,
                        event_time=event_time,
                        description=(cat.get("description") or "").strip() or None,
                    )
                )
    if events:
        return events

    # --- Single-date fallback: appSettings.eventStart (legacy single-form). ---
    event_date = _parse_date(app_settings.get("eventStart")) or _parse_date(
        (app_settings.get("calendarInfo") or {}).get("date")
    )
    if event_date is None:
        return []
    return [
        _build_event(
            title=title,
            event_date=event_date,
            form_url=form_url,
            price=_lowest_price(form_data) if has_form else None,
            sold_out=form_sold_out,
            event_time=event_time,
            description=None,
        )
    ]


def extract_event(html: str, form_url: str) -> Optional[TicketSpiceEvent]:
    """Single-result convenience wrapper around :func:`extract_events`.

    Returns the first parsed event (or ``None``). Retained for backward
    compatibility; new callers should prefer :func:`extract_events`.
    """
    events = extract_events(html, form_url)
    return events[0] if events else None
