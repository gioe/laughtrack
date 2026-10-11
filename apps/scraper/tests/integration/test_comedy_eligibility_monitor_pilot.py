"""Synthetic boundary calibration, not a measured production accuracy result."""
from datetime import datetime, timedelta, timezone
import json

from laughtrack.core.comedy_eligibility import (
    CanonicalPerson, EventEvidence, PerformerObservation, classify_comedy_eligibility,
)
from laughtrack.core.comedy_eligibility_store import fingerprint
from laughtrack.core.entities.club.comedy_policy import SourceComedyPolicy


def _baseline(kind):
    kwargs = {}
    complete = True
    comedy = EventEvidence("comedy", "event_billing", "Stand-up comedy show")
    music = EventEvidence("music", "event_billing", "Live music concert")
    if kind == "comedy":
        kwargs["evidence"] = [comedy]
    elif kind == "music":
        kwargs["evidence"] = [music]
    elif kind in {"blocked", "partial_blocked", "conflicting_blocked"}:
        kwargs.update(people=[CanonicalPerson(1, "Example Band", False, block_reason="non_comedian_musician")],
                      performers=[PerformerObservation("Example Band")])
        complete = kind != "partial_blocked"
        if kind == "conflicting_blocked":
            kwargs["evidence"] = [comedy]
    elif kind == "rescued_parent":
        kwargs.update(people=[CanonicalPerson(1, "Alias", False, parent_id=2), CanonicalPerson(2, "Root", True)],
                      performers=[PerformerObservation("Alias")], evidence=[comedy])
    elif kind == "structural_exception":
        kwargs.update(people=[CanonicalPerson(1, "Example Troupe", False, block_reason="show label", entity_kind="troupe")],
                      performers=[PerformerObservation("Example Troupe", structural_kind="troupe", structural_evidence="Reviewed official troupe billing")],
                      evidence=[comedy])
    elif kind != "missing":
        raise ValueError(kind)
    result = classify_comedy_eligibility(source_id=7, policy=SourceComedyPolicy(), **kwargs).to_dict()
    if not complete:
        result["lineup_status"] = "partial"
    return {**result, "raw_lineup_complete": complete}


def _samples(kinds):
    rows = []
    for index, kind in enumerate(kinds):
        baseline = _baseline(kind)
        rows.append({"event_key": f"native:synthetic-{index}", "source_id": 7, "policy_version": 1,
                     "payload_fingerprint": fingerprint({"id": index, "kind": kind}),
                     "identity_fingerprint": fingerprint(baseline["performers"]), "baseline": baseline,
                     "last_seen_at": datetime(2026, 10, 11, tzinfo=timezone.utc)})
    return rows


def test_synthetic_pilot_boundary_matrix():
    from laughtrack.core.comedy_eligibility_monitor import MonitorConfig, recommendation, summarize_samples

    config = MonitorConfig()
    assert (config.window_days, config.min_events, config.min_rejections, config.rejection_fraction) == (30, 20, 5, 0.25)
    assert config.auto_downgrade is False
    cases = [
        ("19 events, all negative", ["blocked"] * 19, False),
        ("20 events, four negative", ["blocked"] * 4 + ["comedy"] * 16, False),
        ("20 events, five negative", ["blocked"] * 5 + ["comedy"] * 15, True),
        ("20 events, all missing lineups", ["missing"] * 20, False),
        ("20 blocked aliases with valid parents", ["rescued_parent"] * 20, False),
        ("20 incomplete blocked lineups", ["partial_blocked"] * 20, False),
        ("20 accepted structural exceptions", ["structural_exception"] * 20, False),
        ("20 positive and blocked conflicts", ["conflicting_blocked"] * 20, False),
        ("20 explicit music events without lineups", ["music"] * 20, True),
    ]
    transcript = []
    for name, kinds, expected in cases:
        metrics = summarize_samples(_samples(kinds))
        result = recommendation(metrics, config)
        assert result["downgrade"] is expected, (name, metrics, result)
        assert metrics["event_count"] == len(kinds)
        if kinds[0] == "rescued_parent":
            assert metrics["blocked_appearances"]["count"] == 0
        if kinds[0] in {"rescued_parent", "structural_exception", "partial_blocked"}:
            assert metrics["blocked_only_events"]["count"] == 0
        if kinds[0] == "partial_blocked":
            assert metrics["coverage"]["partial"]["count"] == 20
        transcript.append({"case": name, "events": metrics["event_count"], "downgrade_recommended": result["downgrade"]})
    print(json.dumps({"kind": "synthetic boundary verification, not production accuracy", "cases": transcript}, sort_keys=True))


def test_repeated_observations_do_not_satisfy_minimum_events():
    from laughtrack.core.comedy_eligibility_monitor import MonitorConfig, recommendation, summarize_samples

    rows = _samples(["blocked"])
    repeated = [{**rows[0], "last_seen_at": rows[0]["last_seen_at"] + timedelta(minutes=i)} for i in range(25)]
    metrics = summarize_samples(repeated)
    assert metrics["event_count"] == 1
    assert recommendation(metrics, MonitorConfig())["downgrade"] is False
