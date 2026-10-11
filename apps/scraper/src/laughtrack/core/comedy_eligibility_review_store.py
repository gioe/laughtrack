"""Explicit, optimistic event review; no public persistence or source-policy edits."""
import json
from uuid import uuid4

from laughtrack.core.comedy_eligibility_store import _row, fingerprint, load_source

CURRENT_SQL = """
SELECT c.id AS candidate_id,c.source_id,c.club_id,c.event_key,c.observation_generation,c.review_version,
 o.decision_id,o.baseline_identity_fingerprint AS identity_fingerprint,
 d.payload_fingerprint,d.policy_version,d.payload,d.evidence,d.decision,d.classifier_version,
 ss.comedy_policy_version AS current_policy_version,ss.comedy_gate_mode AS gate_mode,ss.enabled,
 ss.comedy_policy AS source_policy,ss.comedy_reviewed_by,ss.comedy_reviewed_at,ss.comedy_review_evidence,
 cl.name AS club_name,ss.scraper_key,
 r.action AS review_action,r.identity_fingerprint AS reviewed_identity_fingerprint,
 r.payload_fingerprint AS reviewed_payload_fingerprint,r.policy_version AS reviewed_policy_version
FROM comedy_event_candidates c
JOIN clubs cl ON cl.id=c.club_id JOIN scraping_sources ss ON ss.id=c.source_id
LEFT JOIN comedy_event_observations o ON o.candidate_id=c.id AND o.generation=c.observation_generation
LEFT JOIN comedy_event_decisions d ON d.candidate_id=c.id AND d.id=o.decision_id
LEFT JOIN comedy_event_reviews r ON r.candidate_id=c.id AND r.review_version=c.review_version
WHERE c.id=%s
"""
LOAD_REVIEW_SQL = """
SELECT c.review_version,r.id,r.action,r.reason,r.actor,r.payload_fingerprint,r.identity_fingerprint,r.policy_version
FROM comedy_event_candidates c LEFT JOIN comedy_event_reviews r
 ON r.candidate_id=c.id AND r.review_version=c.review_version
WHERE c.source_id=%s AND c.event_key=%s
"""
INSERT_PREVIEW_SQL = """
INSERT INTO comedy_review_previews(id,actor,action,reason,items,token_digest,expires_at)
VALUES(%s,%s,%s,%s,%s::jsonb,%s,clock_timestamp()+interval '15 minutes')
"""
LOAD_PREVIEW_SQL = "SELECT *,expires_at>clock_timestamp() AS fresh FROM comedy_review_previews WHERE id=%s FOR UPDATE"
LOAD_OPERATION_SQL = "SELECT * FROM comedy_review_operations WHERE idempotency_key=%s OR preview_id=%s"
INSERT_OPERATION_SQL = """
INSERT INTO comedy_review_operations(idempotency_key,preview_id,actor,token_digest,result)
VALUES(%s,%s,%s,%s,%s::jsonb)
"""
ADVANCE_REVIEW_SQL = """
UPDATE comedy_event_candidates SET review_version=review_version+1
WHERE id=%s AND review_version=%s AND observation_generation=%s RETURNING review_version
"""
INSERT_REVIEW_SQL = """
INSERT INTO comedy_event_reviews(candidate_id,observation_generation,decision_id,review_version,
 payload_fingerprint,identity_fingerprint,policy_version,actor,reason,action,operation_key)
VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
"""
HISTORY_SQL = "SELECT * FROM comedy_event_reviews WHERE candidate_id=%s ORDER BY review_version DESC LIMIT 101"
OBSERVATION_HISTORY_SQL = """
SELECT o.*,d.decision,d.payload_fingerprint,d.policy_version,d.classifier_version,d.evidence
FROM comedy_event_observations o JOIN comedy_event_decisions d ON d.id=o.decision_id
WHERE o.candidate_id=%s ORDER BY o.generation DESC LIMIT 101
"""


