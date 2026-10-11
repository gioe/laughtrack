"""Bounded, deterministic rules over current event billing, never venue prose.

Descriptions must come from a validated same-event collector. This module does
not fetch sources, infer identity, decide publication, or change source policy.
"""

from __future__ import annotations

import re
from typing import TypedDict

RULE_VERSION = "comedy-event-rules-v1"
RULE_REASONS = {
    "non_public": frozenset({"booking_promotion", "private_event_closure"}),
    "unrelated_activity": frozenset({"bull_rides", "paint_and_sip", "sewing_circle"}),
}


class RuleEvidence(TypedDict):
    kind: str
    provenance: str
    detail: str
    rule_family: str
    rule_version: str
    rule_reason: str


_UNSAFE = re.compile(
    r"\b(?:no|not|never|without|isn['’]t|aren['’]t|doesn['’]t|don['’]t|won['’]t|"
    r"cancelled|canceled|postponed|previously|formerly|used to|last year|example|"
    r"hypothetical|pretend|imagine|called|named|titled|quotes?|rather than|"
    r"before|after|nearby|also available|available for|contact us|inquire|enquire|"
    r"ignore|instructions|system prompt|classify|return accept|return reject)\b|[\"“”]",
    re.I,
)
_COMEDY_REFERENCE = re.compile(r"\b(?:comedy|comedian|comedians|stand[ -]?up|improv|sketch)\b", re.I)
_BOOKING = re.compile(r"book (?:your|a|an) (?:(?:holiday|private|corporate|birthday) )?(?:party|event)[.!]?", re.I)
_CLOSURE = re.compile(r"(?:we(?:'re| are) )?closed (?:for|due to) (?:a )?private (?:event|party)[.!]?", re.I)
_BULL_TITLE = re.compile(r"(?:(?:mechanical|comix) )?bull rides?[.!]?", re.I)
_PAINT_TITLE = re.compile(r"paint\s*(?:&|and|n['’]?)\s*sip(?: at [\w '&’.-]{1,100})?[.!]?", re.I)
_SEWING_TITLE = re.compile(r"(?:[\w'-]+ ){0,4}(?:monthly )?sewing circle[.!]?", re.I)
_DESCRIPTION_RULES = (
    ("non_public", "private_event_closure", re.compile(
        r"this (?:event|listing) is closed (?:for|due to) (?:a )?private (?:event|party)[.!]?$", re.I)),
    ("non_public", "booking_promotion", re.compile(
        r"this listing is (?:for )?(?:private|holiday|corporate) (?:party|event) bookings?(?: only)?[.!]?$", re.I)),
    ("unrelated_activity", "bull_rides", re.compile(
        r"(?:ride (?:the|our) (?:(?:mechanical|comix) )?bull tonight\b|"
        r"this (?:event|session) (?:offers|features|is for) (?:mechanical )?bull rides?\b)", re.I)),
    ("unrelated_activity", "paint_and_sip", re.compile(
        r"(?:this (?:event|session) is (?:a )?|join us (?:tonight )?for (?:a )?)paint\s*(?:&|and)\s*sip\b", re.I)),
    ("unrelated_activity", "sewing_circle", re.compile(
        r"(?:this (?:event|session) is (?:a )?|join us (?:tonight )?for (?:a )?)(?:monthly )?sewing circle\b", re.I)),
)


def _item(family: str, reason: str, provenance: str, detail: str) -> RuleEvidence:
    return {"kind": family, "provenance": provenance, "detail": detail,
            "rule_family": family, "rule_version": RULE_VERSION, "rule_reason": reason}


def title_rule_evidence(title: object) -> list[RuleEvidence]:
    """Recognize a complete offering title; mentioning an activity is insufficient."""
    if not isinstance(title, str) or not 1 <= len(title) <= 300:
        return []
    checked = " ".join(title.split())
    if _UNSAFE.search(checked):
        return []
    rules = (
        ("non_public", "booking_promotion", _BOOKING),
        ("non_public", "private_event_closure", _CLOSURE),
        ("unrelated_activity", "bull_rides", _BULL_TITLE),
        ("unrelated_activity", "paint_and_sip", _PAINT_TITLE),
        ("unrelated_activity", "sewing_circle", _SEWING_TITLE),
    )
    result = []
    for family, reason, pattern in rules:
        # A comedy venue after "at" is allowed; a comedic title prefix is not.
        subject = re.split(r"\s+at\s+", checked, maxsplit=1, flags=re.I)[0] if reason == "paint_and_sip" else checked
        if pattern.fullmatch(checked) and not _COMEDY_REFERENCE.search(subject):
            result.append(_item(family, reason, "event_billing", title))
    return result


def description_rule_evidence(text: str, url: str) -> list[RuleEvidence]:
    """Consume only collector-validated event text; keep exact cited sentences."""
    if not isinstance(text, str) or not 1 <= len(text) <= 16000:
        return []
    # Instruction-like content invalidates the entire block, not one sentence.
    if re.search(r"\b(?:ignore|instructions|system prompt|classify|return (?:accept|reject))\b", text, re.I):
        return []
    result = []
    for sentence in re.split(r"(?<=[.!?;])\s+|[\r\n]+", text):
        checked = sentence.strip().strip("*").strip()
        guard_text = re.sub(r"\bbefore clos(?:e|ing)\b", "", checked, flags=re.I)
        if not checked or len(checked) > 600 or _UNSAFE.search(guard_text) or _COMEDY_REFERENCE.search(checked):
            continue
        for family, reason, pattern in _DESCRIPTION_RULES:
            if pattern.match(checked):
                item = _item(family, reason, "event_description", f"{url}\n{sentence.strip()}")
                if item not in result:
                    result.append(item)
    return result
