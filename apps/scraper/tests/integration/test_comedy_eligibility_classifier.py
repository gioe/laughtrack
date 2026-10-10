"""Pure pre-entity admission contracts: fixtures are synthetic, never live listings."""

from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from laughtrack.core.comedy_eligibility import (
    CLASSIFIER_VERSION,
    CanonicalPerson,
    DeniedName,
    EventEvidence,
    PerformerObservation,
    classify_comedy_eligibility,
)
from laughtrack.core.entities.club.comedy_policy import SourceComedyPolicy

COMEDY = EventEvidence("comedy", "event_category", "Platform labels this event Comedy")
MUSIC = EventEvidence("music", "event_category", "Platform labels this event Live Music")
SPORTS = EventEvidence("sports", "event_billing", "Boxing championship")


def classify(**kwargs):
    return classify_comedy_eligibility(source_id=42, policy=kwargs.pop("policy", SourceComedyPolicy()), **kwargs)


def trusted():
    return SourceComedyPolicy(
        policy="comedy_only",
        reviewed_by="operator",
        reviewed_at=datetime(2026, 10, 10, tzinfo=timezone.utc),
        evidence={"calendar_review": "Comedy-only bookings"},
    )


def test_contract_1():
    assert classify(evidence=[COMEDY]).decision == "accept"
    assert classify(evidence=[MUSIC]).decision == "reject"
    assert classify(evidence=[SPORTS], policy=trusted()).decision == "reject"
    assert classify(evidence=[COMEDY, MUSIC]).decision == "review"
    assert classify().decision == "review"
    assert classify(policy=SourceComedyPolicy(policy="mixed")).decision == "review"
    assert classify(policy=SourceComedyPolicy(policy="mixed"), evidence=[COMEDY]).decision == "accept"
    assert classify(policy=trusted()).decision == "accept"
    for metadata in ({"reviewed_at": None}, {"reviewed_at": "invalid"}, {"reviewed_by": " "}, {"evidence": {}}):
        assert classify(policy=replace(trusted(), **metadata)).decision == "review"
    for evidence in (
        EventEvidence("comedy", "venue_name", "Comedy Cellar"),
        EventEvidence("comedy", "event_category", " "),
        EventEvidence("dance", "event_category", "dance"),
    ):
        result = classify(evidence=[COMEDY, evidence])
        assert result.decision == "review"
        assert "invalid_event_evidence" in result.reason_codes
        assert {
            "kind": evidence.kind,
            "provenance": evidence.provenance,
            "detail": evidence.detail,
        } in result.to_dict()["evidence"]
        assert result.to_dict() == classify(evidence=[evidence, COMEDY, evidence]).to_dict()
    result = classify(evidence=[COMEDY], policy=replace(trusted(), version=17))
    output = result.to_dict()
    assert output["source_id"] == 42 and output["policy_version"] == 17
    assert output["classifier_version"] == CLASSIFIER_VERSION
    assert 0 <= output["confidence"] <= 1
    assert output == json.loads(json.dumps(output))
    assert result.to_dict() == classify(evidence=[COMEDY, COMEDY], policy=replace(trusted(), version=17)).to_dict()
    for gate in ("off", "shadow", "enforce"):
        assert classify(evidence=[COMEDY], policy=replace(trusted(), gate_mode=gate)).decision == "accept"


