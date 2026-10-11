"""Conservative event-description evidence; scraped prose is never authority."""
from __future__ import annotations

import re
from urllib.parse import urlsplit

from laughtrack.core.comedy_event_rules import description_comedy_is_offered, normalized_rule_text, unsafe_context

DETAIL_SELECTOR = "#event-detail #descr .custom-content"
BIO_SELECTOR = "#event-detail #bio"
_BILLING_ADJECTIVE = r"(?:hilarious|high-energy|raw|uncensored|monthly|live|new|brand-new|headlining|gloriously|nerdy)"
# Genre lists are deliberately bounded to performance formats: a reference to
# comedians as people (or music written by them) is not comedy billing.
_COMEDY = r"(?:comedy|stand[\s\-\u2011]?up(?:\s+comedy)?)"
_FORMAT = rf"(?:{_COMEDY}|burlesque|cabaret|theatrical|dance|live music)"
_LIST_SEPARATOR = r"(?:\s*,\s*(?:and\s+)?|\s+and\s+|\s+&\s+)"
_FORMAT_PREFIX = rf"(?:{_FORMAT}{_LIST_SEPARATOR}){{0,4}}"
_FORMAT_SUFFIX = rf"(?:{_LIST_SEPARATOR}{_FORMAT}){{0,4}}"
_CURRENT_COMEDY = re.compile(
    rf"\b(?:a|an|this|the|our)\s+(?:{_BILLING_ADJECTIVE}[,\s]+){{0,4}}"
    rf"(?:night|evening|hour)\s+of\s+(?:{_BILLING_ADJECTIVE}[,\s]+){{0,3}}{_FORMAT_PREFIX}{_COMEDY}\b"
    rf"|\b(?:this|the|our)\s+{_COMEDY}\s+(?:burlesque\s+)?(?:show|cabaret|extravaganza|performance)\b"
    rf"|\b(?:this|the|our)\s+(?:show|cabaret|production|event)\s+(?:features|includes)\s+"
    rf"{_FORMAT_PREFIX}{_COMEDY}{_FORMAT_SUFFIX}\s+performances?\b"
    r"|\bsee\s+\d+\+?\s+(?:of\s+the\s+)?(?:(?:best|local|live|top)\s+){0,3}comedians?\s+(?:live|on stage)\b"
    r"|\b(?:get ready for|join us for)\s+a\s+night\s+filled with\s+(?:top\s+)?performers\s+"
    r"alongside\s+(?:the\s+)?(?:(?:sharpest|best|local|top)\s+){0,2}comedians?\b"
    rf"|\bwe\s+(?:start|begin|open)\s+with\s+(?:{_BILLING_ADJECTIVE}[,\s]+){{0,3}}{_COMEDY}\s+(?:from|by)\b"
    rf"|\b(?:party|show|cabaret)\s+packed with\s+(?:(?:jaw-dropping|live|theatrical)\s+){{0,2}}"
    rf"performances?{_LIST_SEPARATOR}{_COMEDY}\b"
    rf"|\bour cast\s+brings\b[^.!?]{{0,100}}\bto life with\s+{_FORMAT_PREFIX}{_COMEDY}"
    rf"{_FORMAT_SUFFIX}\s+performances?\b"
    r"|\bnow\s+(?:[\w'-]+\s+){1,4}brings\s+"
    r"(?:(?:that|same|his|her|their|sharp|unfiltered|political|live)[,\s]+){0,7}"
    r"comedy\s+to\b[^.!?]{0,100}\b(?:tour|live)\b",
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
    r"hosted|headlined|performed|appeared|produced|recorded|released|toured|won(?!['’]t\b)|awarded|screening|screenings|clips|footage|memorabilia|"
    r"has (?:appeared|performed)|appeared on|performed on|netflix|youtube|comedy central)\b"
    r"|\bin (?:19|20)\d{2}\b", re.I,
)
_NEGATION = re.compile(r"\b(?:no|not|never|without|won['’]t|doesn['’]t|don['’]t|isn['’]t|aren['’]t|cancelled|canceled|cancellation|postponed)\b", re.I)
_BIO = re.compile(r"\b(?:is|was)\s+(?:an?\s+)?(?:[\w-]+\s+){0,3}(?:comedian|actor|writer|musician)\b", re.I)
_CURRENT_NEGATIVE = re.compile(
    r"\b(?:no|without)\s+(?:live\s+)?(?:comedy|stand[ -]?up)\b"
    r"|\bnot\s+(?:a\s+)?(?:comedy|stand[ -]?up)\b"
    r"|\b(?:(?:does|will)\s+not|(?:won|doesn)['’]t)\s+(?:feature|include|offer|present)\b[^.!?]{0,35}\b(?:comedy|stand[ -]?up)\b"
    r"|\b(?:this|the|tonight'?s)\s+(?:show|event|performance)\s+(?:(?:has been|is|was)\s+)?"
    r"(?:cancelled|canceled|postponed)\b"
    r"|\b(?:comedy|stand[ -]?up)\b[^.!?]{0,70}\b(?:cancelled|canceled|postponed)\b"
    r"|^(?:cancelled|canceled|postponed)[.!]?$", re.I,
)


