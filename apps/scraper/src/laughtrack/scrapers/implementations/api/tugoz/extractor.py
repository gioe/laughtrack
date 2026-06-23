"""Extraction helpers for Tugoz venue configuration and event payloads."""

import re
from typing import Any, Iterable

from .data import TugozEvent

_LIVE_EVENTS_RE = re.compile(r"LIVE_EVENTS\s*:\s*\{(?P<body>.*?)\}", re.DOTALL)
_LIVE_EVENT_ENTRY_RE = re.compile(r"(?P<key>[A-Za-z0-9_-]+)\s*:\s*(?P<event_id>\d+)")


class TugozExtractor:
    """Parse Tugoz event IDs and static event JSON."""

    @staticmethod
    def extract_live_event_ids(config_js: str, allowed_keys: Iterable[str] | None = None) -> list[int]:
        match = _LIVE_EVENTS_RE.search(config_js or "")
        if not match:
            return []

        allowed = {key.strip() for key in allowed_keys or [] if key and key.strip()}
        event_ids: list[int] = []
        for entry in _LIVE_EVENT_ENTRY_RE.finditer(match.group("body")):
            if allowed and entry.group("key") not in allowed:
                continue
            event_ids.append(int(entry.group("event_id")))
        return event_ids

    @staticmethod
    def event_from_payload(payload: dict[str, Any]) -> TugozEvent | None:
        return TugozEvent.from_api_response(payload)

