"""Conservative event-description evidence; scraped prose is never authority."""
from __future__ import annotations

import re
from urllib.parse import urlsplit

DETAIL_SELECTOR = "#event-detail #descr .custom-content"
# Genre lists are deliberately bounded to performance formats: a reference to
# comedians as people (or music written by them) is not comedy billing.
_COMEDY = r"(?:comedy|stand[\s\-\u2011]?up(?:\s+comedy)?)"
_FORMAT = rf"(?:{_COMEDY}|burlesque|cabaret|theatrical|dance|live music)"
_LIST_SEPARATOR = r"(?:\s*,\s*(?:and\s+)?|\s+and\s+|\s+&\s+)"
_FORMAT_PREFIX = rf"(?:{_FORMAT}{_LIST_SEPARATOR}){{0,4}}"
_FORMAT_SUFFIX = rf"(?:{_LIST_SEPARATOR}{_FORMAT}){{0,4}}"
_CURRENT_COMEDY = re.compile(
    rf"\b(?:a|an|this|the|our)\s+(?:(?:hilarious|high-energy|raw|uncensored|monthly|live|new|brand-new)\s+){{0,4}}"
    rf"(?:night|evening|hour)\s+of\s+{_FORMAT_PREFIX}{_COMEDY}\b"
    rf"|\b(?:this|the|our)\s+{_COMEDY}\s+(?:burlesque\s+)?(?:show|cabaret|extravaganza|performance)\b"
    rf"|\b(?:this|the|our)\s+(?:show|cabaret|production|event)\s+(?:features|includes)\s+"
    rf"{_FORMAT_PREFIX}{_COMEDY}{_FORMAT_SUFFIX}\s+performances?\b"
    r"|\bsee\s+\d+\+?\s+(?:of\s+the\s+)?(?:(?:best|local|live|top)\s+){0,3}comedians?\s+(?:live|on stage)\b"
    r"|\b(?:get ready for|join us for)\s+a\s+night\s+filled with\s+(?:top\s+)?performers\s+"
    r"alongside\s+(?:the\s+)?(?:(?:sharpest|best|local|top)\s+){0,2}comedians?\b",
    re.I,
)
_CURRENT_MUSIC = re.compile(
    r"\b(?:this|the|a|an|our)\s+(?:show|event|night|evening|experience|showcase)\b"
    r"[^.!?]{0,100}\b(?:live music|live (?:jazz|blues|funk)|music concert|karaoke)\b"
    r"|\b(?:this|the|a|an)\s+(?:epic\s+)?(?:night|evening)\s+of\s+live music\b"
    r"|\b(?:karaoke|live music)\s+(?:starts|begins)\b", re.I,
)
_UNTRUSTED = re.compile(
    r"\b(?:ignore\b[^.!?]{0,50}\binstructions|system prompt|classify\b[^.!?]{0,30}\bas|"
    r"return (?:accept|reject)|pretend|example|hypothetical|compared to|rather than|"
    r"sounds? like|looks? like|(?:is|was|feels?) like|as if|would be|used to|previously|formerly|last year|"
    r"hosted|headlined|performed|appeared|produced|recorded|released|toured|won|awarded|"
    r"has (?:appeared|performed)|appeared on|performed on|netflix|youtube|comedy central)\b"
    r"|\bin (?:19|20)\d{2}\b", re.I,
)
_NEGATION = re.compile(r"\b(?:no|not|never|without|cancelled|canceled|cancellation|postponed)\b", re.I)
_BIO = re.compile(r"\b(?:is|was)\s+(?:an?\s+)?(?:[\w-]+\s+){0,3}(?:comedian|actor|writer|musician)\b", re.I)
_CURRENT_NEGATIVE = re.compile(
    r"\b(?:no|without)\s+(?:live\s+)?(?:comedy|stand[ -]?up)\b"
    r"|\bnot\s+(?:a\s+)?(?:comedy|stand[ -]?up)\b"
    r"|\b(?:does|will)\s+not\s+(?:feature|include|offer|present)\b[^.!?]{0,35}\b(?:comedy|stand[ -]?up)\b"
    r"|\b(?:this|the|tonight'?s)\s+(?:show|event|performance)\s+(?:(?:has been|is|was)\s+)?"
    r"(?:cancelled|canceled|postponed)\b"
    r"|\b(?:comedy|stand[ -]?up)\b[^.!?]{0,70}\b(?:cancelled|canceled|postponed)\b"
    r"|^(?:cancelled|canceled|postponed)[.!]?$", re.I,
)


def unsafe_billing(text: str) -> bool:
    # Ticket boilerplate is not negation of the performance itself.
    checked = re.sub(r"\b(?:no refunds|not refundable|no exchanges)\b", "", text, flags=re.I)
    return bool(_NEGATION.search(checked) or _UNTRUSTED.search(checked) or re.search(r"\bwas\b", checked, re.I))


def validated_event_description(event: object) -> tuple[str, str] | None:
    """Return text and citation URL only for the collected same-event marker.

    Arbitrary Show.description and biography panels are never inputs here.
    Shared by genre extraction and the separately versioned offering rules.
    """
    if not isinstance(event, dict) or not isinstance(event.get("event"), dict):
        return None
    marker = event.get("_comedy_event_detail")
    if not isinstance(marker, dict) or marker.get("status") != "collected" or marker.get("selector") != DETAIL_SELECTOR:
        return None
    event_id = str(event["event"].get("id", ""))
    show_id = str(marker.get("show_id", ""))
    if not event_id.isdigit() or str(marker.get("event_id")) != event_id or not show_id.isdigit():
        return None
    text, url = marker.get("text"), marker.get("url")
    if (not isinstance(text, str) or not 1 <= len(text) <= 16000 or not isinstance(url, str)
            or len(url) > 2048 or any(c.isspace() for c in url)):
        return None
    try:
        parts = urlsplit(url)
        _ = parts.port  # Reject malformed ports rather than retaining a misleading citation URL.
        if (parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password
                or parts.query or parts.fragment or parts.path.rstrip("/") != f"/shows/{show_id}"):
            return None
    except ValueError:
        return None
    # Instructions invalidate the whole description; sentence splitting is not
    # an invitation to follow a later instruction after ignoring the first one.
    if re.search(r"\b(?:ignore\b.{0,50}\binstructions|system prompt|return (?:accept|reject))\b", text, re.I):
        return None
    return text, url


def description_evidence(event: object) -> list[dict]:
    """Extract current performance statements and retain exact source citations."""
    detail = validated_event_description(event)
    if detail is None:
        return []
    text, url = detail
    evidence = []
    for sentence in re.split(r"(?<=[.!?;])\s+|[\r\n]+", text):
        sentence = sentence.strip()
        if not sentence or len(sentence) > 600:
            continue
        if _CURRENT_NEGATIVE.search(sentence) and not _UNTRUSTED.search(sentence):
            evidence.append({"kind": "unknown", "provenance": "event_description", "detail": f"{url}\n{sentence}"})
            continue
        if unsafe_billing(sentence) or _BIO.search(sentence):
            continue
        for kind, pattern in (("comedy", _CURRENT_COMEDY), ("music", _CURRENT_MUSIC)):
            if pattern.search(sentence):
                item = {"kind": kind, "provenance": "event_description", "detail": f"{url}\n{sentence}"}
                if item not in evidence:
                    evidence.append(item)
    return evidence