def test_contract_2():
    people = [
        CanonicalPerson(1, "Root", True),
        CanonicalPerson(2, "Alias", False, 1, "duplicate"),
        CanonicalPerson(3, "Musician", False, block_reason="not a comic"),
    ]
    result = classify(
        evidence=[COMEDY],
        people=people,
        performers=[PerformerObservation("Alias"), PerformerObservation("Root"), PerformerObservation("Alias", 2)],
    )
    assert result.decision == "accept" and result.performer_count == 1 and result.blocked_count == 0
    assert result.performers[0].canonical_id == 1
    assert "canonical_parent_resolved" in result.reason_codes
    assert "duplicate" in result.performers[0].block_reasons
    rescued_without_comedy = classify(people=people, performers=[PerformerObservation("Alias")])
    assert rescued_without_comedy.decision == "review"
    assert rescued_without_comedy.blocked_count == 0
    assert "database_membership_not_comedy_evidence" in rescued_without_comedy.reason_codes
    blocked = classify(people=people, performers=[PerformerObservation("Musician")])
    assert blocked.decision == "reject" and "blocked_only_lineup" in blocked.reason_codes
    assert (
        classify(evidence=[COMEDY], people=people, performers=[PerformerObservation("Musician")]).decision == "review"
    )
    for person, extra in [
        (CanonicalPerson(4, "Child", False, 3), []),
        (CanonicalPerson(4, "Child", False, 1), [DeniedName("Root", "not a comic")]),
    ]:
        result = classify(people=people + [person], denied=extra, performers=[PerformerObservation("Child")])
        assert result.decision == "reject"
    for bad in (
        [CanonicalPerson(4, "Bad", False, 99)],
        [CanonicalPerson(4, "Bad", False, 5), CanonicalPerson(5, "Loop", True, 4)],
        [CanonicalPerson(4, "Same", False), CanonicalPerson(5, "Same", True)],
    ):
        result = classify(people=bad, performers=[PerformerObservation(bad[0].name)])
        assert result.decision == "review" and "identity_conflict" in result.reason_codes
        music_result = classify(evidence=[MUSIC], people=bad, performers=[PerformerObservation(bad[0].name)])
        assert music_result.decision == "reject" and "identity_conflict" in music_result.reason_codes
    result = classify(
        people=people + [CanonicalPerson(4, "Band", False)],
        performers=[PerformerObservation("Root"), PerformerObservation("Musician"), PerformerObservation("Band")],
        evidence=[COMEDY],
    )
    assert result.decision == "review" and "majority_blocked_lineup" in result.reason_codes
    assert result.blocked_count == 2 and result.performer_count == 3
    result = classify(
        people=people, performers=[PerformerObservation("Root"), PerformerObservation("Musician")], evidence=[COMEDY]
    )
    assert "majority_blocked_lineup" not in result.reason_codes
    for observations, snapshots in (
        ([PerformerObservation("Wrong name", 1)], people),
        ([PerformerObservation("Missing", 99)], people),
        ([PerformerObservation("Root", 1)], people + [CanonicalPerson(1, "Root", False)]),
    ):
        result = classify(people=snapshots, performers=observations, evidence=[COMEDY])
        assert result.decision == "review" and "identity_conflict" in result.reason_codes
    # Resolution cache belongs to one invocation; hiding the root changes the next result.
    result = classify(people=[replace(people[0], visible=False), people[1]], performers=[PerformerObservation("Alias")])
    assert result.decision == "reject"


def test_contract_3():
    musician = CanonicalPerson(1, "Unverified Musician", True)
    assert classify(people=[musician], performers=[PerformerObservation(musician.name)]).decision == "review"
    assert (
        classify(people=[musician], performers=[PerformerObservation(musician.name)], evidence=[MUSIC]).decision
        == "reject"
    )
    for lineup in (None, []):
        result = classify(performers=lineup)
        assert result.lineup_status == "missing" and result.performer_count == 0
        assert "missing_lineup" in result.reason_codes
    unknown = classify(performers=[PerformerObservation("New Performer")])
    assert unknown.lineup_status == "partial" and unknown.decision == "review"
    denied = [DeniedName(" New Musician ", "non_comedian_musician")]
    raw = classify(
        performers=[PerformerObservation("NEW\xa0 MUSICIAN"), PerformerObservation("New Musician")], denied=denied
    )
    assert raw.decision == "reject" and raw.performer_count == 1
    label = CanonicalPerson(2, "The Second City", False, block_reason="show label", entity_kind="troupe")
    observation = PerformerObservation(
        label.name, structural_kind="troupe", structural_evidence="Reviewed official troupe billing"
    )
    assert classify(people=[label], performers=[observation]).decision == "reject"
    accepted = classify(people=[label], performers=[observation], evidence=[COMEDY])
    assert accepted.decision == "accept" and "structural_label_exception" in accepted.reason_codes
    assert accepted.performers[0].structural_evidence
    for bad_observation in (
        replace(observation, structural_evidence=None),
        replace(observation, structural_kind="show_label"),
    ):
        assert classify(people=[label], performers=[bad_observation], evidence=[COMEDY]).decision == "review"
    # Claiming an actual blocked person is a troupe cannot override snapshot type.
    spoof = replace(label, entity_kind="person", block_reason="non_comedian_musician")
    assert classify(people=[spoof], performers=[observation], evidence=[COMEDY]).decision == "review"
    conflicting_label = replace(label, block_reason="non_comedian_musician")
    assert classify(people=[conflicting_label], performers=[observation], evidence=[COMEDY]).decision == "review"
    musician = CanonicalPerson(3, "Blocked Musician", False)
    mixed = classify(
        people=[label, musician], performers=[observation, PerformerObservation(musician.name)], evidence=[COMEDY]
    )
    assert mixed.decision == "review" and "structural_label_exception" not in mixed.reason_codes
    assert classify(people=[label], performers=[observation], evidence=[COMEDY, MUSIC]).decision == "review"


@pytest.mark.parametrize(
    "case",
    json.loads((Path(__file__).parent / "fixtures/comedy_eligibility_cases.json").read_text()),
    ids=lambda c: c["name"],
)
def test_representative_fixture(case):
    result = classify(
        evidence=[EventEvidence(**e) for e in case["evidence"]],
        people=[CanonicalPerson(**p) for p in case.get("people", [])],
        performers=[PerformerObservation(**p) for p in case.get("performers", [])],
    )
    assert result.decision == case["expected"]
    assert case["reason"] in result.reason_codes
