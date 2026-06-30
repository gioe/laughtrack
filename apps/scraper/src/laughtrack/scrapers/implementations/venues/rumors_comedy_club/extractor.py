"""Extraction for Rumor's Comedy Club Nuxt pages."""

import json
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from laughtrack.core.entities.event.rumors_comedy_club import RumorsComedyClubEvent
from laughtrack.foundation.utilities.html.utils import HtmlUtils

BASE_URL = "https://rumorscomedyclub.com"


class RumorsComedyClubExtractor:
    """Parse RumorsComedyClubEvent objects from the Nuxt SSR payload."""

    @staticmethod
    def extract_events(html_content: str, base_url: str = BASE_URL) -> List[RumorsComedyClubEvent]:
        payload = _extract_nuxt_payload(html_content)
        if not payload:
            return []

        events_by_key: Dict[tuple[str, str], RumorsComedyClubEvent] = {}
        for raw_event in _iter_payload_events(payload):
            if not isinstance(raw_event, dict) or raw_event.get("isSimpleEvent"):
                continue

            event_id = str(raw_event.get("id") or "").strip()
            name = str(raw_event.get("name") or "").strip()
            if not event_id or not name:
                continue

            description = _event_description(raw_event)
            show_page_url = urljoin(base_url, f"/events/{event_id}")
            for raw_show in raw_event.get("shows") or []:
                if not isinstance(raw_show, dict):
                    continue
                if _is_sold_out(raw_show):
                    continue

                show_id = str(raw_show.get("id") or "").strip()
                start_date = str(raw_show.get("date") or "").strip()
                if not show_id or not start_date:
                    continue

                ticket_url = urljoin(base_url, f"/events/{event_id}/{show_id}")
                ticket_price = _safe_float(raw_show.get("ticketPrice"))
                ticket_type = str(raw_show.get("type") or "General Admission").strip() or "General Admission"
                option = {
                    "purchase_url": ticket_url,
                    "price": ticket_price,
                    "type": ticket_type,
                }
                key = (name.lower(), start_date)
                if key in events_by_key:
                    events_by_key[key].ticket_options.append(option)
                    continue

                events_by_key[key] = RumorsComedyClubEvent(
                        name=name,
                        start_date=start_date,
                        show_page_url=show_page_url,
                        ticket_url=ticket_url,
                        ticket_price=ticket_price,
                        ticket_type=ticket_type,
                        description=description,
                        ticket_options=[option],
                    )

        return list(events_by_key.values())


