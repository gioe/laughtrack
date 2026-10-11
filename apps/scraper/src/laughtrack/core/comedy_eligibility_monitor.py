"""Source-level quality evidence, independent of trusted-source or model acceptance."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import os
from typing import cast

from laughtrack.core.comedy_eligibility import PerformerObservation, classify_comedy_eligibility, normalize_name
from laughtrack.core.comedy_eligibility_store import canonical_json, fingerprint, load_source
from laughtrack.core.entities.club.comedy_policy import SourceComedyPolicy
from laughtrack.foundation.infrastructure.logger.logger import Logger


@dataclass(frozen=True)
class MonitorConfig:
    window_days: int = 30
    min_events: int = 20
    min_rejections: int = 5
    rejection_fraction: float = 0.25
    auto_downgrade: bool = False

    def __post_init__(self):
        if any(type(v) is not int or v <= 0 for v in (self.window_days, self.min_events, self.min_rejections)):
            raise ValueError("Monitor window and minimum samples must be positive integers")
        if self.window_days > 365:
            raise ValueError("Monitor window must not exceed 365 days")
        if type(self.rejection_fraction) not in (int, float) or not 0 < self.rejection_fraction <= 1:
            raise ValueError("Rejection threshold must be within (0,1]")
        if type(self.auto_downgrade) is not bool:
            raise ValueError("Automatic downgrade flag must be boolean")

    @classmethod
    def from_env(cls):
        return cls(
            window_days=int(os.getenv("COMEDY_MONITOR_WINDOW_DAYS", "30")),
            min_events=int(os.getenv("COMEDY_MONITOR_MIN_EVENTS", "20")),
            min_rejections=int(os.getenv("COMEDY_MONITOR_MIN_REJECTIONS", "5")),
            rejection_fraction=float(os.getenv("COMEDY_MONITOR_REJECTION_FRACTION", ".25")),
            auto_downgrade=os.getenv("COMEDY_MONITOR_AUTO_DOWNGRADE", "0") == "1",
        )


def _latest(samples):
    latest: dict[tuple, tuple[tuple[str, str], dict]] = {}
    for sample in samples:
        key = (sample.get("source_id"), sample["event_key"])
        stamp = sample.get("last_seen_at") or ""
        if isinstance(stamp, datetime):
            stamp = stamp.astimezone(timezone.utc).isoformat()
        order = (str(stamp), canonical_json(sample.get("baseline", {})))
        previous = latest.get(key)
        if previous is None or order > previous[0]:
            latest[key] = (order, sample)
    return [value[1] for _, value in sorted(latest.items(), key=lambda pair: str(pair[0]))]


def _ratio(count, denominator):
    return {"count": count, "denominator": denominator, "fraction": count / denominator if denominator else None}


def summarize_samples(samples):
    rows = _latest(samples)
    total = len(rows)
    decisions = {key: 0 for key in ("accept", "reject", "review")}
    coverage = {key: 0 for key in ("missing", "partial", "observed")}
    resolved_count = blocked_count = blocked_only = with_lineup = strong_rejections = 0
    performer_count = unresolved_count = 0
    for row in rows:
        baseline = row.get("baseline") or {}
        verdict = baseline.get("decision", "review")
        decisions[verdict if verdict in decisions else "review"] += 1
        status = baseline.get("lineup_status", "missing")
        coverage[status if status in coverage else "missing"] += 1
        performers = baseline.get("performers") or []
        with_lineup += bool(performers)
        performer_count += len(performers)
        unresolved_count += sum(p.get("state") not in {"blocked", "unblocked"} for p in performers)
        resolved_count += sum(p.get("state") in {"blocked", "unblocked"} for p in performers)
        blocked_count += sum(p.get("state") == "blocked" for p in performers)
        fully_blocked = (
            bool(performers)
            and bool(baseline.get("raw_lineup_complete"))
            and all(p.get("state") == "blocked" for p in performers)
            and not (verdict == "accept" and "structural_label_exception" in baseline.get("reason_codes", []))
        )
        blocked_only += fully_blocked
        strong_rejections += verdict == "reject" and (
            "explicit_non_comedy_event" in baseline.get("reason_codes", []) or fully_blocked
        )
    return {
        "event_count": total,
        "strong_rejections": _ratio(strong_rejections, total),
        "decisions": {key: _ratio(value, total) for key, value in decisions.items()},
        "coverage": {
            **{key: _ratio(value, total) for key, value in coverage.items()},
            "with_lineup": _ratio(with_lineup, total),
        },
        "blocked_appearances": _ratio(blocked_count, resolved_count),
        "unresolved_appearances": _ratio(unresolved_count, performer_count),
        "blocked_only_events": _ratio(blocked_only, with_lineup),
    }


def recommendation(metrics, config: MonitorConfig):
    reasons = []
    if metrics["event_count"] == 0:
        reasons.append("no_observations_telemetry_gap")
    rejections = metrics["strong_rejections"]
    if metrics["event_count"] < config.min_events:
        reasons.append("insufficient_distinct_events")
    if rejections["count"] < config.min_rejections:
        reasons.append("insufficient_strong_rejections")
    if (rejections["fraction"] or 0) < config.rejection_fraction:
        reasons.append("rejection_fraction_below_threshold")
    return {"downgrade": not reasons, "reasons": reasons or ["sustained_non_comedy_evidence"]}


def evidence_digest(samples) -> str:
    # Exclude timestamps, source-policy revision and trust so an operator rollback
    # does not cause unchanged bad evidence to immediately downgrade again.
    content = []
    for row in _latest(samples):
        baseline = dict(row.get("baseline") or {})
        for key in ("source_id", "policy", "policy_version"):
            baseline.pop(key, None)
        content.append(
            {
                "event_key": row["event_key"],
                "payload": row.get("payload_fingerprint"),
                "identity": row.get("identity_fingerprint"),
                "baseline": baseline,
            }
        )
    return cast(str, fingerprint(content))


def observe_show(cursor, source, show, identity_snapshots=None):
    """Best-effort independent baseline inside a savepoint, never an admission rule.

    All gated sources and comedy_only/off sources call this before public writes.
    Monitoring outages are visible but cannot stop an off source's legacy ingest.
    """
    from laughtrack.core.comedy_eligibility_gate import _identity_snapshot, candidate_payload, event_evidence, event_key
    from laughtrack.core.comedy_eligibility_monitor_store import record_sample
    from laughtrack.core.comedy_eligibility_review import baseline_identity_fingerprint

    try:
        cursor.execute("SAVEPOINT comedy_monitor_observation")
        names = sorted(
            {normalize_name(n) for n in (show.eligibility_performer_names or []) if isinstance(n, str) and n.strip()}
        )
        snapshots = identity_snapshots if identity_snapshots is not None else {}
        if tuple(names) not in snapshots:
            snapshots[tuple(names)] = _identity_snapshot(cursor, names)
        people, denied = snapshots[tuple(names)]
        baseline = classify_comedy_eligibility(
            source_id=source["id"],
            policy=SourceComedyPolicy(version=source["comedy_policy_version"]),
            evidence=event_evidence(show),
            performers=[PerformerObservation(n) for n in names],
            people=people,
            denied=denied,
        )
        if names and not show.eligibility_raw_performers_preserved:
            baseline = replace(baseline, lineup_status="partial")
            if baseline.decision == "reject" and "explicit_non_comedy_event" not in baseline.reason_codes:
                baseline = replace(
                    baseline,
                    decision="review",
                    confidence=0.3,
                    reason_codes=tuple(sorted((*baseline.reason_codes, "partial_blocked_evidence"))),
                )
        record_sample(
            cursor,
            source_id=source["id"],
            event_key=event_key(show),
            payload_fingerprint=fingerprint(candidate_payload(show)),
            identity_fingerprint=baseline_identity_fingerprint(baseline, people, denied),
            baseline={**baseline.to_dict(), "raw_lineup_complete": show.eligibility_raw_performers_preserved},
            policy_version=source["comedy_policy_version"],
        )
        cursor.execute("RELEASE SAVEPOINT comedy_monitor_observation")
        return True
    except Exception as exc:
        cursor.execute("ROLLBACK TO SAVEPOINT comedy_monitor_observation")
        cursor.execute("RELEASE SAVEPOINT comedy_monitor_observation")
        Logger.warn(f"Comedy monitoring observation unavailable for source {source['id']}: {type(exc).__name__}")
        return False


def evaluate_source(store, source_id, config=None, *, apply=None):
    config = config or MonitorConfig.from_env()
    snapshot = store.load_snapshot(source_id, config.window_days)
    metrics = summarize_samples(snapshot["samples"])
    advised = recommendation(metrics, config)
    report = store.record_report(
        source_id,
        evidence_digest=evidence_digest(snapshot["samples"]),
        config=asdict(config),
        metrics=metrics,
        recommendation=advised,
        expected_version=snapshot["source"]["comedy_policy_version"],
        apply=config.auto_downgrade if apply is None else apply,
    )
    if report.get("new_report"):
        Logger.info(
            f"Comedy quality source {source_id}: {metrics['strong_rejections']['count']}/"
            f"{metrics['event_count']} strong rejections; {','.join(advised['reasons'])}"
        )
    return {
        "source_id": source_id,
        "metrics": metrics,
        "recommendation": advised,
        "window": {"days": config.window_days, "as_of": snapshot.get("as_of"), "since": snapshot.get("window_start")},
        **report,
    }


def evaluate_completed_source(transaction, source_id):
    """Run after publication/reconciliation transactions have closed; errors remain reports."""
    if source_id is None:
        return None
    try:
        with transaction() as connection:
            with connection.cursor() as cursor:
                source = load_source(cursor, source_id)
        if (
            not source
            or not source["enabled"]
            or (source["comedy_policy"] != "comedy_only" and source["comedy_gate_mode"] == "off")
        ):
            return None
        from laughtrack.core.comedy_eligibility_monitor_store import MonitorStore

        return evaluate_source(MonitorStore(transaction), source_id)
    except Exception as exc:
        Logger.warn(f"Comedy quality evaluation unavailable for source {source_id}: {type(exc).__name__}")
        return None
