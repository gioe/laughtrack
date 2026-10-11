"""Transaction-owned staging; no global state or implicit commits."""

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping


LOAD_SOURCE_SQL = """
SELECT ss.*,
 COALESCE(to_jsonb(ss)->>'comedy_policy', 'unreviewed') AS comedy_policy,
 COALESCE(to_jsonb(ss)->>'comedy_gate_mode', 'off') AS comedy_gate_mode,
 COALESCE((to_jsonb(ss)->>'comedy_policy_version')::integer, 1) AS comedy_policy_version,
 to_jsonb(ss)->>'comedy_reviewed_by' AS comedy_reviewed_by,
 to_jsonb(ss)->>'comedy_reviewed_at' AS comedy_reviewed_at,
 COALESCE(to_jsonb(ss)->'comedy_review_evidence', '{}'::jsonb) AS comedy_review_evidence
FROM scraping_sources ss WHERE ss.id = %s
"""
UPSERT_CANDIDATE_SQL = """
INSERT INTO comedy_event_candidates(source_id,event_key,club_id) VALUES (%s,%s,%s)
ON CONFLICT(source_id,event_key) DO UPDATE SET last_seen_at=GREATEST(comedy_event_candidates.last_seen_at,now()),
 observation_generation=comedy_event_candidates.observation_generation+1
WHERE comedy_event_candidates.club_id=EXCLUDED.club_id
RETURNING id,observation_generation,review_version
"""
INSERT_DECISION_SQL = """
INSERT INTO comedy_event_decisions(candidate_id,payload_fingerprint,identity_fingerprint,
 policy_version,classifier_version,gate_mode,decision,payload,evidence)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)
ON CONFLICT(candidate_id,payload_fingerprint,identity_fingerprint,policy_version,classifier_version)
DO NOTHING RETURNING id
"""
FIND_DECISION_SQL = """
SELECT id FROM comedy_event_decisions WHERE candidate_id=%s AND payload_fingerprint=%s
 AND identity_fingerprint=%s AND policy_version=%s AND classifier_version=%s
"""
VERIFY_CANDIDATE_SQL = """
SELECT d.decision,d.gate_mode FROM comedy_event_candidates c
JOIN comedy_event_decisions d ON d.candidate_id=c.id
WHERE c.id=%s AND c.source_id=%s AND c.event_key=%s AND d.id=%s AND d.policy_version=%s
 AND c.observation_generation=%s AND c.review_version=%s
FOR UPDATE OF c
"""
INSERT_OBSERVATION_SQL = """
INSERT INTO comedy_event_observations(candidate_id,generation,decision_id,baseline_identity_fingerprint)
VALUES(%s,%s,%s,%s)
"""
LINK_PUBLICATION_SQL = """
INSERT INTO comedy_event_publications(candidate_id,decision_id,show_id)
SELECT c.id,d.id,s.id FROM comedy_event_candidates c
JOIN comedy_event_decisions d ON d.candidate_id=c.id
JOIN shows s ON s.club_id=c.club_id
WHERE c.id=%s AND d.id=%s AND s.id=%s
ON CONFLICT (candidate_id,decision_id,show_id) DO UPDATE SET published_at=comedy_event_publications.published_at
RETURNING show_id
"""


@dataclass(frozen=True)
class StagedCandidate:
    id: int
    decision_id: int
    source_id: int
    event_key: str
    policy_version: int
    gate_mode: str
    observation_generation: int = 1
    review_version: int = 0


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def _row(cursor: Any) -> dict | None:
    value = cursor.fetchone()
    if value is None:
        return None
    if isinstance(value, Mapping):
        return dict(value)
    return dict(zip([column[0] for column in cursor.description], value))


def load_source(cursor: Any, source_id: int, lock: bool = False) -> dict | None:
    """Policy columns remain optional before DDL; off mode needs no staging tables."""
    cursor.execute(LOAD_SOURCE_SQL + (" FOR SHARE OF ss" if lock else ""), (source_id,))
    return _row(cursor)


def stage_candidate(cursor: Any, *, source_id: int, event_key: str, club_id: int,
                    payload: dict, decision: Any, gate_mode: str,
                    identity_fingerprint: str = "", baseline_identity_fingerprint: str = "",
                    review_version: int | None = None) -> StagedCandidate:
    evidence = decision.to_dict() if hasattr(decision, "to_dict") else dict(decision)
    source = load_source(cursor, source_id, lock=True)
    version = evidence["policy_version"]
    if (source is None or not source["enabled"] or evidence.get("source_id") != source_id
            or source["comedy_policy"] != evidence.get("policy")
            or source["comedy_policy_version"] != version or source["comedy_gate_mode"] != gate_mode
            or gate_mode not in {"shadow", "enforce"}):
        raise ValueError("Source policy changed or staging source is unavailable")
    if not event_key:
        raise ValueError("A stable event identity is required")
    payload_json, evidence_json = canonical_json(payload), canonical_json(evidence)
    # Resolved identity evidence is part of dedup even when the source payload is unchanged.
    identity_digest = fingerprint({"snapshot": identity_fingerprint, "performers": evidence.get("performers", [])})
    payload_digest = fingerprint(payload)
    cursor.execute(UPSERT_CANDIDATE_SQL, (source_id, event_key, club_id))
    candidate = _row(cursor)
    if candidate is None:
        raise ValueError("Candidate identity changed physical venue; requires review")
    if review_version is not None and candidate["review_version"] != review_version:
        raise ValueError("Human review changed during staging")
    key = (candidate["id"], payload_digest, identity_digest, version, evidence["classifier_version"])
    cursor.execute(INSERT_DECISION_SQL, (*key, gate_mode, evidence["decision"], payload_json, evidence_json))
    revision = _row(cursor)
    if revision is None:
        cursor.execute(FIND_DECISION_SQL, key)
        revision = _row(cursor)
    if revision is None:
        raise RuntimeError("Concurrent staging decision unavailable; retry transaction")
    cursor.execute(INSERT_OBSERVATION_SQL, (candidate["id"], candidate["observation_generation"], revision["id"], baseline_identity_fingerprint or identity_digest))
    return StagedCandidate(candidate["id"], revision["id"], source_id, event_key, version, gate_mode, candidate["observation_generation"], candidate["review_version"])


def verify_publication(cursor: Any, staged: StagedCandidate) -> bool:
    """Hold source and candidate locks until caller finishes public persistence."""
    source = load_source(cursor, staged.source_id, lock=True)
    if (source is None or not source["enabled"] or source["comedy_policy_version"] != staged.policy_version
            or source["comedy_gate_mode"] != staged.gate_mode):
        return False
    cursor.execute(VERIFY_CANDIDATE_SQL, (staged.id, staged.source_id, staged.event_key,
                                        staged.decision_id, staged.policy_version, staged.observation_generation, staged.review_version))
    revision = _row(cursor)
    return bool(revision and revision["gate_mode"] == staged.gate_mode
                and (staged.gate_mode == "shadow" or revision["decision"] == "accept"))


def link_published(cursor: Any, staged: StagedCandidate, show_id: int) -> None:
    if not verify_publication(cursor, staged):
        raise ValueError("Publication decision is stale or ineligible")
    cursor.execute(LINK_PUBLICATION_SQL, (staged.id, staged.decision_id, show_id))
    if _row(cursor) is None:
        raise ValueError("Published show does not belong to candidate venue")
