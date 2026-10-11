"""Durable source-quality observations and reversible, explicitly enabled actions."""
from dataclasses import asdict
from datetime import timedelta
import json

from laughtrack.core.comedy_eligibility_store import _row, fingerprint, LOAD_SOURCE_SQL
from laughtrack.core.entities.club.comedy_policy import SourceComedyPolicy, save_source_comedy_policy

RECORD_SAMPLE_SQL = """
INSERT INTO comedy_source_samples(source_id,event_key,payload_fingerprint,identity_fingerprint,baseline,policy_version)
SELECT id,%s,%s,%s,%s::jsonb,%s FROM scraping_sources WHERE id=%s AND enabled=true
 AND comedy_policy_version=%s
ON CONFLICT(source_id,event_key) DO UPDATE SET payload_fingerprint=EXCLUDED.payload_fingerprint,
 identity_fingerprint=EXCLUDED.identity_fingerprint,baseline=EXCLUDED.baseline,
 policy_version=EXCLUDED.policy_version,last_seen_at=clock_timestamp()
RETURNING source_id
"""
SAMPLES_SQL = """
WITH boundary AS MATERIALIZED (SELECT clock_timestamp() AS as_of)
SELECT samples.* FROM comedy_source_samples samples CROSS JOIN boundary WHERE source_id=%s
 AND last_seen_at>=as_of-(%s * interval '1 day') AND last_seen_at<=as_of ORDER BY event_key
"""
SAMPLES_AT_SQL = """
SELECT * FROM comedy_source_samples WHERE source_id=%s
 AND last_seen_at<=%s::timestamptz AND last_seen_at>=%s::timestamptz-(%s * interval '1 day') ORDER BY event_key
"""
INSERT_REPORT_SQL = """
INSERT INTO comedy_source_reports(source_id,report_digest,evidence_digest,config,metrics,recommendation,source_snapshot)
VALUES(%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb)
ON CONFLICT(source_id,report_digest) DO NOTHING RETURNING id
"""
FIND_REPORT_SQL = "SELECT id FROM comedy_source_reports WHERE source_id=%s AND report_digest=%s"
SUPPRESSED_SQL = """
SELECT EXISTS(SELECT 1 FROM comedy_source_transitions undone
 JOIN comedy_source_transitions original ON original.id=undone.rollback_of
 JOIN comedy_source_reports r ON r.id=original.report_id
 WHERE undone.kind='rollback' AND undone.source_id=%s AND r.evidence_digest=%s) AS suppressed
"""
EXISTING_TRANSITION_SQL = "SELECT * FROM comedy_source_transitions WHERE report_id=%s AND kind='downgrade'"
INSERT_TRANSITION_SQL = """
INSERT INTO comedy_source_transitions(source_id,report_id,kind,rollback_of,actor,reason,before_state,after_state)
VALUES(%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb) RETURNING *
"""
LOAD_TRANSITION_SQL = "SELECT * FROM comedy_source_transitions WHERE id=%s"
ROLLBACK_EXISTING_SQL = "SELECT * FROM comedy_source_transitions WHERE rollback_of=%s"


def _json(value):
    return json.dumps(value, sort_keys=True, default=str, allow_nan=False)


def _rows(cursor):
    columns = [c[0] for c in cursor.description]
    return [dict(row) if hasattr(row, "keys") else dict(zip(columns, row)) for row in cursor.fetchall()]


def record_sample(cursor, *, source_id, event_key, payload_fingerprint, identity_fingerprint, baseline, policy_version):
    if not event_key or not isinstance(baseline, dict):
        raise ValueError("Monitor sample needs an event key and baseline evidence")
    cursor.execute(LOAD_SOURCE_SQL + " FOR SHARE OF ss", (source_id,))
    source = _row(cursor)
    if not source or not source["enabled"] or source["comedy_policy_version"] != policy_version:
        raise ValueError("Monitor source changed")
    cursor.execute(RECORD_SAMPLE_SQL, (event_key, payload_fingerprint, identity_fingerprint, _json(baseline),
                                      policy_version, source_id, policy_version))
    if _row(cursor) is None:
        raise ValueError("Monitor source disabled, missing or policy changed")


def _policy_snapshot(source):
    return {"policy": source["comedy_policy"], "gate_mode": source["comedy_gate_mode"],
            "version": source["comedy_policy_version"], "reviewed_by": source["comedy_reviewed_by"],
            "reviewed_at": source["comedy_reviewed_at"], "evidence": source["comedy_review_evidence"]}


