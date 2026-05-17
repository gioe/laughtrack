from __future__ import annotations

from laughtrack.core.podcast_appearance_auto_acceptance import (
    AutoAcceptanceCandidate,
    apply_auto_acceptance_rules,
    build_spot_check_sample,
)


def _candidate(**overrides) -> AutoAcceptanceCandidate:
    values = {
        "candidate_id": 10,
        "comedian_id": 12,
        "comedian_name": "Ari Shaffir",
        "podcast_title": "Comedy Talk",
        "podcast_author": "",
        "episode_title": "Ari Shaffir on the road",
        "role_guess": "guest",
        "confidence": 0.97,
        "source": "podcast_index",
        "source_field": "title",
        "evidence_text": "Ari Shaffir",
        "evidence": {},
        "host_association_types": [],
    }
    values.update(overrides)
    return AutoAcceptanceCandidate(**values)


def test_high_confidence_title_match_is_auto_accepted_with_rule_audit():
    result = apply_auto_acceptance_rules(_candidate())

    assert result.status == "accepted"
    assert result.rule_id == "high_confidence_title_name"
    assert result.evidence["auto_acceptance"]["rule_id"] == "high_confidence_title_name"
    assert result.evidence["auto_acceptance"]["status"] == "accepted"
    assert result.evidence["auto_acceptance"]["sample_eligible"] is True


def test_existing_host_relationship_is_auto_accepted_as_host():
    result = apply_auto_acceptance_rules(
        _candidate(
            episode_title="Weekly update",
            role_guess="host",
            confidence=0.88,
            source_field="podcast_relationship",
            evidence_text="Ari Shaffir",
            host_association_types=["host"],
        )
    )

    assert result.status == "accepted"
    assert result.rule_id == "accepted_host_relationship"
    assert result.evidence["auto_acceptance"]["rule_id"] == "accepted_host_relationship"


def test_podcast_index_guid_match_is_high_trust_source_rule():
    result = apply_auto_acceptance_rules(
        _candidate(
            confidence=0.71,
            source_field="metadata",
            evidence={"guid_match": True},
        )
    )

    assert result.status == "accepted"
    assert result.rule_id == "podcast_index_guid_match"


def test_low_signal_mentions_are_ignored_to_keep_manual_queue_focused():
    result = apply_auto_acceptance_rules(
        _candidate(
            episode_title="Network update",
            role_guess="mention",
            confidence=0.43,
            source_field="description",
            evidence_text="Ari Shaffir",
        )
    )

    assert result.status == "ignored"
    assert result.rule_id == "low_signal_mention"
    assert result.evidence["auto_acceptance"]["status"] == "ignored"


def test_ambiguous_near_threshold_guest_stays_pending():
    result = apply_auto_acceptance_rules(
        _candidate(
            comedian_name="Ari",
            episode_title="Ari on the road",
            confidence=0.94,
            evidence_text="Ari",
        )
    )

    assert result.status == "pending"
    assert result.rule_id is None
    assert "auto_acceptance" not in result.evidence


def test_spot_check_sample_is_deterministic_and_about_two_percent():
    rows = [
        _candidate(candidate_id=i, evidence={"auto_acceptance": {"rule_id": "high_confidence_title_name"}})
        for i in range(1, 201)
    ]

    sample = build_spot_check_sample(rows, sample_rate=0.02)

    assert [row.candidate_id for row in sample] == [row.candidate_id for row in build_spot_check_sample(rows, sample_rate=0.02)]
    assert 1 <= len(sample) <= 5