QUEUE_SQL = """
WITH current_rows AS (
 SELECT c.id AS candidate_id,c.source_id,c.club_id,c.event_key,c.observation_generation,c.review_version,
  o.decision_id,o.baseline_identity_fingerprint AS identity_fingerprint,d.payload_fingerprint,d.policy_version,
  d.payload,d.evidence,d.decision,d.classifier_version,ss.comedy_policy_version AS current_policy_version,
  ss.comedy_gate_mode AS gate_mode,ss.enabled,ss.comedy_policy AS source_policy,cl.name AS club_name,ss.scraper_key,
  CASE WHEN o.decision_id IS NULL THEN 'awaiting_observation'
   WHEN d.policy_version<>ss.comedy_policy_version THEN 'stale_policy'
   WHEN c.review_version>0 AND (o.baseline_identity_fingerprint,d.payload_fingerprint,d.policy_version)
     IS DISTINCT FROM (r.identity_fingerprint,r.payload_fingerprint,r.policy_version) THEN 'stale_review'
   WHEN c.review_version>0 THEN r.action ELSE d.decision END AS status
 FROM comedy_event_candidates c JOIN clubs cl ON cl.id=c.club_id JOIN scraping_sources ss ON ss.id=c.source_id
 LEFT JOIN comedy_event_observations o ON o.candidate_id=c.id AND o.generation=c.observation_generation
 LEFT JOIN comedy_event_decisions d ON d.candidate_id=c.id AND d.id=o.decision_id
 LEFT JOIN comedy_event_reviews r ON r.candidate_id=c.id AND r.review_version=c.review_version
 WHERE c.id>%s AND c.id<=%s
), filters AS (SELECT %s::jsonb AS f)
SELECT current_rows.* FROM current_rows CROSS JOIN filters
WHERE (NOT f ? 'source_id' OR source_id=(f->>'source_id')::integer)
 AND (NOT f ? 'club_id' OR club_id=(f->>'club_id')::integer)
 AND (NOT f ? 'status' OR status=f->>'status')
 AND (NOT f ? 'decision' OR decision=f->>'decision')
 AND (NOT f ? 'coverage' OR evidence->>'lineup_status'=f->>'coverage')
 AND (NOT f ? 'reason' OR (evidence->'reason_codes') ? (f->>'reason'))
ORDER BY candidate_id LIMIT %s
"""
PUBLICATIONS_SQL = "SELECT * FROM comedy_event_publications WHERE candidate_id=%s ORDER BY published_at DESC LIMIT 101"


def _rows(cursor):
    columns = [c[0] for c in cursor.description]
    return [dict(row) if hasattr(row, "keys") else dict(zip(columns, row)) for row in cursor.fetchall()]


def load_review(cursor, source_id, event_key, payload_fingerprint, identity_fingerprint, policy_version):
    cursor.execute(LOAD_REVIEW_SQL, (source_id, event_key))
    row = _row(cursor)
    if row is None:
        return {"review_version": 0, "review": None, "stale": False}
    matches = row["id"] is not None and (row["payload_fingerprint"], row["identity_fingerprint"], row["policy_version"]) == (
        payload_fingerprint, identity_fingerprint, policy_version)
    return {"review_version": row["review_version"], "review": row if matches else None,
            "stale": bool(row["review_version"] and not matches)}


def _token(row):
    return {key: row[key] for key in ("candidate_id", "source_id", "observation_generation", "review_version",
                                     "decision_id", "payload_fingerprint", "identity_fingerprint", "policy_version", "gate_mode")}


def _state(row):
    if row["decision_id"] is None:
        return "awaiting_observation"
    if row["policy_version"] != row["current_policy_version"]:
        return "stale_policy"
    if row["review_version"]:
        if (row["identity_fingerprint"], row["payload_fingerprint"], row["policy_version"]) != (
                row["reviewed_identity_fingerprint"], row["reviewed_payload_fingerprint"], row["reviewed_policy_version"]):
            return "stale_review"
        return row["review_action"]
    return row["decision"]