def _iter_payload_events(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    for item in payload.get("data") or []:
        if isinstance(item, dict) and isinstance(item.get("events"), list):
            return item["events"]
    return []


def _event_description(raw_event: Dict[str, Any]) -> str:
    description = str(raw_event.get("description") or "").strip()
    if not description and raw_event.get("useBioForDescription"):
        comedian = raw_event.get("comedian") or {}
        if isinstance(comedian, dict):
            description = str(comedian.get("biography") or "").strip()
    return HtmlUtils.strip_tags(description).strip() if description else ""


def _is_sold_out(raw_show: Dict[str, Any]) -> bool:
    total = _safe_float(raw_show.get("totalTickets"))
    sold = _safe_float(raw_show.get("ticketsSold"))
    return total is not None and sold is not None and sold >= total


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_nuxt_payload(html_content: str) -> Optional[Dict[str, Any]]:
    marker = "window.__NUXT__=(function("
    start = html_content.find(marker)
    if start < 0:
        return None

    params_start = start + len("window.__NUXT__=(function(")
    params_end = html_content.find(")", params_start)
    if params_end < 0:
        return None

    params = [name.strip() for name in html_content[params_start:params_end].split(",") if name.strip()]
    return_match = re.search(r"\breturn\s+", html_content[params_end:])
    if not return_match:
        return None
    body_start = params_end + return_match.end()

    body_parser = _NuxtValueParser(html_content[body_start:], {})
    body, body_offset = body_parser.parse()
    if not isinstance(body, dict):
        return None

    after_body = body_start + body_offset
    call_start = html_content.find("}(", after_body)
    if call_start < 0:
        return None
    args_start = call_start + 2
    args_end = _matching_paren(html_content, args_start - 1)
    if args_end < 0:
        return None

    args_parser = _NuxtValueParser("[" + html_content[args_start:args_end] + "]", {})
    args, _ = args_parser.parse()
    aliases = dict(zip(params, args if isinstance(args, list) else []))
    resolved_body, _ = _NuxtValueParser(html_content[body_start:], aliases).parse()
    return resolved_body if isinstance(resolved_body, dict) else None


def _matching_paren(text: str, open_index: int) -> int:
    depth = 0
    in_string = ""
    escaped = False
    for index in range(open_index, len(text)):
        ch = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == in_string:
                in_string = ""
            continue
        if ch in ("'", '"'):
            in_string = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return index
    return -1


class _NuxtValueParser:
    """Small parser for Nuxt's JS object literal payload format."""

    _IDENT_RE = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*")

    def __init__(self, text: str, aliases: Dict[str, Any]):
        self.text = text
        self.aliases = aliases
        self.pos = 0

    def parse(self) -> tuple[Any, int]:
        value = self._parse_value()
        self._skip_ws()
        return value, self.pos

    def _parse_value(self) -> Any:
        self._skip_ws()
        if self.pos >= len(self.text):
            raise ValueError("Unexpected end of Nuxt payload")

        ch = self.text[self.pos]
        if ch == "{":
            return self._parse_object()
        if ch == "[":
            return self._parse_array()
        if ch in ("'", '"'):
            return self._parse_string()
        if ch == "-" or ch.isdigit():
            return self._parse_number()
        return self._parse_identifier_value()

    def _parse_object(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        self.pos += 1
        while True:
            self._skip_ws()
            if self._consume("}"):
                return result
            key = self._parse_key()
            self._skip_ws()
            if not self._consume(":"):
                raise ValueError(f"Expected ':' after key {key!r}")
            result[key] = self._parse_value()
            self._skip_ws()
            if self._consume(","):
                continue
            if self._consume("}"):
                return result
            raise ValueError("Expected ',' or '}' in object")

    def _parse_array(self) -> List[Any]:
        result: List[Any] = []
        self.pos += 1
        while True:
            self._skip_ws()
            if self._consume("]"):
                return result
            result.append(self._parse_value())
            self._skip_ws()
            if self._consume(","):
                continue
            if self._consume("]"):
                return result
            raise ValueError("Expected ',' or ']' in array")

    def _parse_key(self) -> str:
        self._skip_ws()
        if self.text[self.pos] in ("'", '"'):
            return str(self._parse_string())
        match = self._IDENT_RE.match(self.text, self.pos)
        if not match:
            raise ValueError("Expected object key")
        self.pos = match.end()
        return match.group(0)

    def _parse_string(self) -> str:
        quote = self.text[self.pos]
        start = self.pos
        self.pos += 1
        escaped = False
        while self.pos < len(self.text):
            ch = self.text[self.pos]
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                self.pos += 1
                raw = self.text[start : self.pos]
                if quote == '"':
                    return json.loads(raw)
                return json.loads('"' + raw[1:-1].replace('"', '\\"') + '"')
            self.pos += 1
        raise ValueError("Unterminated string")

    def _parse_number(self) -> Any:
        start = self.pos
        if self.text[self.pos] == "-":
            self.pos += 1
        while self.pos < len(self.text) and self.text[self.pos].isdigit():
            self.pos += 1
        if self.pos < len(self.text) and self.text[self.pos] == ".":
            self.pos += 1
            while self.pos < len(self.text) and self.text[self.pos].isdigit():
                self.pos += 1
        if self.pos < len(self.text) and self.text[self.pos] in ("e", "E"):
            self.pos += 1
            if self.pos < len(self.text) and self.text[self.pos] in ("+", "-"):
                self.pos += 1
            while self.pos < len(self.text) and self.text[self.pos].isdigit():
                self.pos += 1

        raw = self.text[start : self.pos]
        return float(raw) if any(part in raw for part in (".", "e", "E")) else int(raw)

    def _parse_identifier_value(self) -> Any:
        match = self._IDENT_RE.match(self.text, self.pos)
        if not match:
            raise ValueError("Expected value")
        self.pos = match.end()
        ident = match.group(0)
        if ident == "true":
            return True
        if ident == "false":
            return False
        if ident in {"null", "undefined"}:
            return None
        return self.aliases.get(ident)

    def _skip_ws(self) -> None:
        while self.pos < len(self.text) and self.text[self.pos].isspace():
            self.pos += 1

    def _consume(self, token: str) -> bool:
        if self.text.startswith(token, self.pos):
            self.pos += len(token)
            return True
        return False