class MonitorStore:
    def __init__(self, transaction):
        self.transaction = transaction

    def sources(self):
        with self.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(LOAD_SOURCE_SQL.replace("WHERE ss.id = %s", "WHERE ss.enabled=true ORDER BY ss.id"))
                return _rows(cur)

    def load_snapshot(self, source_id, days):
        if type(days) is not int or not 1<=days<=365:
            raise ValueError("Window must be 1–365 days")
        with self.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(LOAD_SOURCE_SQL, (source_id,))
                source = _row(cur)
                if source is None:
                    raise ValueError("Source not found")
                cur.execute("SELECT clock_timestamp() AS as_of")
                as_of = _row(cur)["as_of"]
                cur.execute(SAMPLES_AT_SQL, (source_id, as_of, as_of, days))
                return {"source": source, "samples": _rows(cur), "as_of": as_of, "window_start": as_of-timedelta(days=days)}

    def record_report(self, source_id, *, evidence_digest, config, metrics, recommendation, expected_version, apply=False):
        if not isinstance(recommendation, dict) or type(recommendation.get("downgrade")) is not bool:
            raise ValueError("Monitor recommendation requires an explicit downgrade boolean")
        digest = fingerprint({"evidence": evidence_digest, "config": config, "recommendation": recommendation})
        with self.transaction() as conn:
            with conn.cursor() as cur:
                # Source always precedes history locks; never upgrade a shared lock.
                cur.execute(LOAD_SOURCE_SQL + " FOR UPDATE OF ss", (source_id,))
                source = _row(cur)
                if source is None or source["comedy_policy_version"] != expected_version:
                    raise ValueError("Source policy changed since monitor snapshot")
                from laughtrack.core.comedy_eligibility_monitor import evidence_digest as current_digest
                from laughtrack.core.comedy_eligibility_monitor import MonitorConfig, summarize_samples, recommendation as evaluate
                cur.execute("SELECT clock_timestamp() AS as_of")
                as_of = _row(cur)["as_of"]
                cur.execute(SAMPLES_AT_SQL, (source_id, as_of, as_of, config["window_days"]))
                current_samples = _rows(cur)
                if current_digest(current_samples) != evidence_digest:
                    raise ValueError("Monitor evidence changed since snapshot; reload before applying")
                if summarize_samples(current_samples) != metrics or evaluate(metrics, MonitorConfig(**config)) != recommendation:
                    raise ValueError("Monitor metrics or recommendation do not match current evidence")
                before = _policy_snapshot(source)
                report_snapshot = {**before, "window": {"as_of": str(as_of),
                    "since": str(as_of-timedelta(days=config["window_days"]))},
                    "negative_examples": [{"event_key": sample["event_key"], "payload_fingerprint": sample["payload_fingerprint"],
                        "identity_fingerprint": sample["identity_fingerprint"], "reason_codes": sample["baseline"].get("reason_codes",[])}
                        for sample in current_samples if sample["baseline"].get("decision")=="reject"][:5]}
                cur.execute(INSERT_REPORT_SQL, (source_id,digest,evidence_digest,_json(config),_json(metrics),
                                               _json(recommendation),_json(report_snapshot)))
                report = _row(cur)
                created = report is not None
                if report is None:
                    cur.execute(FIND_REPORT_SQL, (source_id,digest))
                    report = _row(cur)
                result = {"report_id": report["id"], "created": created, "new_report": created, "transition": None, "reason": "report_only"}
                cur.execute(SUPPRESSED_SQL, (source_id,evidence_digest))
                if _row(cur)["suppressed"]:
                    result["reason"] = "rollback_suppressed_same_evidence"
                    return result
                if not apply or not recommendation["downgrade"]:
                    return result
                if not source["enabled"] or source["comedy_policy"] != "comedy_only":
                    result["reason"] = "source_not_enabled_comedy_only"
                    return result
                cur.execute(EXISTING_TRANSITION_SQL, (report["id"],))
                existing = _row(cur)
                if existing:
                    result.update(transition=existing,reason="already_applied")
                    return result
                reason = "; ".join(map(str,recommendation.get("reasons",[]))) or "Unsafe source quality threshold"
                new = SourceComedyPolicy(policy="mixed",gate_mode="enforce",version=expected_version,
                    reviewed_by="comedy_quality_monitor",evidence={"report_id":report["id"],"evidence_digest":evidence_digest,"reason":reason})
                after = asdict(save_source_comedy_policy(cur,source_id,new))
                cur.execute(INSERT_TRANSITION_SQL,(source_id,report["id"],"downgrade",None,"comedy_quality_monitor",reason,_json(before),_json(after)))
                result.update(transition=_row(cur),reason="downgraded")
                return result

    def history(self, source_id):
        with self.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM comedy_source_reports WHERE source_id=%s ORDER BY id DESC LIMIT 101",(source_id,))
                reports = _rows(cur)
                cur.execute("SELECT * FROM comedy_source_transitions WHERE source_id=%s ORDER BY id DESC LIMIT 101",(source_id,))
                transitions = _rows(cur)
                return {"reports":reports[:100],"transitions":transitions[:100],"reports_truncated":len(reports)>100,
                        "transitions_truncated":len(transitions)>100}

    def rollback(self, transition_id, *, expected_version, actor, reason):
        if not isinstance(actor,str) or not actor.strip() or not isinstance(reason,str) or not reason.strip():
            raise ValueError("Rollback requires actor and reason")
        with self.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(LOAD_TRANSITION_SQL,(transition_id,))
                transition = _row(cur)
                if not transition or transition["kind"]!="downgrade":
                    raise ValueError("Rollback requires a downgrade transition")
                sid = transition["source_id"]
                cur.execute(LOAD_SOURCE_SQL + " FOR UPDATE OF ss",(sid,))
                source = _row(cur)
                cur.execute(ROLLBACK_EXISTING_SQL,(transition_id,))
                if _row(cur):
                    raise ValueError("Transition already rolled back")
                if not source or source["comedy_policy_version"]!=expected_version or expected_version!=transition["after_state"]["version"]:
                    raise ValueError("Policy changed after transition; rollback refused")
                original = transition["before_state"]
                restored = SourceComedyPolicy(policy=original["policy"],gate_mode=original["gate_mode"],version=expected_version,
                    reviewed_by=actor,evidence={"rollback_of":transition_id,"reason":reason,"original_review":original})
                after = asdict(save_source_comedy_policy(cur,sid,restored))
                cur.execute(INSERT_TRANSITION_SQL,(sid,transition["report_id"],"rollback",transition_id,actor,reason,
                                                  _json(_policy_snapshot(source)),_json(after)))
                return _row(cur)
