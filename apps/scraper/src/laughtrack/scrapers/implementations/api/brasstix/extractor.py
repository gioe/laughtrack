"""Extract BrassTix calendar entries from inline JavaScript."""

from __future__ import annotations

import re
from urllib.parse import urljoin

from laughtrack.core.entities.event.brasstix import BrassTixEvent

_EVENT_RE = re.compile(
    r"\{title:'(?P<title>(?:\\'|[^'])*)',"
    r"subtitle:'(?P<subtitle>(?:\\'|[^'])*)',"
    r"eventid:'(?P<event_id>[^']*)',"
    r"start:'(?P<start>[^']*)',"
    r"url:'(?P<url>[^']*)'"
    r".*?,ShowName:'(?P<show_name>[^']*)'\}",
    re.DOTALL,
)

_STATUS_LABELS = {
    "BEST AVAILABILITY",
    "SELLING OUT",
    "SOLD OUT",
}


def extract_brasstix_events(html: str, calendar_url: str) -> list[BrassTixEvent]:
    """Return future purchasable calendar entries embedded in BrassTix JS."""
    events: list[BrassTixEvent] = []
    for match in _EVENT_RE.finditer(html or ""):
        raw_url = _unescape_js_string(match.group("url")).strip()
        if not raw_url:
            continue

        title_lines = _clean_lines(_unescape_js_string(match.group("title")))
        subtitle_lines = _clean_lines(_unescape_js_string(match.group("subtitle")))
        title_parts = [line for line in title_lines if line.upper() not in _STATUS_LABELS]
        if not title_parts:
            continue

        availability_parts = [
            line for line in [*title_lines, *subtitle_lines] if line.upper() in _STATUS_LABELS
        ]
        events.append(
            BrassTixEvent(
                event_id=_unescape_js_string(match.group("event_id")).strip(),
                title=" ".join(title_parts),
                start=_unescape_js_string(match.group("start")).strip(),
                ticket_url=urljoin(calendar_url, raw_url.replace(" ", "%20")),
                show_name=_unescape_js_string(match.group("show_name")).strip(),
                availability_label="; ".join(dict.fromkeys(availability_parts)),
            )
        )
    return events


def _clean_lines(value: str) -> list[str]:
    return [" ".join(line.split()) for line in value.splitlines() if line.strip()]


def _unescape_js_string(value: str) -> str:
    return (
        value.replace("\\n", "\n")
        .replace("\\r", "\r")
        .replace("\\t", "\t")
        .replace("\\'", "'")
        .replace("\\\\", "\\")
    )
