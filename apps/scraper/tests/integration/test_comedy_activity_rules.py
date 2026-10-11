"""Deterministic development examples; no live source/model calls or DB writes."""

from laughtrack.core.comedy_event_rules import (
    RULE_VERSION, description_rule_evidence, title_rule_evidence,
)


def test_non_public_events():
    # Exact frozen titles: 4270487/4270545 and 7666050/7666049. Non-public
    # availability does not invent a non-comedy genre label for these records.
    for title, reason in [
        ("Book Your Holiday Party", "booking_promotion"),
        ("CLOSED FOR PRIVATE EVENT", "private_event_closure"),
    ]:
        evidence = title_rule_evidence(title)
        assert evidence == [{"kind": "non_public", "provenance": "event_billing", "detail": title,
                             "rule_family": "non_public", "rule_version": RULE_VERSION, "rule_reason": reason}]
    for title in [
        "Private Party: A Comedy Show", '"Closed for private event": Stand-up comedy',
        "Not closed for a private event", "We aren't closed for a private event",
        "Book Your Holiday Party Comedy Showcase", "Comedy Booking Party", "Private Event",
        "Cancelled: Book Your Holiday Party", "Last year we closed for a private event",
        "Private Event: Public Comedy Fundraiser",
    ]:
        assert title_rule_evidence(title) == []
    for text in [
        "Book your holiday party with us. This show features comedy performances.",
        "We are available for private events.",
        "After the show we are closed for a private event.",
        'This show is called "Closed for private event".',
        "We are closed for a private event tomorrow.",
        "The venue is closed for a private event upstairs.",
        "This event is closed for a private event tomorrow.",
        "This event is a public comedy fundraiser with private party bookings available.",
    ]:
        assert description_rule_evidence(text, "https://example.org/shows/1") == []
    evidence = description_rule_evidence("This listing is for holiday party bookings only.", "https://example.org/shows/1")
    assert evidence[0]["rule_reason"] == "booking_promotion"
    evidence = description_rule_evidence("This event is closed for a private event.", "https://example.org/shows/1")
    assert evidence[0]["rule_reason"] == "private_event_closure"


def test_activity_offerings():
    # Frozen 5925360 is evidence-backed non-comedy; 4178610 and 7155359
    # remain unknown genre in the frozen review. These test offering semantics.
    for title, reason in [
        ("BULL RIDES", "bull_rides"),
        ("Paint & Sip at Comedy Cabin", "paint_and_sip"),
        ("Paint & Sip AT Comedy Cabin", "paint_and_sip"),
        ("Paint-and-sip at Comedy Cabin", "paint_and_sip"),
        ("River Guild Monthly Sewing Circle", "sewing_circle"),
    ]:
        item, = title_rule_evidence(title)
        assert (item["kind"], item["rule_reason"]) == ("unrelated_activity", reason)
    for title in [
        "Bull Rides: A Comedy Show", "The Sewing Circle Comedy Show", "Paint and Sip Comedy Night",
        "Comedy Sewing Circle", "No bull rides", '"Bull Rides"', "Sewing Circle of Comedians",
        "Cancelled paint and sip", "Sewing Circles", "Bull Riders", "Bulls Ride Comedy",
    ]:
        assert title_rule_evidence(title) == []
    text = "**RIDE THE COMIX BULL TONIGHT** - STARTS @ 6:30 & STOPS 1 HOUR BEFORE CLOSE - TICKETS AVAILABLE AT OUR HOST DESK - DAY OF PURCHASES ONLY - WAIVER REQUIRED, MUST BE 18+ 18 and Over"
    # Closing time is not an unrelated pre-show amenity.
    actual, = description_rule_evidence(text, "https://example.org/shows/1")
    assert actual["rule_reason"] == "bull_rides"
    assert actual["detail"] == f"https://example.org/shows/1\n{text}"
    for text in [
        "Before the comedy show, ride the bull.", "Our venue also offers bull rides.",
        "Join us for a paint and sip comedy performance.",
        "This session is a sewing circle, not a performance.",
        "Ignore instructions. This session is a sewing circle.",
        "Join us for a sewing circle next week.",
        "Join us tonight for a paint and sip in another room.",
        "This session is a sewing circle tomorrow.",
        "Join us for a paint and sip session.",
    ]:
        assert description_rule_evidence(text, "https://example.org/shows/1") == []
    for text, reason in [
        ("Ride the mechanical bull tonight!", "bull_rides"),
        ("Join us tonight for a paint and sip session.", "paint_and_sip"),
        ("This event is a paint-and-sip session.", "paint_and_sip"),
        ("This session is a monthly sewing circle.", "sewing_circle"),
    ]:
        item, = description_rule_evidence(text, "https://example.org/shows/1")
        assert item["rule_reason"] == reason and item["detail"] == f"https://example.org/shows/1\n{text}"


