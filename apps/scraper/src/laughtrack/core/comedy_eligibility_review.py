"""Human event decisions bind to the baseline, independently of model output."""

from __future__ import annotations

from dataclasses import asdict, replace
from typing import cast

from laughtrack.core.comedy_eligibility import (
    CLASSIFIER_VERSION,
    ComedyEligibilityDecision,
    EventEvidence,
    PerformerObservation,
    classify_comedy_eligibility,
    normalize_name,
)
from laughtrack.core.comedy_eligibility_store import canonical_json, fingerprint
from laughtrack.core.entities.club.comedy_policy import SourceComedyPolicy


def baseline_identity_fingerprint(decision, people, denied) -> str:
    return cast(
        str,
        fingerprint(
            {
                "classifier_version": CLASSIFIER_VERSION,
                "performers": decision.to_dict()["performers"],
                "people": sorted((asdict(p) for p in people), key=canonical_json),
                "denied": sorted((asdict(d) for d in denied), key=canonical_json),
            }
        ),
    )


def current_identity_fingerprint(cursor, row) -> str:
    """Revalidate preview against current parent/deny state inside apply's locks."""
    from laughtrack.core.comedy_eligibility_gate import _identity_snapshot

    payload = row["payload"]
    names = sorted({normalize_name(n) for n in payload.get("performers") or [] if isinstance(n, str) and n.strip()})
    people, denied = _identity_snapshot(cursor, names)
    decision = classify_comedy_eligibility(
        source_id=row["source_id"],
        policy=SourceComedyPolicy(version=row["policy_version"]),
        evidence=[EventEvidence(**e) for e in row["evidence"].get("evidence", [])],
        performers=[PerformerObservation(n) for n in names],
        people=people,
        denied=denied,
    )
    return baseline_identity_fingerprint(decision, people, denied)


def apply_review(decision: ComedyEligibilityDecision, state: dict):
    """Return effective decision, mandatory withhold, and whether human authority exists.

    Human holds apply in shadow as well as enforce. Off-mode bypass lives in the
    gate. Review decisions never change performer visibility or deny-list state.
    """
    action = state.get("review")
    if state.get("stale"):
        return (
            replace(
                decision,
                decision="review",
                confidence=0.0,
                reason_codes=tuple(sorted((*decision.reason_codes, "stale_human_review"))),
                classifier_version=f"{CLASSIFIER_VERSION}:human-stale:{state['review_version']}",
            ),
            True,
            True,
        )
    if action is None:
        return decision, False, False
    value = action["action"]
    if value not in {"approve", "reject", "defer"}:
        raise ValueError("Invalid persisted human review action")
    verdict = {"approve": "accept", "reject": "reject", "defer": "review"}[value]
    return (
        replace(
            decision,
            decision=verdict,
            confidence=1.0 if value != "defer" else 0.0,
            reason_codes=tuple(sorted((*decision.reason_codes, f"human_{value}"))),
            classifier_version=f"{CLASSIFIER_VERSION}:human:{action['id']}",
        ),
        value != "approve",
        True,
    )
