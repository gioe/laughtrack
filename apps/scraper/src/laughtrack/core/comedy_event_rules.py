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
    r"before|after|nearby|elsewhere|tomorrow|next week|next month|other room|another room|"
    r"upstairs|downstairs|other venue|another venue|also available|available for|contact us|inquire|enquire|"
    r"ignore|instructions|system prompt|classify|return accept|return reject)\b|[\"“”]",
    re.I,
)
_COMEDY_REFERENCE = re.compile(r"\b(?:comedy|comedian|comedians|stand[ -]?up|improv|sketch)\b", re.I)
_BOOKING = re.compile(r"book (?:your|a|an) (?:(?:holiday|private|corporate|birthday) )?(?:party|event)[.!]?", re.I)
_CLOSURE = re.compile(r"(?:we(?:'re| are) )?closed (?:for|due to) (?:a )?private (?:event|party)[.!]?", re.I)
_BULL_TITLE = re.compile(r"(?:(?:mechanical|comix) )?bull rides?[.!]?", re.I)
_PAINT = r"paint(?:\s*&\s*|\s+(?:and|n['’]?)\s+|-and-)sip"
_PAINT_TITLE = re.compile(rf"{_PAINT}(?: at [\w '&’.-]{{1,100}})?[.!]?", re.I)
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
        rf"(?:this (?:event|session) is (?:a )?|join us tonight for (?:a )?){_PAINT}\b", re.I)),
    ("unrelated_activity", "sewing_circle", re.compile(
        r"(?:this (?:event|session) is (?:a )?|join us tonight for (?:a )?)(?:monthly )?sewing circle\b", re.I)),
)
_DENIAL_SUBJECT = r"this (?:event|session|listing)\b"
_DENIAL = r"(?:not|no|never|without|isn['’]t|aren['’]t|doesn['’]t|don['’]t|won['’]t)"
_DENIAL_RULES = tuple(
    (family, reason, re.compile(
        rf"^{_DENIAL_SUBJECT}[^.!?]{{0,60}}\b{_DENIAL}\b[^.!?]{{0,60}}\b(?:{offering})\b"
        rf"|^{_DENIAL_SUBJECT}[^.!?]{{0,60}}\b(?:{offering})\b[^.!?]{{0,40}}\b(?:cancelled|canceled|postponed)\b",
        re.I,
    ))
    for family, reason, offering in (
        ("non_public", "private_event_closure", r"closed (?:for|due to) (?:a )?private (?:event|party)"),
        ("non_public", "booking_promotion", r"(?:party|event) bookings?"),
        ("unrelated_activity", "bull_rides", r"(?:mechanical )?bull rides?"),
        ("unrelated_activity", "paint_and_sip", _PAINT),
        ("unrelated_activity", "sewing_circle", r"sewing circle"),
    )
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
        if not checked or len(checked) > 600:
            continue
        denials = [(family, reason) for family, reason, pattern in _DENIAL_RULES if pattern.search(checked)]
        if denials:
            for family, reason in denials:
                item = _item(family, reason, "event_description", f"{url}\n{sentence.strip()}")
                # Explicit current denial is uncertainty, not an offering. Keep
                # it so a contradictory title cannot silently win classification.
                item["kind"] = "unknown"
                if item not in result:
                    result.append(item)
            continue
        guard_text = re.sub(r"\bbefore clos(?:e|ing)\b", "", checked, flags=re.I)
        if _UNSAFE.search(guard_text) or _COMEDY_REFERENCE.search(checked):
            continue
        for family, reason, pattern in _DESCRIPTION_RULES:
            if pattern.match(checked):
                item = _item(family, reason, "event_description", f"{url}\n{sentence.strip()}")
                if item not in result:
                    result.append(item)
    return result


# Families are versioned independently: extending event formats must not make
# already-recorded v1 availability/activity evidence invalid on replay.
CONTEXT_RULE_VERSION = "comedy-context-rules-v1"
RULE_REASONS.update({
    "event_format": frozenset({"music_performance", "karaoke", "sightseeing_tour", "games_sports"}),
    "comedy_format": frozenset({"live_comedy", "mixed_comedy", "musical_improv", "comedy_band_camp"}),
})
RULE_VERSIONS = {family: RULE_VERSION for family in ("non_public", "unrelated_activity")}
RULE_VERSIONS.update({family: CONTEXT_RULE_VERSION for family in ("event_format", "comedy_format")})
AUDIENCE_RULE_VERSION = "comedy-audience-formats-v1"
RULE_REASONS.update({
    "audience_format": frozenset({"live_performance", "screening", "instruction", "mixer", "ambiguous"}),
    "audience_content": frozenset({"comedy_instruction", "comedy_screening", "comedy_performance"}),
})
RULE_VERSIONS.update({family: AUDIENCE_RULE_VERSION for family in ("audience_format", "audience_content")})


def normalized_rule_text(text: str) -> str:
    """Normalize matching only; evidence retains the original Unicode text."""
    import unicodedata

    return " ".join(unicodedata.normalize("NFKC", text).translate(str.maketrans({
        "’": "'", "‘": "'", "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "−": "-",
    })).split())


_CONTEXT_UNSAFE = re.compile(
    r"\b(?:no|not|never|without|isn't|aren't|wasn't|weren't|doesn't|don't|won't|can't|cannot|"
    r"cancelled|canceled|cancellation|postponed|previously|formerly|was|were|used to|last year|last week|"
    r"example|hypothetical|pretend|imagine|called|named|titled|quotes?|rather than|"
    r"before|after|nearby|elsewhere|tomorrow|next week|next month|other room|another room|"
    r"upstairs|downstairs|other venue|another venue|also available|available for|contact us|inquire|enquire|"
    r"hosted|headlined|performed|appeared|starred|known for|recorded|released|toured|won|awarded|"
    r"netflix|youtube|comedy central|biography|ignore|instructions|system prompt|classify|"
    r"return accept|return reject)\b|\bin (?:19|20)\d{2}\b|[\"“”]", re.I,
)


def unsafe_context(text: str) -> bool:
    checked = normalized_rule_text(text)
    # Admission policies do not negate an offering.
    checked = re.sub(r"\b(?:no refunds|not refundable|no exchanges|no tickets or reservations needed)\b", "", checked, flags=re.I)
    checked = re.sub(r"\bhosted by\b", "", checked, flags=re.I)
    return bool(_CONTEXT_UNSAFE.search(checked))


_CONTEXT_NEGATIVE_PATTERNS = (
    ("karaoke", re.compile(r"\bkaraoke\b", re.I)),
    ("sightseeing_tour", re.compile(r"\b(?:walking|sightseeing|historical|history|ghost) tour\b", re.I)),
    ("games_sports", re.compile(
        r"\b(?:bingo|trivia|(?:boxing|wrestling) match|(?:basketball|football|baseball|hockey) game|"
        r"(?:sports|football|basketball|baseball|hockey|super bowl|nfl|nba|ufc) (?:watch party|viewing)|"
        r"(?:pro|professional) wrestling|wrestling (?:show|event))\b|^wrestling[.!]?$", re.I)),
    ("music_performance", re.compile(
        r"\b(?:live music|live (?:jazz|blues|funk|rock)|(?:jazz|rock|blues|orchestra|music) concert|"
        r"concert|tribute bands?|(?:ep|album) release|music(?:al)? open mic|dj set|live band)\b", re.I)),
)
_LIVE_COMEDY = re.compile(
    r"\b(?:stand[ -]?up (?:comedy|show|acts|performances?|night)|comedy (?:show|showcase|night|open mic|performances?)|"
    r"(?:sketch|improv) comedy)\b", re.I,
)
# Match only an explicit performance-format list, never a free-standing mention
# of comedy. Kept aligned with the older genre extractor's supported formats.
_PERFORMANCE_COMEDY = r"(?:comedy|stand[ -]?up(?: comedy)?)"
_PERFORMANCE_FORMAT = rf"(?:{_PERFORMANCE_COMEDY}|burlesque|cabaret|theatrical|dance|live music)"
_PERFORMANCE_SEPARATOR = r"(?:\s*,\s*(?:and\s+)?|\s+and\s+|\s*&\s*)"
_COMEDY_PERFORMANCE_LIST = re.compile(
    rf"\b(?:{_PERFORMANCE_FORMAT}{_PERFORMANCE_SEPARATOR}){{0,4}}{_PERFORMANCE_COMEDY}"
    rf"(?:{_PERFORMANCE_SEPARATOR}{_PERFORMANCE_FORMAT}){{0,4}}\s+performances?\b", re.I,
)
_MIXED_COMEDY = re.compile(
    r"\b(?:karaoke|bingo|trivia|live music)\s*(?:and|&|\+)\s*(?:live )?(?:comedy|stand[ -]?up)\b"
    r"|\b(?:comedy|stand[ -]?up)\s*(?:and|&|\+)\s*(?:karaoke|bingo|trivia|live music)\b", re.I,
)
_MUSICAL_IMPROV = re.compile(r"\b(?:music|musical) improv(?:isation)? (?:show|jam|performances?)\b", re.I)
_BAND_CAMP = re.compile(r"\bcomedy band camp\b", re.I)
_CURRENT_OFFERING = re.compile(
    r"^(?:this|the|our) (?:show|event|session|night|evening|performance) "
    r"(?:is |offers |features |includes |combines |presents )|^join us tonight for ", re.I,
)
_BIOGRAPHY = re.compile(r"\b(?:is|was) (?:an? )?(?:[\w-]+ ){0,3}(?:comedian|actor|writer|musician)\b", re.I)


def _context_item(kind: str, reason: str, provenance: str, detail: str) -> RuleEvidence:
    family = "comedy_format" if reason in RULE_REASONS["comedy_format"] else "event_format"
    return {"kind": kind, "provenance": provenance, "detail": detail,
            "rule_family": family, "rule_version": CONTEXT_RULE_VERSION, "rule_reason": reason}


def _context_subject(title: str) -> str:
    # A venue's branding after the offering cannot supply performance evidence.
    subject = re.split(r"\s+(?:at|@)\s+", title, maxsplit=1, flags=re.I)[0]
    return re.sub(r"^.{0,120}\b(?:presents|presents:)\s*", "", subject, flags=re.I).strip()



def _offered_positive_matches(pattern: re.Pattern, text: str) -> list[re.Match]:
    """Exclude a work credited by music/songs, while retaining another offering."""
    matches = []
    for match in pattern.finditer(text):
        # Strong billing separators or an explicitly introduced new performance
        # end the attribution scope. Ordinary words within a credited work do not.
        boundaries = [boundary.end() for boundary in re.finditer(
            r"[+|;/]|\band\s+(?=(?:a\s+|an\s+|live\s+)?(?:stand[ -]?up|comedy (?:show|performance)|musical improv))",
            text, flags=re.I,
        ) if boundary.end() <= match.start()]
        component = text[max(boundaries, default=0):match.start()]
        if not re.search(r"\b(?:music|songs?|soundtrack|cast|clips?)\s+(?:by|from|of)\b", component, re.I):
            matches.append(match)
    return matches


def _context_matches(checked: str, provenance: str, detail: str, *, positive_allowed: bool = True) -> list[RuleEvidence]:
    negative_matches = [(reason, list(pattern.finditer(checked))) for reason, pattern in _CONTEXT_NEGATIVE_PATTERNS]
    negatives = [reason for reason, matches in negative_matches if matches]
    positive = (
        "musical_improv" if _offered_positive_matches(_MUSICAL_IMPROV, checked) else
        "comedy_band_camp" if _offered_positive_matches(_BAND_CAMP, checked) else
        "mixed_comedy" if _offered_positive_matches(_MIXED_COMEDY, checked) else
        "live_comedy" if (_offered_positive_matches(_LIVE_COMEDY, checked)
                          or _offered_positive_matches(_COMEDY_PERFORMANCE_LIST, checked)) else None
    )
    if not positive_allowed:
        positive = None
    if unsafe_context(checked) or _BIOGRAPHY.search(checked):
        # Keep explicit uncertainty: otherwise a conflicting category or title
        # could win after a denial/cancellation was silently discarded.
        return [_context_item("unknown", (negatives or [positive])[0], provenance, detail)] if negatives or positive else []
    items = [_context_item("comedy", positive, provenance, detail)] if positive else []
    hybrid_spans = [match.span() for match in _offered_positive_matches(_MIXED_COMEDY, checked)] if positive else []
    if positive == "live_comedy":
        hybrid_spans.extend(match.span() for match in re.finditer(r"\bcomedic (?:historical )?tour\b", checked, re.I))
    # Only the negative phrase inside an explicit combination is excepted.
    # Another format (even another occurrence of the same format) still conflicts.
    for reason, matches in negative_matches:
        if any(not any(start <= match.start() and match.end() <= end for start, end in hybrid_spans)
               for match in matches):
            items.append(_context_item("event_format", reason, provenance, detail))
    return items


def context_title_evidence(title: object) -> list[RuleEvidence]:
    """Current title offerings, with explicit mixed-format comedy exceptions."""
    if not isinstance(title, str) or not 1 <= len(title) <= 300:
        return []
    checked = _context_subject(normalized_rule_text(title))
    # Bare artist names and words such as band, tour, music, or sports do not
    # match any format. Quotes, histories, and incidental timing stay uncertain.
    return _context_matches(checked, "event_billing", title)



def description_comedy_is_offered(text: str) -> bool:
    """A comedy phrase must head an offered component, not an artist's credit."""
    checked = normalized_rule_text(text)
    current = _CURRENT_OFFERING.match(checked)
    if current is None:
        # Existing genre grammar also supports explicit invitations and new-hour
        # billing. Attribution to another work never makes that work this event.
        return not re.search(r"\b(?:songs?|music) (?:by|from)|\bcast of|\bstarred in|\bknown for", checked, re.I)
    offering = checked[current.end():]
    # Explicit conjunctions can introduce additional promised performances.
    # Each component must itself begin with the performance format, so "Elvis,
    # who starred in a comedy show" and "songs from a comedy show" do not qualify.
    components = [offering, *re.split(r"\s+(?:and|with|alongside)\s+|\s*[,&+]\s*", offering, flags=re.I)]
    for component in components:
        component = re.sub(r"^(?:(?:a|an|live|free|r&b)\s+){0,3}", "", component, flags=re.I)
        if any(pattern.match(component) for pattern in (_LIVE_COMEDY, _COMEDY_PERFORMANCE_LIST, _MIXED_COMEDY, _MUSICAL_IMPROV, _BAND_CAMP)):
            return True
    return False


def context_description_evidence(text: str, url: str) -> list[RuleEvidence]:
    """Only explicit current-offering sentences in a validated event panel."""
    if not isinstance(text, str) or not 1 <= len(text) <= 16000:
        return []
    if re.search(r"\b(?:ignore|instructions|system prompt|classify|return (?:accept|reject))\b", text, re.I):
        return []
    result = []
    for sentence in re.split(r"(?<=[.!?;])\s+|[\r\n]+", text):
        checked = normalized_rule_text(sentence.strip().strip("*"))
        if not checked or len(checked) > 600:
            continue
        # Denials of this event's formats must survive even without the usual
        # affirmative verb, preventing contradictory titles from auto-rejecting.
        current = _CURRENT_OFFERING.match(checked)
        denial = re.match(r"^this (?:event|show|session)\b", checked, re.I) and unsafe_context(checked)
        if not current and not denial:
            continue
        for item in _context_matches(checked, "event_description", f"{url}\n{sentence.strip()}",
                                     positive_allowed=description_comedy_is_offered(checked)):
            if item not in result:
                result.append(item)
    return result


_AUDIENCE_LIVE = re.compile(
    r"\b(?:(?:graduation|grad(?:uation)? revue|student|class)\s+(?:comedy\s+)?(?:shows?|showcases?|performances?)"
    r"|(?:shows?|showcases?)\s*:\s*(?:improv|stand[ -]?up|class|graduation)"
    r"|(?:improv|stand[ -]?up|comedy)\s+(?:class\s+)?showcases?"
    r"|(?:improv|stand[ -]?up|comedy)(?:\s+comedy)?\s+graduation"
    r"|(?:improvised|improvisational)\s+(?:movie|film|comedy|theatre|theater)\s+(?:show|performance)"
    r"|(?:live\s+)?(?:stand[ -]?up|comedy|improv|sketch comedy)\s+(?:show|performance|theatre|theater)"
    r"|(?:musical|music) improv(?:isation)? (?:show|jam|performance))\b", re.I,
)
_AUDIENCE_SCREEN = re.compile(
    r"\b(?:(?:(?:movie|film|television|tv|comedy)\s+)?screening"
    r"|(?:classic\s+)?movie nights?|(?:movie|film|television|tv)\s+(?:viewing|watch party)"
    r"|watch(?:ing)?\s+(?:a |the )?(?:movie|film|television|tv))\b", re.I,
)
_AUDIENCE_CLASS = re.compile(
    r"\b(?:(?:(?:stand[ -]?up|comedy|improv)(?:\s+(?:comedy|writing))?\s+(?:level\s+\d+\s+)?)class(?:es)?"
    r"|(?:intro(?:duction)? to |drop-in |beginner(?:s)? )(?:(?:stand[ -]?up|comedy|improv)\s+)?class(?:es)?"
    r"|(?:class|course)\s+(?:enrollment|registration)|(?:enroll|register|sign up)\s+(?:now\s+)?(?:for|in)\s+(?:a |the |our )?(?:class|course|workshop)"
    r"|(?:comedy|improv|stand[ -]?up)\s+course)\b", re.I,
)
_AUDIENCE_WORKSHOP = re.compile(r"\bworkshops?\b", re.I)
_AUDIENCE_MIXER = re.compile(r"\b(?:corporate|business|networking) mixer\b", re.I)
_AUDIENCE_VARIETY = re.compile(r"\b(?:variety|drag|burlesque|magic)\s+(?:show|night|performance)\b", re.I)
_COMEDY_STUDY = re.compile(
    r"\b(?:stand[ -]?up(?: comedy)?|comedy(?: writing)?|improv)\s+(?:level\s+\d+\s+)?(?:class(?:es)?|course|workshop)\b"
    r"|\b(?:class|workshop|course) teaches (?:stand[ -]?up|comedy|improv)\b", re.I,
)
_COMEDY_SCREEN = re.compile(r"\bcomedy (?:film|movie|screening)\b", re.I)
_COMEDY_AUDIENCE_LIVE = re.compile(
    r"\b(?:stand[ -]?up|comedy|improv)(?:\s+(?:comedy|level|\d+|class|student|university|workshoppe|graduation)){0,5}\s+(?:shows?|showcases?|performances?|graduation|theatre|theater)\b"
    r"|\bimprovised (?:movie|film|comedy) (?:show|performance)\b"
    r"|\b(?:music|musical) improv(?:isation)? (?:show|jam|performance)\b", re.I,
)
_CLASS_PERFORMANCE = re.compile(r"\b(?:class|workshoppe?)\s+(?:graduation\s+)?(?:shows?|showcases?)\b", re.I)


def _audience_item(reason: str, provenance: str, detail: str, *, content: bool = False) -> RuleEvidence:
    return {"kind": "comedy" if content else "audience_format", "provenance": provenance, "detail": detail,
            "rule_family": "audience_content" if content else "audience_format",
            "rule_version": AUDIENCE_RULE_VERSION, "rule_reason": reason}


def _audience_matches(text: str, provenance: str, detail: str) -> list[RuleEvidence]:
    live = _offered_positive_matches(_AUDIENCE_LIVE, text)
    screen = list(_AUDIENCE_SCREEN.finditer(text))
    classes = list(_AUDIENCE_CLASS.finditer(text))
    workshops = list(_AUDIENCE_WORKSHOP.finditer(text))
    mixer = bool(_AUDIENCE_MIXER.search(text))
    variety = bool(_AUDIENCE_VARIETY.search(text))
    if not (live or screen or classes or workshops or mixer or variety):
        return []
    if unsafe_context(text) or _BIOGRAPHY.search(text):
        return [_audience_item("ambiguous", provenance, detail)]
    # Only a grammatical class-show phrase describes students performing.
    # An unrelated performance in the same sentence cannot erase enrollment.
    def performance_component(match):
        return any(offered.start() < match.end() and match.start() < offered.end()
                   for offered in _CLASS_PERFORMANCE.finditer(text))

    classes = [match for match in classes if not performance_component(match)]
    workshops = [match for match in workshops if not performance_component(match)]
    instruction = bool(classes) or bool(workshops and re.search(
        r"\b(?:learn|instruction|training|enroll|register|sign up|practice|skills|taught|teaches)\b", text, re.I))
    formats = {"live_performance"} if live else set()
    if screen:
        formats.add("screening")
    if instruction:
        formats.add("instruction")
    if mixer:
        formats.add("mixer")
    if (workshops and not instruction) or (variety and not live):
        formats.add("ambiguous")
    items = [_audience_item(reason, provenance, detail) for reason in sorted(formats)]
    # Genre is a separate claim: generic screenings/classes do not establish it.
    for pattern, reason, applies in (
        (_COMEDY_STUDY, "comedy_instruction", instruction or workshops),
        (_COMEDY_SCREEN, "comedy_screening", screen),
        (_COMEDY_AUDIENCE_LIVE, "comedy_performance", live),
    ):
        if applies and _offered_positive_matches(pattern, text):
            items.append(_audience_item(reason, provenance, detail, content=True))
    return items


def audience_title_evidence(title: object) -> list[RuleEvidence]:
    if not isinstance(title, str) or not 1 <= len(title) <= 300:
        return []
    return _audience_matches(_context_subject(normalized_rule_text(title)), "event_billing", title)


def audience_description_evidence(text: str, url: str) -> list[RuleEvidence]:
    """Use only after validated_event_description; retain current-offering citations."""
    if not isinstance(text, str) or not 1 <= len(text) <= 16000 or re.search(
        r"\b(?:ignore|instructions|system prompt|classify|return (?:accept|reject))\b", text, re.I,
    ):
        return []
    result = []
    for sentence in re.split(r"(?<=[.!?;])\s+|[\r\n]+", text):
        checked = normalized_rule_text(sentence.strip())
        if not checked or len(checked) > 600:
            continue
        current = _CURRENT_OFFERING.match(checked)
        instruction = re.match(
            r"^(?:this (?:class|workshop|course) (?:is|offers|teaches)|(?:enroll|register|sign up) (?:for|in))\b",
            checked, re.I,
        )
        if not (current or instruction):
            continue
        if current:
            offering = checked[current.end():]
            components = [offering, *re.split(r"\s+(?:and|with|alongside)\s+|\s*[,&+]\s*", offering, flags=re.I)]
            patterns = (_AUDIENCE_LIVE, _AUDIENCE_SCREEN, _AUDIENCE_CLASS, _AUDIENCE_WORKSHOP,
                        _AUDIENCE_MIXER, _AUDIENCE_VARIETY, _COMEDY_STUDY, _COMEDY_SCREEN,
                        _COMEDY_AUDIENCE_LIVE)
            if not any(pattern.match(re.sub(r"^(?:(?:a|an|live|free)\s+){0,3}", "", component, flags=re.I))
                       for component in components for pattern in patterns):
                continue
        result.extend(_audience_matches(checked, "event_description", f"{url}\n{sentence.strip()}"))
    return result