def unsafe_billing(text: str) -> bool:
    # Ticket boilerplate is not negation of the performance itself.
    checked = re.sub(r"\b(?:no refunds|not refundable|no exchanges)\b", "", normalized_rule_text(text), flags=re.I)
    checked = re.sub(r"\b(?:won['’]t want to miss|don['’]t miss)\b", "", checked, flags=re.I)
    return bool(unsafe_context(checked) or _NEGATION.search(checked) or _UNTRUSTED.search(checked))


def _validated_event_blocks(event: object) -> tuple[list[dict], str] | None:
    """Only consume a bounded, explicitly collected, same-event detail marker.

    Sentence text and the validated source URL are retained for later review.
    The marker is produced by the SeatEngine adapter after checking page identity;
    Arbitrary Show.description is not an input. Separately tagged biography
    panels can supply current program statements, never identity-only proof.
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
    url = marker.get("url")
    blocks = marker.get("blocks", [{"selector": DETAIL_SELECTOR, "text": marker.get("text")}])
    if not isinstance(blocks, list) or not 1 <= len(blocks) <= 2:
        return None
    selectors = set()
    for block in blocks:
        if not isinstance(block, dict) or block.get("selector") not in {DETAIL_SELECTOR, BIO_SELECTOR}:
            return None
        text = block.get("text")
        if block["selector"] in selectors or not isinstance(text, str) or not 1 <= len(text) <= 16000:
            return None
        selectors.add(block["selector"])
    if (sum(len(block["text"]) for block in blocks) > 16000 or not isinstance(url, str)
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
    # Instructions invalidate all panels, not just the paragraph containing them.
    text = "\n".join(block["text"] for block in blocks)
    if re.search(r"\b(?:ignore|instructions|system prompt|classify|return (?:accept|reject))\b", normalized_rule_text(text), re.I):
        return None
    return blocks, url


def validated_event_description(event: object) -> tuple[str, str] | None:
    """Share only the verified description panel with offering-format rules.

    Biography panels have a separate current-program grammar and citation. They
    must not silently acquire the description panel's broader rule semantics.
    """
    detail = _validated_event_blocks(event)
    if detail is None:
        return None
    blocks, url = detail
    for block in blocks:
        if block["selector"] == DETAIL_SELECTOR:
            return block["text"], url
    return None


def description_evidence(event: object) -> list[dict]:
    """Extract current program statements from independently identified panels."""
    detail = _validated_event_blocks(event)
    if detail is None:
        return []
    blocks, url = detail
    evidence = []
    for block in blocks:
        for sentence in re.split(r"(?<=[.!?;])\s+|[\r\n]+", block["text"]):
            sentence = sentence.strip()
            if not sentence or len(sentence) > 600:
                continue
            # Normalize typography only for matching; preserve original citations.
            checked = normalized_rule_text(sentence)
            detail = f"{url}\n{sentence}"
            if block["selector"] == BIO_SELECTOR:
                detail = f"{url}\n{BIO_SELECTOR}\n{sentence}"
            if _CURRENT_NEGATIVE.search(checked) and not _UNTRUSTED.search(checked):
                evidence.append({"kind": "unknown", "provenance": "event_description", "detail": detail})
                continue
            if unsafe_billing(checked) or _BIO.search(checked):
                continue
            for kind, pattern in (("comedy", _CURRENT_COMEDY), ("music", _CURRENT_MUSIC)):
                if pattern.search(checked) and (kind != "comedy" or description_comedy_is_offered(checked)):
                    item = {"kind": kind, "provenance": "event_description", "detail": detail}
                    if item not in evidence:
                        evidence.append(item)
    return evidence
