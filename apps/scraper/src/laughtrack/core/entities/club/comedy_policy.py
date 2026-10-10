"""Source-owned comedy trust configuration; this module never filters events."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping

POLICIES = frozenset({"unreviewed", "comedy_only", "mixed"})
GATE_MODES = frozenset({"off", "shadow", "enforce"})


@dataclass(frozen=True)
class SourceComedyPolicy:
    policy: str = "unreviewed"
    gate_mode: str = "off"
    version: int = 1
    reviewed_by: str | None = None
    reviewed_at: datetime | str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.policy not in POLICIES:
            raise ValueError("Invalid comedy policy")
        if self.gate_mode not in GATE_MODES:
            raise ValueError("Invalid comedy gate mode")
        if type(self.version) is not int or self.version < 1:
            raise ValueError("Comedy policy version must be a positive integer")
        if not isinstance(self.evidence, dict):
            raise ValueError("Comedy policy evidence must be an object")

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "SourceComedyPolicy":
        return cls(
            policy=row.get("comedy_policy", "unreviewed"),
            gate_mode=row.get("comedy_gate_mode", "off"),
            version=row.get("comedy_policy_version", 1),
            reviewed_by=row.get("comedy_reviewed_by"),
            reviewed_at=row.get("comedy_reviewed_at"),
            evidence=row.get("comedy_review_evidence", {}),
        )

    def accepts_decision(self, *, source_id: int | None, decision_source_id: int, decision_policy_version: int) -> bool:
        """Only compare cache identity; this does not approve a comedy decision."""
        return source_id is not None and (source_id, self.version) == (decision_source_id, decision_policy_version)


UPDATE_POLICY_SQL = """
    UPDATE scraping_sources
    SET comedy_policy = %s, comedy_gate_mode = %s,
        comedy_reviewed_by = %s, comedy_review_evidence = %s::jsonb
    WHERE id = %s AND comedy_policy_version = %s
    RETURNING comedy_policy, comedy_gate_mode, comedy_policy_version,
              comedy_reviewed_by, comedy_reviewed_at, comedy_review_evidence
"""


def save_source_comedy_policy(cursor: Any, source_id: int, policy: SourceComedyPolicy) -> SourceComedyPolicy:
    """Persist through the caller's transaction; reject stale or missing sources.

    Supply the currently loaded version and a nonempty reviewer/evidence for
    changes. The database owns version increments and review timestamps.
    No source ownership, enabled flag or fetch configuration is updated.
    """
    import json

    if not policy.reviewed_by or not policy.reviewed_by.strip() or not policy.evidence:
        raise ValueError("Policy updates require reviewer and evidence")
    cursor.execute(
        UPDATE_POLICY_SQL,
        (
            policy.policy,
            policy.gate_mode,
            policy.reviewed_by,
            json.dumps(policy.evidence),
            source_id,
            policy.version,
        ),
    )
    row = cursor.fetchone()
    if row is None:
        raise ValueError("Source missing or comedy policy version changed; reload before retrying")
    if not isinstance(row, Mapping):
        row = dict(
            zip(
                (
                    "comedy_policy",
                    "comedy_gate_mode",
                    "comedy_policy_version",
                    "comedy_reviewed_by",
                    "comedy_reviewed_at",
                    "comedy_review_evidence",
                ),
                row,
            )
        )
    return SourceComedyPolicy.from_row(row)
