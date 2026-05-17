"""Auto-acceptance rules for podcast episode appearance review candidates."""

from __future__ import annotations

import hashlib
import html
import re
import unicodedata
from dataclasses import dataclass
from typing import Any


AUTO_ACCEPTANCE_RULE_VERSION = "podcast-appearance-auto-acceptance-v1"
_TITLE_CONFIDENCE_THRESHOLD = 0.95
_HIGH_TRUST_SOURCES = frozenset({"podcast_index"})
_HOST_ASSOCIATION_TYPES = frozenset({"host", "cohost"})


@dataclass(frozen=True)
class AutoAcceptanceCandidate:
    candidate_id: int
    comedian_id: int
    comedian_name: str
    podcast_title: str
    podcast_author: str
    episode_title: str
    role_guess: str
    confidence: float
    source: str
    source_field: str
    evidence_text: str
    evidence: dict[str, Any]
    host_association_types: list[str]


@dataclass(frozen=True)
class AutoAcceptanceResult:
    status: str
    rule_id: str | None
    evidence: dict[str, Any]


def normalize_match_text(value: str) -> str:
    unescaped = html.unescape(value or "")
    normalized = unicodedata.normalize("NFKD", unescaped)
    normalized = normalized.replace("\u2019", "'").replace("\u2018", "'")
    normalized = normalized.replace("\u2013", "-").replace("\u2014", "-")
    normalized = re.sub(r"(?i)\b([a-z0-9]+)'s\b", r"\1", normalized)
    normalized = re.sub(r"[^a-zA-Z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip().lower()


def _contains_normalized_phrase(text: str, phrase: str) -> bool:
    normalized_text = normalize_match_text(text)
    normalized_phrase = normalize_match_text(phrase)
    if not normalized_text or not normalized_phrase:
        return False
    return re.search(rf"(?<![a-z0-9]){re.escape(normalized_phrase)}(?![a-z0-9])", normalized_text) is not None


def _author_matches_comedian(candidate: AutoAcceptanceCandidate) -> bool:
    author = normalize_match_text(candidate.podcast_author)
    comedian = normalize_match_text(candidate.comedian_name)
    return bool(author and comedian and (author == comedian or comedian in author))


def _has_host_relationship(candidate: AutoAcceptanceCandidate) -> bool:
    return any(normalize_match_text(value) in _HOST_ASSOCIATION_TYPES for value in candidate.host_association_types)


def _with_rule_evidence(
    candidate: AutoAcceptanceCandidate,
    *,
    status: str,
    rule_id: str,
    reason: str,
) -> AutoAcceptanceResult:
    evidence = dict(candidate.evidence)
    evidence["auto_acceptance"] = {
        "rule_id": rule_id,
        "rule_version": AUTO_ACCEPTANCE_RULE_VERSION,
        "status": status,
        "reason": reason,
        "sample_eligible": status == "accepted",
    }
    return AutoAcceptanceResult(status=status, rule_id=rule_id, evidence=evidence)


def apply_auto_acceptance_rules(candidate: AutoAcceptanceCandidate) -> AutoAcceptanceResult:
    if candidate.source in _HIGH_TRUST_SOURCES and candidate.evidence.get("guid_match") is True:
        return _with_rule_evidence(
            candidate,
            status="accepted",
            rule_id="podcast_index_guid_match",
            reason="Podcast Index candidate evidence matched an episode GUID.",
        )

    if candidate.role_guess in _HOST_ASSOCIATION_TYPES and _has_host_relationship(candidate):
        return _with_rule_evidence(
            candidate,
            status="accepted",
            rule_id="accepted_host_relationship",
            reason="An accepted host/cohost comedian-podcast relationship already exists.",
        )

    if (
        candidate.role_guess == "guest"
        and candidate.confidence >= _TITLE_CONFIDENCE_THRESHOLD
        and (
            _contains_normalized_phrase(candidate.episode_title, candidate.comedian_name)
            or _author_matches_comedian(candidate)
        )
    ):
        return _with_rule_evidence(
            candidate,
            status="accepted",
            rule_id="high_confidence_title_name",
            reason="High-confidence guest candidate with comedian name in episode title or podcast author.",
        )

    if candidate.role_guess == "mention" and candidate.confidence < _TITLE_CONFIDENCE_THRESHOLD:
        return _with_rule_evidence(
            candidate,
            status="ignored",
            rule_id="low_signal_mention",
            reason="Mention-only candidate is low signal and excluded from manual review.",
        )

    return AutoAcceptanceResult(status="pending", rule_id=None, evidence=dict(candidate.evidence))


def build_spot_check_sample(
    candidates: list[AutoAcceptanceCandidate],
    *,
    sample_rate: float = 0.02,
) -> list[AutoAcceptanceCandidate]:
    eligible = [
        candidate
        for candidate in candidates
        if isinstance(candidate.evidence.get("auto_acceptance"), dict)
        and candidate.evidence["auto_acceptance"].get("sample_eligible") is not False
    ]
    if not eligible:
        return []
    sample_size = max(1, round(len(eligible) * sample_rate))
    ranked = sorted(
        eligible,
        key=lambda candidate: hashlib.sha256(
            f"{AUTO_ACCEPTANCE_RULE_VERSION}:{candidate.candidate_id}".encode("utf-8")
        ).hexdigest(),
    )
    return ranked[:sample_size]
