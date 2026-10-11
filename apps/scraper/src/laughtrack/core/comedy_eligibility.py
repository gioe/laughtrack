"""Pure pre-ingestion comedy decisions over event evidence and identity snapshots.

Adapters supply normalized, event-scoped evidence, not venue branding, performer
biographies or raw platform category IDs. No entity construction, I/O, cache writes
or rollout enforcement occurs here. Confidence values are rule strengths, not
empirically calibrated probabilities.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Iterable, cast

if TYPE_CHECKING:
    from laughtrack.core.entities.club.comedy_policy import SourceComedyPolicy

CLASSIFIER_VERSION = "comedy-eligibility-v2"
_LABEL_KINDS = frozenset({"troupe", "show_label"})
_KINDS = _LABEL_KINDS | {"person"}
_NON_COMEDY_BLOCK_REASONS = frozenset({"non_comedian_musician", "musician", "non_comedy_sports"})
_PROVENANCE = frozenset({"event_category", "event_billing", "event_description"})


def normalize_name(name: str) -> str:
    return " ".join(name.replace("\xa0", " ").split()).lower()


@dataclass(frozen=True)
class EventEvidence:
    kind: str
    provenance: str
    detail: str

    def __post_init__(self) -> None:
        if not all(isinstance(value, str) for value in (self.kind, self.provenance, self.detail)):
            raise ValueError("Event evidence fields must be strings")

    @property
    def valid(self) -> bool:
        return (
            self.kind in {"comedy", "music", "sports"}
            and self.provenance in _PROVENANCE
            and isinstance(self.detail, str)
            and bool(self.detail.strip())
        )


@dataclass(frozen=True)
class CanonicalPerson:
    id: int
    name: str
    visible: bool
    parent_id: int | None = None
    block_reason: str | None = None
    entity_kind: str = "person"

    def __post_init__(self) -> None:
        if type(self.id) is not int or self.id <= 0 or not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Identity snapshots require a positive ID and name")
        if type(self.visible) is not bool or self.entity_kind not in _KINDS:
            raise ValueError("Identity snapshots require explicit visibility and valid entity kind")
        if self.parent_id is not None and (type(self.parent_id) is not int or self.parent_id <= 0):
            raise ValueError("Parent IDs must be positive integers")


@dataclass(frozen=True)
class DeniedName:
    name: str
    reason: str
    entity_kind: str = "person"

    def __post_init__(self) -> None:
        if not self.name.strip() or self.entity_kind not in _KINDS:
            raise ValueError("Deny entries require a name and valid entity kind")


@dataclass(frozen=True)
class PerformerObservation:
    name: str
    comedian_id: int | None = None
    # Explicit reviewed adapter evidence, never guessed from a name or block reason.
    structural_kind: str | None = None
    structural_evidence: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Performer observations require a name")
        if self.comedian_id is not None and (type(self.comedian_id) is not int or self.comedian_id <= 0):
            raise ValueError("Performer IDs must be positive integers")
        if self.structural_kind is not None and self.structural_kind not in _LABEL_KINDS:
            raise ValueError("Only troupe and show_label structural exceptions are supported")


@dataclass(frozen=True)
class ResolvedPerformer:
    identity_key: str
    names: tuple[str, ...]
    state: str  # unblocked, blocked, unknown, conflict
    canonical_id: int | None
    block_reasons: tuple[str, ...]
    diagnostics: tuple[str, ...]
    structural_exception: bool
    structural_evidence: tuple[str, ...]


@dataclass(frozen=True)
class ComedyEligibilityDecision:
    decision: str
    reason_codes: tuple[str, ...]
    confidence: float
    source_id: int | None
    policy: str
    policy_version: int
    classifier_version: str
    evidence: tuple[EventEvidence, ...]
    performers: tuple[ResolvedPerformer, ...]
    lineup_status: str
    blocked_count: int
    performer_count: int

    def to_dict(self) -> dict[str, Any]:
        """JSON-safe stable contract suitable for staging and replay."""
        import json

        return cast(dict[str, Any], json.loads(json.dumps(asdict(self), sort_keys=True)))


def _reviewed_trust(policy: SourceComedyPolicy) -> bool:
    if (
        policy.policy != "comedy_only"
        or not policy.reviewed_by
        or not policy.reviewed_by.strip()
        or not policy.evidence
    ):
        return False
    value = policy.reviewed_at
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return False
    return isinstance(value, datetime) and value.tzinfo is not None


def _resolve_performers(
    observations: Iterable[PerformerObservation], people: Iterable[CanonicalPerson], denied: Iterable[DeniedName]
) -> tuple[ResolvedPerformer, ...]:
    identities: dict[int, CanonicalPerson] = {}
    collisions: set[int] = set()
    by_name: dict[str, set[int]] = {}
    for person in people:
        if person.id in identities and identities[person.id] != person:
            collisions.add(person.id)
        identities[person.id] = person
        by_name.setdefault(normalize_name(person.name), set()).add(person.id)
    denials: dict[str, list[DeniedName]] = {}
    for entry in denied:
        denials.setdefault(normalize_name(entry.name), []).append(entry)

    def blocks(person: CanonicalPerson) -> tuple[str, ...]:
        reasons = [d.reason or "deny_list" for d in denials.get(normalize_name(person.name), [])]
        if not person.visible:
            reasons.append(person.block_reason or "hidden_without_reason")
        return tuple(sorted(set(reasons)))

    # Memoization is per call, so policy/identity changes cannot leak stale results.
    cache: dict[int, tuple[int | None, str]] = {}

    def root(pid: int) -> tuple[int | None, str]:
        path: list[int] = []
        seen: set[int] = set()
        current = pid
        while True:
            if current in cache:
                result = cache[current]
                break
            if current in seen:
                result = (None, "parent_cycle")
                break
            if current in collisions:
                result = (None, "identity_collision")
                break
            person = identities.get(current)
            if person is None:
                result = (None, "missing_parent_or_identity")
                break
            path.append(current)
            seen.add(current)
            if person.parent_id is None:
                result = (current, "blocked" if blocks(person) else "unblocked")
                break
            current = person.parent_id
        for member in path:
            cache[member] = result
        return result

    merged: dict[str, dict[str, Any]] = {}
    for observation in observations:
        name = normalize_name(observation.name)
        candidate_ids = by_name.get(name, set())
        pid = observation.comedian_id
        diagnostics: set[str] = set()
        state = "unknown"
        canonical_id = None
        reasons: set[str] = {d.reason or "deny_list" for d in denials.get(name, [])}
        kinds: list[str] = []
        if pid is not None and (pid not in identities or name != normalize_name(identities[pid].name)):
            state = "conflict"
            diagnostics.add("identity_name_mismatch" if pid in identities else "missing_parent_or_identity")
        elif pid is None and len(candidate_ids) > 1:
            # Distinct name matches are only safe if every path resolves to the same root.
            roots = {root(i) for i in candidate_ids}
            if len(roots) == 1 and next(iter(roots))[0] is not None:
                pid = min(candidate_ids)
            else:
                state = "conflict"
                diagnostics.add("ambiguous_name")
        elif pid is None and candidate_ids:
            pid = next(iter(candidate_ids))
        if pid is not None and state != "conflict":
            canonical_id, resolved = root(pid)
            own = identities[pid]
            reasons.update(blocks(own))
            if canonical_id is None:
                state = "conflict"
                diagnostics.add(resolved)
            else:
                canonical = identities[canonical_id]
                state = resolved
                reasons.update(blocks(canonical))
                kinds.append(canonical.entity_kind)
                kinds.extend(d.entity_kind for d in denials.get(normalize_name(canonical.name), []))
                if pid != canonical_id:
                    diagnostics.add("canonical_parent_resolved")
        elif state == "unknown" and name in denials:
            state = "blocked"
            reasons.update(d.reason or "deny_list" for d in denials[name])
            kinds.extend(d.entity_kind for d in denials[name])
        if state == "unknown":
            diagnostics.add("unverified_performer")
        if state == "unblocked":
            diagnostics.add("database_membership_not_comedy_evidence")
        structural = bool(
            state == "blocked"
            and not any(normalize_name(reason) in _NON_COMEDY_BLOCK_REASONS for reason in reasons)
            and kinds
            and all(k in _LABEL_KINDS for k in kinds)
            and observation.structural_kind in _LABEL_KINDS
            and all(k == observation.structural_kind for k in kinds)
            and isinstance(observation.structural_evidence, str)
            and observation.structural_evidence.strip()
        )
        key = f"person:{canonical_id}" if canonical_id is not None else f"name:{name}"
        item = merged.setdefault(
            key,
            {
                "names": set(),
                "states": set(),
                "reasons": set(),
                "diagnostics": set(),
                "canonical_id": canonical_id,
                "structural": True,
                "structural_evidence": set(),
            },
        )
        item["names"].add(name)
        item["states"].add(state)
        item["reasons"].update(reasons)
        item["diagnostics"].update(diagnostics)
        item["structural"] = item["structural"] and structural
        if structural:
            item["structural_evidence"].add(observation.structural_evidence)
    result = []
    for key, item in sorted(merged.items()):
        state = next(iter(item["states"])) if len(item["states"]) == 1 else "conflict"
        result.append(
            ResolvedPerformer(
                key,
                tuple(sorted(item["names"])),
                state,
                item["canonical_id"],
                tuple(sorted(item["reasons"])),
                tuple(sorted(item["diagnostics"])),
                item["structural"],
                tuple(sorted(item["structural_evidence"])),
            )
        )
    return tuple(result)


def classify_comedy_eligibility(
    *,
    source_id: int | None,
    policy: SourceComedyPolicy,
    evidence: Iterable[EventEvidence] = (),
    performers: Iterable[PerformerObservation] | None = None,
    people: Iterable[CanonicalPerson] = (),
    denied: Iterable[DeniedName] = (),
) -> ComedyEligibilityDecision:
    """Evaluate normalized evidence without creating or suppressing any entities.

    Gate mode is deliberately ignored: off/shadow/enforce is an orchestration
    choice, not a change in what the same event evidence means.
    """
    if source_id is not None and (type(source_id) is not int or source_id <= 0):
        raise ValueError("Source ID must be a positive integer")
    observed = tuple(performers or ())
    supplied = tuple(sorted(set(evidence), key=lambda e: (e.kind, e.provenance, e.detail)))
    valid = tuple(e for e in supplied if e.valid)
    resolved = _resolve_performers(observed, people, denied)
    reasons: set[str] = set()
    if not resolved:
        reasons.add("missing_lineup")
    if any(p.state == "unknown" for p in resolved):
        reasons.add("unverified_performer")
    if any(p.state == "unblocked" for p in resolved):
        reasons.add("database_membership_not_comedy_evidence")
    if any("canonical_parent_resolved" in p.diagnostics for p in resolved):
        reasons.add("canonical_parent_resolved")
    blocked = sum(p.state == "blocked" for p in resolved)
    total = len(resolved)
    all_blocked = total > 0 and blocked == total
    majority = total > 0 and blocked * 2 > total
    if all_blocked:
        reasons.add("blocked_only_lineup")
    elif majority:
        reasons.add("majority_blocked_lineup")
    conflict = any(p.state == "conflict" for p in resolved)
    if conflict:
        reasons.add("identity_conflict")
    positive = any(e.kind == "comedy" for e in valid)
    negative = any(e.kind in {"music", "sports"} for e in valid)
    if positive:
        reasons.add("affirmative_event_comedy")
    if negative:
        reasons.add("explicit_non_comedy_event")

    if any(not e.valid for e in supplied):
        decision, confidence = "review", 0.3
        reasons.add("invalid_event_evidence")
    elif positive and negative:
        decision, confidence = "review", 0.5
        reasons.add("conflicting_event_evidence")
    elif negative:
        decision, confidence = "reject", 0.95
    elif conflict:
        decision, confidence = "review", 0.4
    elif all_blocked:
        if positive and all(p.structural_exception for p in resolved):
            decision, confidence = "accept", 0.85
            reasons.add("structural_label_exception")
        elif positive:
            decision, confidence = "review", 0.5
            reasons.add("comedy_block_conflict")
        else:
            decision, confidence = "reject", 0.9
    elif majority:
        decision, confidence = "review", 0.5
    elif positive:
        decision, confidence = "accept", 0.9
    elif _reviewed_trust(policy):
        decision, confidence = "accept", 0.7
        reasons.add("reviewed_comedy_only_source")
    else:
        decision, confidence = "review", 0.3
        reasons.add("insufficient_event_evidence")
        if policy.policy == "comedy_only":
            reasons.add("unverified_source_policy")
    return ComedyEligibilityDecision(
        decision,
        tuple(sorted(reasons)),
        confidence,
        source_id,
        policy.policy,
        policy.version,
        CLASSIFIER_VERSION,
        supplied,
        resolved,
        (
            "missing"
            if not resolved
            else "partial" if any(p.state in {"unknown", "conflict"} for p in resolved) else "observed"
        ),
        blocked,
        total,
    )
