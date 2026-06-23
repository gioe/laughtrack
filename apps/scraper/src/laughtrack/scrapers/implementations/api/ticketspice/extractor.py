"""Parser for a TicketSpice (Webconnex) ticketing-form page.

A TicketSpice form (``<account>.ticketspice.com/<slug>``) is a single-event
ticketing page that embeds its full configuration in a ``window.__BOOTSTRAP__``
JavaScript object literal at the top of the page HTML. Two of its members are
themselves JSON *strings* (escaped):

- ``appSettings`` — ``formName`` (show title), ``eventStart`` (ISO date at UTC
  midnight, date-only — NO reliable show time), ``timeZone``, ``status``
  (1 == active/published).
- ``formData`` — the rendered form tree, including ``ticketBlock`` ``levels``
  with the ticket ``price``; ``soldOut`` flags the whole form as sold out.

:func:`extract_event` parses those into a single :class:`TicketSpiceEvent`, or
``None`` when the form is unpublished or carries no event date. Validated
2026-06-23 against the live "Barley & Me Pod-uctions Comedy Show" form at
thestage.ticketspice.com/barley-me-comedy (1 GA level, $9, eventStart
2026-06-07, schedules: []).
"""

from __future__ import annotations

import json
import re
from datetime import date
from typing import Any, List, Optional

from laughtrack.core.entities.event.ticketspice import TicketSpiceEvent

# `key: "<escaped-json-string>"` inside the window.__BOOTSTRAP__ object literal.
# The value is a double-quoted string whose body may contain escaped quotes
# (\") and other backslash escapes; match a run of (non-quote-non-backslash | \.)
# so we stop at the real closing quote, then unescape.
_JS_STRING_RE_TMPL = r'{key}:\s*"((?:[^"\\]|\\.)*)"'


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


def _lowest_price(form_data: Any) -> Optional[float]:
    """Return the lowest numeric ticket-level price in the form tree, or None."""
    prices: List[float] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if node.get("type") == "ticketBlock":
                for level in node.get("levels", []) or []:
                    raw = level.get("price") if isinstance(level, dict) else None
                    try:
                        if raw is not None and str(raw).strip() != "":
                            prices.append(float(raw))
                    except (TypeError, ValueError):
                        continue
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(form_data)
    return min(prices) if prices else None


def _parse_event_date(app_settings: dict) -> Optional[date]:
    """Date portion of appSettings.eventStart (or calendarInfo.date) — no time."""
    for raw in (app_settings.get("eventStart"), (app_settings.get("calendarInfo") or {}).get("date")):
        if not raw or not isinstance(raw, str):
            continue
        # e.g. "2026-06-07T00:00:00Z" — take the leading YYYY-MM-DD.
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", raw)
        if m:
            try:
                return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                continue
    return None


def extract_event(html: str, form_url: str) -> Optional[TicketSpiceEvent]:
    """Parse one TicketSpice form page into a single TicketSpiceEvent.

    Returns ``None`` when the bootstrap is missing, the form is not published
    (``status != 1``), or no event date can be read.
    """
    if not html:
        return None

    app_settings = _extract_js_json_string(html, "appSettings")
    if not isinstance(app_settings, dict):
        return None

    # status 1 == active/published. Skip drafts/disabled forms (no live show).
    if app_settings.get("status") not in (1, "1"):
        return None

    title = (app_settings.get("formName") or "").strip()
    event_date = _parse_event_date(app_settings)
    if not title or event_date is None:
        return None

    form_data = _extract_js_json_string(html, "formData")
    price = _lowest_price(form_data) if isinstance(form_data, (dict, list)) else None
    sold_out = bool(form_data.get("soldOut")) if isinstance(form_data, dict) else False

    return TicketSpiceEvent(
        title=title,
        event_date=event_date,
        form_url=form_url,
        price=price,
        sold_out=sold_out,
    )