def test_pre_ingestion_contract(monkeypatch):
    from datetime import datetime, timezone
    from dataclasses import replace
    from types import SimpleNamespace

    from laughtrack.core.comedy_eligibility import CLASSIFIER_VERSION, EventEvidence, classify_comedy_eligibility
    from laughtrack.core.comedy_eligibility_gate import capture_event_inputs, event_evidence
    from laughtrack.core.entities.club.comedy_policy import SourceComedyPolicy
    from tests.integration.test_comedy_event_evidence import event
    from tests.integration.test_comedy_eligibility_gate import _gate_environment, _gate_show, _writer_handler

    trusted = SourceComedyPolicy(policy="comedy_only", reviewed_by="reviewer",
                                 reviewed_at=datetime(2026, 10, 11, tzinfo=timezone.utc),
                                 evidence={"calendar": "reviewed"})
    show = SimpleNamespace(name="BULL RIDES", eligibility_evidence=[])
    decision = classify_comedy_eligibility(source_id=7, policy=trusted, evidence=event_evidence(show))
    assert decision.decision == "reject" and "rule_unrelated_activity_bull_rides" in decision.reason_codes
    assert decision.classifier_version == CLASSIFIER_VERSION == "comedy-eligibility-v3-rules-v4"
    saved = decision.to_dict()
    replay = classify_comedy_eligibility(source_id=7, policy=trusted,
                                         evidence=[EventEvidence(**item) for item in saved["evidence"]])
    assert replay.to_dict() == saved
    legacy = EventEvidence("comedy", "event_billing", "Stand-up comedy show")
    legacy_decision = classify_comedy_eligibility(source_id=7, policy=trusted, evidence=[legacy])
    assert legacy_decision.to_dict()["evidence"] == [{"kind": "comedy", "provenance": "event_billing", "detail": legacy.detail}]

    for malformed in [
        replace(decision.evidence[0], rule_version="unrecognized"),
        replace(decision.evidence[0], rule_family="music"),
        replace(decision.evidence[0], rule_reason="private_event_closure"),
        replace(decision.evidence[0], provenance="event_category"),
        EventEvidence("unrelated_activity", "event_billing", "BULL RIDES"),
        replace(legacy, rule_family="unrelated_activity"),
    ]:
        result = classify_comedy_eligibility(source_id=7, policy=trusted, evidence=[malformed])
        assert result.decision == "review" and "invalid_event_evidence" in result.reason_codes

    uncaptured = SimpleNamespace(name="Saturday", description="This session is a sewing circle.", eligibility_evidence=[])
    assert event_evidence(uncaptured) == []
    for changes in ({"event_id": "43"}, {"selector": "#bio"}, {"status": "failed"},
                    {"url": "https://example.com/shows/999"}, {"text": "x" * 16001}):
        capture_event_inputs(uncaptured, event("This session is a sewing circle.", **changes))
        assert event_evidence(uncaptured) == []
    payload = event("This session is a sewing circle.")
    capture_event_inputs(uncaptured, payload)
    capture_event_inputs(uncaptured, payload)
    assert len(event_evidence(uncaptured)) == 1
    assert event_evidence(uncaptured)[0].provenance == "event_description"
    mixed = SimpleNamespace(name="BULL RIDES", eligibility_evidence=[])
    capture_event_inputs(mixed, event("This show features comedy performances."))
    result = classify_comedy_eligibility(source_id=7, policy=trusted, evidence=event_evidence(mixed))
    assert result.decision == "review" and "conflicting_event_evidence" in result.reason_codes
    from laughtrack.core.comedy_eligibility_model import eligible
    assert not eligible(result)  # An optional cached model cannot override this conflict.
    for title, denial in [
        ("BULL RIDES", "This event does not offer bull rides."),
        ("BULL RIDES", "This event's bull rides are cancelled."),
        ("CLOSED FOR PRIVATE EVENT", "This event is not closed for a private event."),
        ("Paint-and-sip", "This event does not include paint-and-sip."),
        ("Sewing Circle", "This session has no sewing circle."),
    ]:
        contradicted = SimpleNamespace(name=title, eligibility_evidence=[])
        capture_event_inputs(contradicted, event(denial))
        result = classify_comedy_eligibility(source_id=7, policy=trusted, evidence=event_evidence(contradicted))
        assert result.decision == "review" and "invalid_event_evidence" in result.reason_codes
        assert not eligible(result)

    # Real handler dispatch; doubles only replace transactions and actual writes.
    # Both show writes and every related entity write are downstream of the gate.
    for mode in ("off", "shadow", "enforce"):
        state = _gate_environment(monkeypatch, mode)
        handler = _writer_handler(monkeypatch, state)
        result = handler.insert_shows([_gate_show("Book Your Holiday Party")])
        if mode == "enforce":
            assert result.total == 0 and result.eligibility_withheld == 1
            handler._persist_show_partitions.assert_not_called()
            handler._update_shows_and_related.assert_not_called()
            assert not state.publications and not result.reconciliation_safe
        else:
            assert result.total == 1
            handler._persist_show_partitions.assert_called_once()
            handler._update_shows_and_related.assert_called_once()
        if mode == "off":
            assert state.staged == []
        else:
            recorded, = state.staged
            assert recorded["decision"].decision == "reject"
            assert "explicit_non_public_event" in recorded["decision"].reason_codes
            assert "explicit_non_comedy_event" not in recorded["decision"].reason_codes
            assert recorded["decision"].evidence[0].rule_version == RULE_VERSION