class ReviewStore:
    def __init__(self, transaction, snapshot_validator=None):
        self.transaction = transaction
        self.snapshot_validator = snapshot_validator

    def list_queue(self, filters=None, after_id=0, ceiling_id=None, limit=50):
        filters = dict(filters or {})
        if "review_state" in filters:
            filters["status"] = filters.pop("review_state")
        if set(filters) - {"source_id", "club_id", "status", "decision", "reason", "coverage"}:
            raise ValueError("Unsupported queue filter")
        if type(limit) is not int or not 1 <= limit <= 100 or type(after_id) is not int or after_id < 0:
            raise ValueError("Invalid pagination bounds")
        if ceiling_id is not None and (type(ceiling_id) is not int or ceiling_id < after_id):
            raise ValueError("Invalid page ceiling")
        with self.transaction() as conn:
            with conn.cursor() as cur:
                if ceiling_id is None:
                    cur.execute("SELECT COALESCE(max(id),0) AS id FROM comedy_event_candidates")
                    ceiling_id = _row(cur)["id"]
                cur.execute(QUEUE_SQL, (after_id, ceiling_id, json.dumps(filters), limit+1))
                result = _rows(cur)
                has_more = len(result) > limit
                return {"items": result[:limit], "ceiling_id": ceiling_id,
                        "next_after_id": result[limit-1]["candidate_id"] if has_more else None}

    def detail(self, candidate_id):
        with self.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(CURRENT_SQL, (candidate_id,))
                current = _row(cur)
                if current is None:
                    raise ValueError("Candidate not found")
                current["status"] = _state(current)
                if current["decision_id"] is not None and self.snapshot_validator and self.snapshot_validator(cur, current) != current["identity_fingerprint"]:
                    current["status"] = "stale_identity"
                cur.execute(HISTORY_SQL, (candidate_id,))
                history = _rows(cur)
                cur.execute(OBSERVATION_HISTORY_SQL, (candidate_id,))
                observations = _rows(cur)
                cur.execute(PUBLICATIONS_SQL, (candidate_id,))
                publications = _rows(cur)
                return {"current": current, "history": history[:100], "observations": observations[:100],
                        "publications": publications[:100], "history_truncated": len(history)>100,
                        "observations_truncated": len(observations)>100, "publications_truncated": len(publications)>100}

    def preview(self, candidate_ids, action, reason, actor):
        if action not in {"approve", "reject", "defer"} or not isinstance(reason, str) or not reason.strip() or not isinstance(actor, str) or not actor.strip():
            raise ValueError("Action, actor and reason are required")
        if not candidate_ids or len(candidate_ids) > 100 or any(type(i) is not int or i <= 0 for i in candidate_ids):
            raise ValueError("Select 1–100 explicit positive candidate IDs")
        if len(set(candidate_ids)) != len(candidate_ids):
            raise ValueError("Duplicate candidate IDs")
        with self.transaction() as conn:
            with conn.cursor() as cur:
                items = []
                display = []
                for cid in sorted(candidate_ids):
                    cur.execute(CURRENT_SQL, (cid,))
                    row = _row(cur)
                    if not row or row["decision_id"] is None or not row["enabled"] or row["gate_mode"] == "off" or row["policy_version"] != row["current_policy_version"]:
                        raise ValueError("Candidate needs a current enabled-source observation")
                    if self.snapshot_validator is None or self.snapshot_validator(cur, row) != row["identity_fingerprint"]:
                        raise ValueError("Live identity changed; await a fresh observation")
                    items.append(_token(row))
                    display.append({**row, "status": _state(row)})
                pid = str(uuid4())
                digest = fingerprint({"preview_id": pid, "actor": actor, "action": action, "reason": reason, "items": items})
                cur.execute(INSERT_PREVIEW_SQL, (pid, actor, action, reason, json.dumps(items), digest))
                return {"preview_id": pid, "token_digest": digest, "items": items, "display": display, "action": action, "reason": reason, "actor": actor}

    def apply(self, preview_id, actor, idempotency_key, token_digest):
        if not isinstance(idempotency_key, str) or not idempotency_key.strip():
            raise ValueError("Idempotency key required")
        with self.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(LOAD_PREVIEW_SQL, (preview_id,))
                preview = _row(cur)
                if not preview or preview["actor"] != actor or preview["token_digest"] != token_digest:
                    raise ValueError("Preview actor or confirmation token mismatch")
                cur.execute(LOAD_OPERATION_SQL, (idempotency_key, preview_id))
                existing = _row(cur)
                if existing:
                    if (existing["idempotency_key"], existing["preview_id"], existing["actor"], existing["token_digest"]) != (idempotency_key, preview_id, actor, token_digest):
                        raise ValueError("Idempotency key or preview already used for another operation")
                    return existing["result"]
                if not preview["fresh"] or self.snapshot_validator is None:
                    raise ValueError("Preview expired or live identity validator unavailable")
                items = preview["items"]
                sources = {sid: load_source(cur, sid, lock=True) for sid in sorted({i["source_id"] for i in items})}
                for item in items:
                    cur.execute(CURRENT_SQL + " FOR UPDATE OF c", (item["candidate_id"],))
                    row = _row(cur)
                    if not row or _token(row) != item:
                        raise ValueError("Candidate changed since preview")
                    source = sources[item["source_id"]]
                    if not source or not source["enabled"] or source["comedy_policy_version"] != item["policy_version"] or source["comedy_gate_mode"] != item["gate_mode"] or source["comedy_gate_mode"] == "off":
                        raise ValueError("Source policy changed since preview")
                    if self.snapshot_validator(cur, row) != item["identity_fingerprint"]:
                        raise ValueError("Comedian identity evidence changed since preview")
                actions = [{**i, "review_version": i["review_version"]+1, "action": preview["action"]} for i in items]
                result = {"actions": actions, "preview_id": preview_id, "idempotency_key": idempotency_key}
                cur.execute(INSERT_OPERATION_SQL, (idempotency_key, preview_id, actor, token_digest, json.dumps(result)))
                for item in actions:
                    cur.execute(ADVANCE_REVIEW_SQL, (item["candidate_id"], item["review_version"]-1, item["observation_generation"]))
                    if _row(cur) is None:
                        raise ValueError("Concurrent review changed")
                    cur.execute(INSERT_REVIEW_SQL, (item["candidate_id"], item["observation_generation"], item["decision_id"],
                        item["review_version"], item["payload_fingerprint"], item["identity_fingerprint"], item["policy_version"],
                        actor, preview["reason"], preview["action"], idempotency_key))
                return result