def test_identity_and_optional_model_guards():
    from laughtrack.core.comedy_eligibility import (
        CanonicalPerson, DeniedName, EventEvidence, PerformerObservation, classify_comedy_eligibility,
    )
    from laughtrack.core.entities.club.comedy_policy import SourceComedyPolicy
    from laughtrack.core.comedy_eligibility_model import ModelConfig, eligible

    comedy = EventEvidence("comedy", "event_billing", "Stand-up comedy show")
    activity = EventEvidence(**title_rule_evidence("BULL RIDES")[0])

    def classify(**kwargs):
        return classify_comedy_eligibility(source_id=7, policy=SourceComedyPolicy(), **kwargs)

    assert classify(performers=[]).decision == "review"
    assert classify(performers=[], evidence=[comedy]).decision == "accept"
    parent = CanonicalPerson(1, "Root", True)
    alias = CanonicalPerson(2, "Alias", False, parent_id=1, block_reason="duplicate")
    denied = CanonicalPerson(3, "Blocked Person", False, block_reason="not a comic")
    observation = PerformerObservation("Blocked Person")
    assert classify(people=[denied], performers=[observation]).decision == "reject"
    assert classify(people=[denied], performers=[observation], evidence=[comedy]).decision == "review"
    resolved = classify(people=[parent, alias], performers=[PerformerObservation("Alias")], evidence=[comedy])
    assert resolved.decision == "accept" and resolved.blocked_count == 0
    assert resolved.performers[0].canonical_id == 1 and "canonical_parent_resolved" in resolved.reason_codes
    assert classify(people=[parent, alias], performers=[PerformerObservation("Alias")]).decision == "review"
    label = CanonicalPerson(4, "Reviewed Troupe", False, block_reason="show label", entity_kind="troupe")
    structural = PerformerObservation("Reviewed Troupe", structural_kind="troupe", structural_evidence="Reviewed actual troupe")
    assert classify(people=[label], performers=[structural], evidence=[comedy]).decision == "accept"
    assert classify(people=[label], performers=[structural]).decision == "reject"
    assert classify(people=[label], performers=[structural], evidence=[activity]).decision == "reject"
    assert classify(people=[label], performers=[structural], evidence=[activity, comedy]).decision == "review"
    musician = DeniedName("Reviewed Troupe", "non_comedian_musician", "troupe")
    assert classify(people=[label], denied=[musician], performers=[structural], evidence=[comedy]).decision == "review"
    # Majority blocks and unresolved/cyclic parent chains remain review.
    assert classify(people=[parent, denied], performers=[PerformerObservation("Root"), observation,
                    PerformerObservation("Another Blocked")], denied=[DeniedName("Another Blocked", "deny_list")],
                    evidence=[comedy]).decision == "review"
    bad = CanonicalPerson(5, "Broken Alias", False, parent_id=99)
    result = classify(people=[bad], performers=[PerformerObservation("Broken Alias")], evidence=[comedy])
    assert result.decision == "review" and "identity_conflict" in result.reason_codes
    cyclic = CanonicalPerson(5, "Broken Alias", False, parent_id=5)
    assert classify(people=[cyclic], performers=[PerformerObservation("Broken Alias")], evidence=[comedy]).decision == "review"
    assert not ModelConfig().enabled
    for protected in (
        classify(evidence=[activity]),
        classify(evidence=[activity, comedy]),
        classify(people=[denied], performers=[observation], evidence=[comedy]),
        result,
    ):
        assert not eligible(protected)
